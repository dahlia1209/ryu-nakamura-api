from pydantic import BaseModel, Field, field_validator, computed_field, model_validator
from typing import List, Optional, Literal, Dict, Any
import bech32
from utils.blockchain import (
    script_to_hex,
    hex_to_script,
    validate_hex_string,
    validate_script,
    validate_readonly,
    validate_script_type,
    Base,
)
from azure.data.tables import TableEntity
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
    Prehashed,
)
import hashlib


class Block(Base):
    hash: str = Field(..., min_length=64, max_length=64)
    height: Optional[int] = Field(None, ge=0, le=2**16 - 1)
    version: int = Field(..., ge=0, le=2**32 - 1)
    previous_hash: str = Field(..., min_length=64, max_length=64)
    merkle_root: str = Field(..., min_length=64, max_length=64)
    timestamp: int = Field(..., ge=0)
    bits: str = Field(..., min_length=8, max_length=8)
    nonce: int = Field(..., ge=0, le=2**32 - 1)
    transaction_count: Optional[int] = Field(None)
    transactions: List["Transaction"] = Field(..., min_length=1)

    @field_validator("hash", "previous_hash", "merkle_root", "bits")
    @classmethod
    def check_hex(cls, v: str) -> str:
        return validate_hex_string(v)

    @model_validator(mode="after")
    def validate_hash(self):
        raw = self.get_raw_data()
        cal_hash = self.hash256_hex(raw)
        if self.hash != cal_hash:
            raise ValueError(
                f"hashが正しくないです。与えられたhash:{self.hash},計算されたhash:{cal_hash},計算元hash:{raw}"
            )
        return self

    @model_validator(mode="after")
    def validate_merkle_root(self):
        txids = [t.txid for t in self.transactions]
        cal_merkle_root = self.get_merkle_root(txids)
        if self.merkle_root != cal_merkle_root:
            txids_str = " ".join(txids)
            raise ValueError(
                f"merkle_rootが正しくないです。"
                f"与えられたmerkle_root:{self.merkle_root}, "
                f"計算されたmerkle_root:{cal_merkle_root}, "
                f"計算元merkle_root:{txids_str}"
            )
        return self

    @model_validator(mode="after")
    def validate_bits(self):
        target = self.bits_to_target()
        hash_int = int(self.hash, 16)
        target_int = int(target, 16)

        if hash_int > target_int:
            raise ValueError(
                f"与えられたhashはtargetより高いです。"
                f"与えられたhash: {self.hash}, target: {target}"
            )
        return self

    @model_validator(mode="after")
    def update_optional_field(self):
        self.transaction_count = len(self.transactions)

        for t in self.transactions:
            t.block_height = self.height
            t.block_hash = self.hash

            for i, vin in enumerate(t.vin):
                vin.spent_block_hash = self.hash

            for i, out in enumerate(t.outputs):
                out.block_hash = self.hash

        return self

    def get_raw_data(self) -> str:
        version_hex = self.int_to_hex(self.version, 4)
        previous_hash_le = self.hex_to_little_endian(self.previous_hash)
        merkle_root_le = self.hex_to_little_endian(self.merkle_root)
        bits_le = self.hex_to_little_endian(self.bits)
        nonce_hex = self.int_to_hex(self.nonce, 4)
        time_hex = self.int_to_hex(self.timestamp, 4)

        return (
            version_hex
            + previous_hash_le
            + merkle_root_le
            + time_hex
            + bits_le
            + nonce_hex
        )

    def get_merkle_root(self, txids: list[str]) -> str:
        # 終了条件: ハッシュが1つになったら返す
        if len(txids) == 1:
            return txids[0]

        # 結果を格納する配列
        result = []

        # ペアに分割して処理
        for i in range(0, len(txids), 2):
            one = self.hex_to_little_endian(txids[i])
            if i + 1 < len(txids):
                two = self.hex_to_little_endian(txids[i + 1])
                concat = one + two
            else:
                # ペアがない場合は自分自身と結合
                concat = one + one

            # 結合したデータをハッシュして結果に追加
            result.append(self.hash256_hex(concat))

        # 再帰: 結果に対して同じ処理を繰り返す
        return self.get_merkle_root(result)

    def to_entity(self, partition_type: "PartitionType", row_key: str):
        return BlockEntity(
            PartitionKey=partition_type,
            RowKey=row_key,
            **self.model_dump(exclude={"transactions"}),
        )

    def bits_to_target(self) -> str:
        bits_num = int(self.bits, 16)
        exponent = bits_num >> 24
        mantissa = bits_num & 0x00FFFFFF

        if exponent <= 3:
            target = mantissa >> (8 * (3 - exponent))
        else:
            target = mantissa << (8 * (exponent - 3))

        return format(target, "064x")


class Transaction(Base):
    txid: str = Field(..., min_length=64, max_length=64)
    block_height: Optional[int] = Field(None, ge=0, le=2**32 - 1)
    block_hash: Optional[str] = Field(None, min_length=64, max_length=64)
    wtxid: Optional[str] = None
    version: int = Field(..., ge=1, le=2**32 - 1)
    size: Optional[int] = None
    weight: Optional[int] = None
    fee: int = Field(0)
    locktime: int = Field(..., ge=0, le=2**32 - 1)
    vin: List["TransactionVin"] = Field(default_factory=list)
    outputs: List["TransactionOutput"] = Field(default_factory=list)

    @model_validator(mode="after")
    def update_optional_field(self):
        for i, vin in enumerate(self.vin):
            vin.spent_txid = self.txid
            vin.n = i

        for i, out in enumerate(self.outputs):
            out.txid = self.txid
            out.n = i

        return self

    @model_validator(mode="after")
    def validate_hash(self):
        raw = self.get_raw_data()
        cal_hash = self.hash256_hex(raw)
        if self.txid != cal_hash:
            raise ValueError(
                f"txidが正しくないです。与えられたhash:{self.txid},計算されたhash:{cal_hash},計算元hash:{raw}"
            )
        return self

    def get_raw_data(self):
        version_le = self.int_to_hex(self.version, 4)
        vin_count = self.int_to_compact_size(len(self.vin))
        vin_raw_data = "".join([vin.get_raw_data() for vin in self.vin])
        vout_count = self.int_to_compact_size(len(self.outputs))
        vout_raw_data = "".join([vout.get_raw_data() for vout in self.outputs])
        locktime_le = self.int_to_hex(self.locktime, 4)

        # 全てを連結
        return (
            version_le
            + vin_count
            + vin_raw_data
            + vout_count
            + vout_raw_data
            + locktime_le
        )

    def to_entity(self):
        return TransactionEntity(
            PartitionKey=self.block_hash,
            RowKey=self.txid,
            **self.model_dump(exclude={"vin", "outputs"}),
        )

    def is_coinbase(self):
        return self.vin[0].is_coinbase()

    def get_hash_raw_message(self, target_index: int, sighash: int = 0x01):
        version_le = self.int_to_hex(self.version, 4)
        vin_count = self.int_to_compact_size(len(self.vin))
        input_raw = "".join(
            [
                vin.get_unsigned_data(target_index == i)
                for (i, vin) in enumerate(self.vin)
            ]
        )
        vout_count = self.int_to_compact_size(len(self.outputs))
        vout_raw_data = "".join([vout.get_raw_data() for vout in self.outputs])
        locktime_le = self.int_to_hex(self.locktime, 4)
        sighash_hex = self.int_to_hex(sighash, 4)

        return (
            version_le
            + vin_count
            + input_raw
            + vout_count
            + vout_raw_data
            + locktime_le
            + sighash_hex
        )
    
    


ScriptType = Literal[
    "P2PK",
    "P2PKH",
    "P2MS",
    "P2SH",
    "OP_RETURN",
    "P2WPKH",
    "P2WSH",
    "P2TR",
    "CUSTOM",
    "COINBASE",
]


class TransactionVin(Base):
    utxo_block_hash: Optional[str] = Field(None, min_length=64, max_length=64)
    utxo_txid: str = Field(..., min_length=64, max_length=64)
    utxo_vout: int = Field(..., ge=0, le=2**32 - 1)
    utxo_script_pubkey: Optional[str] = None
    utxo_value: Optional[int] = None
    sequence: int = Field(..., ge=0, le=2**32 - 1)
    script_sig_asm: Optional[str] = None
    script_sig_hex: Optional[str] = None
    script_type: Optional[ScriptType] = None
    spent_block_hash: Optional[str] = Field(None, min_length=64, max_length=64)
    spent_txid: Optional[str] = Field(None, min_length=64, max_length=64)
    spent_witness: Optional[str] = None
    n: Optional[int] = None

    @field_validator("n", "utxo_block_hash", "spent_block_hash")
    @classmethod
    def check_readonly(cls, v: Optional[int]) -> Optional[int]:
        return validate_readonly(v)

    @field_validator("script_sig_hex", "spent_txid", "utxo_txid")
    @classmethod
    def check_hex(cls, v: str) -> str:
        return validate_hex_string(v)

    @model_validator(mode="after")
    def check_script(self):
        return validate_script(self, "script_sig_asm", "script_sig_hex")

    @model_validator(mode="after")
    def check_coinbase(self):
        if self.is_coinbase():
            if self.spent_txid is not None or self.n is not None:
                raise ValueError(
                    "coinbaseトランザクションではspent_txidとnは指定できません"
                )
            self.script_type = "COINBASE"
            # # coinbaseの場合、script_sig_hexは必須(ブロック高などのデータを含む)
            # if self.script_sig_hex is None:
            #     raise ValueError('coinbaseトランザクションではscript_sig_hexが必須です')

        else:
            # utxo_txidが全て0でない、またはutxo_voutが0xffffffffでない場合
            if self.utxo_txid == "0" * 64 or self.utxo_vout == 0xFFFFFFFF:
                raise ValueError(
                    "無効なUTXO参照です。utxo_txidとutxo_voutの組み合わせが不正です"
                )
        return self

    def is_coinbase(self):
        return self.utxo_txid == "0" * 64 and self.utxo_vout == 0xFFFFFFFF

    def get_raw_data(self) -> str:
        utxo_txid_le = self.hex_to_little_endian(self.utxo_txid)
        utxo_vout_le = self.int_to_hex(self.utxo_vout, 4)
        script_size = self.int_to_compact_size(len(self.script_sig_hex) // 2)
        sequence_le = self.int_to_hex(self.sequence, 4)

        # 全てを連結
        return (
            utxo_txid_le
            + utxo_vout_le
            + script_size
            + self.script_sig_hex
            + sequence_le
        )

    def to_entity(self):
        return TransactionVinEntity(
            PartitionKey=self.spent_txid,
            RowKey=self.n,
            **self.model_dump(),
        )

    def get_unsigned_data(self, is_target: bool = True):
        if is_target and self.utxo_script_pubkey is None :
            raise ValueError(f"署名検証のためにutxo_script_pubkeyをセットしてください,txid:{self.spent_txid},vin_n:{self.n}")
        utxo_txid_le = self.hex_to_little_endian(self.utxo_txid)
        utxo_vout_le = self.int_to_hex(self.utxo_vout, 4)
        script_size = self.int_to_compact_size(len(self.utxo_script_pubkey) // 2) if is_target else "00"
        script_pubkey = self.utxo_script_pubkey if is_target else ""
        sequence_le = self.int_to_hex(self.sequence, 4)
        # 全てを連結
        return utxo_txid_le + utxo_vout_le + script_size + script_pubkey + sequence_le
    
    def get_utxo_value(self):
        if self.utxo_value is None:
            raise  ValueError(f"utxo_valueがセットされていません")
        return self.utxo_value


class TransactionOutput(Base):
    value: int = Field(
        ..., ge=1, le=2**64 - 1, description="サトシ単位: 1 BTC = 100,000,000 satoshi"
    )
    script_pubkey_asm: Optional[str] = None
    script_pubkey_hex: Optional[str] = None
    script_type: Optional[ScriptType] = None
    block_hash: Optional[str] = Field(None, min_length=64, max_length=64)
    txid: Optional[str] = Field(None, min_length=64, max_length=64)
    n: Optional[int] = None

    @field_validator("script_pubkey_hex", "txid")
    @classmethod
    def check_hex(cls, v: str) -> str:
        return validate_hex_string(v)

    @field_validator("n", "txid", "script_type")
    @classmethod
    def check_readonly(cls, v: Optional[int]) -> Optional[int]:
        return validate_readonly(v)

    @model_validator(mode="after")
    def check_script(self):
        return validate_script(self, "script_pubkey_asm", "script_pubkey_hex")

    @model_validator(mode="after")
    def check_script_type(self):
        return validate_script_type(self)

    def get_raw_data(self) -> str:
        value_hex = self.int_to_hex(self.value, 8)
        script_size = self.int_to_compact_size(len(self.script_pubkey_hex) // 2)

        # 全てを連結
        return value_hex + script_size + self.script_pubkey_hex

    def to_entity(self):
        return TransactionOutputEntity(
            PartitionKey=self.txid,
            RowKey=self.n,
            **self.model_dump(),
        )


## Entity
PartitionType = Literal["CURRENT", "HISTORY"]


class BlockEntity(BaseModel):
    PartitionKey: PartitionType
    RowKey: str = Field(..., min_length=64, max_length=64)  # hash or "0"**64
    hash: str = Field(..., min_length=64, max_length=64)  # hash
    version: int = Field(..., ge=0, le=2**32 - 1)
    height: int = Field(..., ge=0, le=2**16 - 1)
    previous_hash: str = Field(..., min_length=64, max_length=64)
    merkle_root: str = Field(..., min_length=64, max_length=64)
    timestamp: int = Field(..., ge=0)
    bits: str = Field(..., min_length=8, max_length=8)
    nonce: int = Field(..., ge=0, le=2**32 - 1)
    transaction_count: Optional[int] = Field(None)


class TransactionEntity(BaseModel):
    PartitionKey: str = Field(..., min_length=64, max_length=64)  # block hash
    RowKey: str = Field(..., min_length=64, max_length=64)  # txid
    txid: str = Field(..., min_length=64, max_length=64)
    block_height: int = Field(..., ge=0, le=2**32 - 1)
    block_hash: str = Field(..., min_length=64, max_length=64)
    wtxid: Optional[str] = None
    version: int = Field(..., ge=1, le=2**32 - 1)
    size: Optional[int] = None
    weight: Optional[int] = None
    fee: int = Field(0)
    locktime: int = Field(..., ge=0, le=2**32 - 1)


class TransactionVinEntity(BaseModel):
    PartitionKey: str = Field(..., min_length=64, max_length=64)  # spent_txid
    RowKey: str = Field(..., min_length=20, max_length=20)  # n 20桁
    utxo_block_hash: Optional[str] = Field(None, min_length=64, max_length=64)
    utxo_txid: str = Field(..., min_length=64, max_length=64)
    utxo_vout: int = Field(..., ge=0, le=2**32 - 1)
    utxo_script_pubkey: Optional[str] = None
    utxo_value: Optional[int] = None
    sequence: int = Field(..., ge=0, le=2**32 - 1)
    script_sig_asm: str
    script_sig_hex: str
    script_type: ScriptType
    spent_block_hash: str = Field(..., min_length=64, max_length=64)
    spent_txid: str = Field(..., min_length=64, max_length=64)
    spent_witness: Optional[str] = None
    n: int

    @field_validator("RowKey", mode="before")
    @classmethod
    def format_rowkey(cls, v):
        if isinstance(v, int):
            return f"{v:020d}"
        return v

    def to_original(self):
        return TransactionVin.model_construct(
            **self.model_dump(exclude={"PartitionKey", "RowKey"}),
        )


class TransactionOutputEntity(Base):
    PartitionKey: str = Field(..., min_length=64, max_length=64)  # txid
    RowKey: str = Field(..., min_length=20, max_length=20)  # n 20桁
    value: int = Field(
        ..., ge=1, le=2**64 - 1, description="サトシ単位: 1 BTC = 100,000,000 satoshi"
    )
    script_pubkey_asm: str
    script_pubkey_hex: str
    script_type: ScriptType
    block_hash: str = Field(..., min_length=64, max_length=64)
    txid: str = Field(..., min_length=64, max_length=64)
    n: int

    @field_validator("RowKey", mode="before")
    @classmethod
    def format_rowkey(cls, v):
        if isinstance(v, int):
            return f"{v:020d}"
        return v

    def to_original(self):
        return TransactionOutput.model_construct(
            **self.model_dump(exclude={"PartitionKey", "RowKey"}),
        )
