from pydantic import BaseModel, Field, field_validator,computed_field
import hashlib
import json
import time
from datetime import datetime
from typing import List, Optional,Literal,Dict, Any
import uuid
import struct
import binascii
from bitcoinutils.setup import setup
from bitcoinutils.keys import PrivateKey, PublicKey, P2wpkhAddress, P2wshAddress, P2shAddress,b58encode
from bitcoinutils.script import Script
import bech32

class BaseBitcoinEntity(BaseModel):
    """Bitcoin関連の基底クラス"""
    
    def calculate_hash(self, hex: str,is_reverse:bool=True) -> str:
        """ハッシュ値を計算"""
        binary_data = binascii.unhexlify(hex)
        hash1 = hashlib.sha256(binary_data).digest()
        hash2 = hashlib.sha256(hash1).digest()
        if is_reverse:
            return hash2[::-1].hex()
        else:
            return hash2.hex()

            
    
    def calculate_double_hash256(self, data: bytes) -> str:
        """ダブルSHA256ハッシュを計算"""
        
        hash1 = hashlib.sha256(data).digest()
        hash2 = hashlib.sha256(hash1).digest()
        return hash2[::-1].hex()
    
    def reverse_bytes(self, hex_string: str) -> str:
        """バイト順序を逆転"""
        return ''.join(reversed([hex_string[i:i+2] for i in range(0, len(hex_string), 2)]))
    
    def to_little_endian(self, value: int, byte_length: int) -> bytes:
        """リトルエンディアンのバイト列に変換"""
        return value.to_bytes(byte_length, 'little')
    
    def encode_varint(self,script_sig:str):
        """ScriptSigサイズをVarIntエンコード"""
        hex_length = len(script_sig)
        byte_length = hex_length // 2
        if byte_length < 0xfd:
            return struct.pack('<B', byte_length)
        elif byte_length <= 0xffff:
            return struct.pack('<BH', 0xfd, byte_length)
        elif byte_length <= 0xffffffff:
            return struct.pack('<BI', 0xfe, byte_length)
        else:
            return struct.pack('<BQ', 0xff, byte_length)


class BitcoinBlockHeader(BaseBitcoinEntity):
    """
    ビットコインブロックヘッダーを表すPydanticモデル
    """
    version: int = Field(..., ge=1, le=2**32 - 1, description="ブロックバージョン番号",example=1)
    previous_hash: str = Field(..., min_length=64, max_length=64, description="前のブロックのハッシュ値（16進数文字列）",example="0000000000000000000000000000000000000000000000000000000000000000")
    merkle_root: str = Field(..., min_length=64, max_length=64, description="マークルルートハッシュ（16進数文字列）",example="4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b")
    timestamp: int = Field(..., description="ブロック作成時のUnixタイムスタンプ", ge=0,example=1231006505)
    bits: int = Field(..., description="難易度ターゲット（コンパクト形式）", ge=0, le=2**32 - 1,example=486604799)
    nonce: int = Field(..., ge=0, le=2**32 - 1, description="プルーフオブワークで使用されるナンス値",example=2083236893)

    @field_validator('previous_hash', 'merkle_root')
    @classmethod
    def validate_hash_format(cls, v):
        """ハッシュ値が正しい16進数形式かチェック"""
        try:
            int(v, 16)
        except ValueError:
            raise ValueError('ハッシュ値は64文字の16進数文字列である必要があります')
        return v.lower()  # 小文字に統一
    
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v):
        """タイムスタンプが妥当な範囲内かチェック"""
        # ビットコイン開始日（2009年1月3日）より前は無効
        bitcoin_genesis_time = 1231006505
        if v < bitcoin_genesis_time:
            raise ValueError('タイムスタンプがビットコイン開始日より前です')
        return v


    def get_preprocessing_data(self) -> str:
        """
        ハッシュ計算前のブロックヘッダーデータを生成
        """
        version_le = struct.pack('<I', self.version).hex()
        timestamp_le = struct.pack('<I', self.timestamp).hex()
        bits_le = struct.pack('<I', self.bits).hex()
        nonce_le = struct.pack('<I', self.nonce).hex()
        previous_hash_le = self.reverse_bytes(self.previous_hash)
        merkle_root_le = self.reverse_bytes(self.merkle_root)
        
        # 全てを連結
        header_data = (version_le + previous_hash_le + merkle_root_le + 
                      timestamp_le + bits_le + nonce_le)
        
        return header_data

    
    def calculate_hash(self) -> str:
        """
        ブロックヘッダーのハッシュ値を計算
        """
        binary_data = binascii.unhexlify(self.get_preprocessing_data())
        return self.calculate_double_hash256(binary_data)

class BitcoinTransactionScriptSignature(BaseModel):
    asm:Optional[str] = Field(None,description="デジタル署名とトランザクションをアンロックするためのスクリプト（asm形式）")
    hex:str = Field(...,description="デジタル署名とトランザクションをアンロックするためのスクリプト（16進数文字列）")
    

class BitcoinTransactionInput(BaseBitcoinEntity):
    txid:str = Field(..., min_length=64, max_length=64, description="前のトランザクションのハッシュ値（16進数文字列）")
    vout:int= Field(..., ge=0, le=2**32 - 1, description="前のトランザクションの出力インデックス (0から開始)")
    script_sig:BitcoinTransactionScriptSignature
    txinwitness:Optional[List[str]]=None
    sequence:int= Field(..., ge=1, le=2**32 - 1, description="シーケンス番号 (通常は0xffffffff = 4294967295)")
    
    def serialize_old(self):
        """
        ハッシュ計算前の生データを生成
        """
        previous_txid_hash_le = self.reverse_bytes(self.txid)
        previous_output_index_le = struct.pack('<I', self.vout).hex()
        script_signature_size=self.encode_varint(self.script_sig.hex).hex()
        sequence_le = struct.pack('<I', self.sequence).hex()
        
        # 全てを連結
        return (previous_txid_hash_le + previous_output_index_le +script_signature_size+ self.script_sig.hex+sequence_le)
    
    def serialize(self):
        if not self.txinwitness:
            return "00"
        stack_items = struct.pack('<B', len(self.txinwitness)).hex()
        size_item="".join([self.encode_varint(txinwitness).hex()+txinwitness for txinwitness  in self.txinwitness])
        return (stack_items+size_item)


ScriptPubkeyType = Literal["P2PK","P2PKH","P2SH","P2WPKH","P2WSH","P2SH-P2WPKH","P2SH-P2WSH","P2TR","OP_RETURN","Nonstandard Scripts"]

class BitcoinTransactionScriptPubkey(BaseModel):
    asm:Optional[str] = Field(None,description="デジタル署名とトランザクションをアンロックするためのスクリプト（asm形式）")
    hex:str = Field(...,description="デジタル署名とトランザクションをアンロックするためのスクリプト（16進数文字列）")
    type:Optional[ScriptPubkeyType]=None

class BitcoinTransactionOutput(BaseBitcoinEntity):
    value:int = Field(..., ge=1, le=2**64 - 1, description="送金額 (サトシ単位: 1 BTC = 100,000,000 satoshi)",example=201649)
    n:Optional[int]=None
    script_pubkey:BitcoinTransactionScriptPubkey

    def serialize(self):
        """
        ハッシュ計算前の生データを生成
        """
        amount_le = struct.pack('<Q', self.value).hex()
        script_pubkey_size=self.encode_varint(self.script_pubkey.hex).hex()
        
        # 全てを連結
        return (amount_le +script_pubkey_size+ self.script_pubkey.hex)

class BitcoinTransactionStackItem(BaseBitcoinEntity):
    item:str= Field(...,description="The data to be pushed on to the stack (16進数文字列)",example="")
    
    def serialize(self):
        size = self.encode_varint(self.item).hex()
        return (size +self.item)


class TransactionRequest(BaseModel):
    version:int= Field(..., ge=1, le=2**32 - 1, description="ブロックバージョン番号")
    locktime:int= Field(..., ge=0, le=2**32 - 1, description="トランザクションが有効になる時刻またはブロック高 (0=即座に有効)")
    vin:List[BitcoinTransactionInput]
    outputs:List[BitcoinTransactionOutput]



class BitcoinTransaction(BaseBitcoinEntity):
    txid:str= Field(..., min_length=64, max_length=64, description="")
    wtxid:Optional[str]= None
    version:int= Field(..., ge=1, le=2**32 - 1, description="ブロックバージョン番号")
    size:Optional[int]=None
    weight:Optional[int]=None
    locktime:int= Field(..., ge=0, le=2**32 - 1, description="トランザクションが有効になる時刻またはブロック高 (0=即座に有効)")
    vin:List[BitcoinTransactionInput]
    outputs:List[BitcoinTransactionOutput]
    blockhash:Optional[str]= Field(None, min_length=64, max_length=64, description="")
    

    def _get_base_transaction_data(self) -> str:
        """
        共通のトランザクションデータ部分を生成（witness除く）
        """
        version_le = struct.pack('<I', self.version).hex()
        input_count = struct.pack('<B', len(self.vin)).hex()
        input_data = "".join([input.serialize_old() for input in self.vin])
        output_count = struct.pack('<B', len(self.outputs)).hex()
        output_data = "".join([output.serialize() for output in self.outputs])
        locktime_le = struct.pack('<I', self.locktime).hex()
        
        return (version_le + input_count + input_data + 
                output_count + output_data + locktime_le)
    
    def _get_witness_data(self) -> str:
        """
        Witnessデータを取得
        """
        
        if not self.vin:
            return ""
        if not  [vin.txinwitness for vin in self.vin if vin.txinwitness]:
            return ""
        return "".join([vin.serialize() for vin in self.vin])

    
    def _get_witness_data_old(self) -> str:
        """
        Witnessデータを取得
        """
        if not self.witness:
            return ""
        return "".join([witness.serialize() for witness in self.witness])
    
    def _is_segwit(self) -> bool:
        """
        SegWitトランザクションかどうかを判定
        """
        return (self.segwit_marker is not None and 
                self.segwit_flag is not None and 
                bool(self.witness))
    
    def get_legacy_transaction_data(self) -> str:
        """
        Legacy形式のトランザクションデータ（TXID計算用）
        """
        return self._get_base_transaction_data()
    
    def get_segwit_transaction_data(self) -> str:
        """
        SegWit形式のトランザクションデータ（WTXID計算用）
        """
        witness_data = self._get_witness_data()
        if not witness_data:
            return self.get_legacy_transaction_data()
            
        version_le = struct.pack('<I', self.version).hex()
        marker_le = struct.pack('<B', 0).hex()
        flag_le = struct.pack('<B', 1).hex()
        input_count = struct.pack('<B', len(self.vin)).hex()
        input_data = "".join([input.serialize_old() for input in self.vin])
        output_count = struct.pack('<B', len(self.outputs)).hex()
        output_data = "".join([output.serialize() for output in self.outputs])
        locktime_le = struct.pack('<I', self.locktime).hex()
        
        return (version_le + marker_le + flag_le + input_count + 
                input_data + output_count + output_data + 
                witness_data + locktime_le)
    
    def calculate_txid(self) :
        """
        TXID（Transaction ID）を計算
        SegWitでもLegacy形式で計算（witnessデータ除外）
        """
        legacy_data = self.get_legacy_transaction_data()
        binary_data = binascii.unhexlify(legacy_data)
        return self.calculate_double_hash256(binary_data)
    
    def calculate_wtxid(self) -> str:
        """
        WTXID（Witness Transaction ID）を計算
        SegWitの場合はwitnessデータを含む、Legacyの場合はTXIDと同じ
        """
        if not self._is_segwit():
            # LegacyトランザクションではWTXID = TXID
            return self.calculate_txid()
            
        segwit_data = self.get_segwit_transaction_data()
        binary_data = binascii.unhexlify(segwit_data)
        return self.calculate_double_hash256(binary_data)
    
    @classmethod
    def generate_transaction(cls,
                             transaction:TransactionRequest,
    ):
        instance = cls(
            txid="0" * 64,
            **transaction.model_dump(),
        )
        
        instance.txid = instance.calculate_hash(instance.get_legacy_transaction_data())
        instance.wtxid = instance.calculate_hash(instance.get_segwit_transaction_data())
        return instance

class BlockRequest(BaseModel):
    version: int = Field(..., ge=1, le=2**32 - 1, description="ブロックバージョン番号")
    previous_block_hash: str = Field(..., min_length=64, max_length=64, description="前ブロックのハッシュ値（16進数文字列）")
    time: int = Field(..., description="ブロック作成時のUnixタイムスタンプ", ge=0)
    bits: str 
    nonce: int = Field(..., ge=0, le=2**32 - 1, description="プルーフオブワークで使用されるナンス値")
    txids:List[str]=Field(default_factory=list)
    # merkleroot: Optional[str] = Field(..., min_length=64, max_length=64, description="マークルルートハッシュ（16進数文字列）")
    


class BitcoinBlock(BaseBitcoinEntity):
    """ビットコインブロック全体を表すクラス"""
    hash: str = Field(..., min_length=64, max_length=64, description="")
    confirmations:Optional[int]=None
    height:Optional[int]=None
    version: int = Field(..., ge=1, le=2**32 - 1, description="ブロックバージョン番号")
    version_hex:Optional[str]=None
    merkleroot: str = Field(..., min_length=64, max_length=64, description="マークルルートハッシュ（16進数文字列）")
    time: int = Field(..., description="ブロック作成時のUnixタイムスタンプ", ge=0)
    nonce: int = Field(..., ge=0, le=2**32 - 1, description="プルーフオブワークで使用されるナンス値")
    bits: str 
    difficulty:Optional[int]=None
    nTx:Optional[int]=None
    previous_block_hash: str = Field(..., min_length=64, max_length=64, description="前ブロックのハッシュ値（16進数文字列）")
    next_block_hash: Optional[str] = Field(None, min_length=64, max_length=64, description="次ブロックのハッシュ値（16進数文字列）")
    size:Optional[int]=None
    weight:Optional[int]=None
    txids:List[str]=Field(default_factory=list)
    
    def get_block_raw_data(self) -> str:
        """
        ハッシュ計算前のブロックデータを生成
        """
        version_le = struct.pack('<I', self.version).hex()
        time_le = struct.pack('<I', self.time).hex()
        nonce_le = struct.pack('<I', self.nonce).hex()
        previous_block_hash_le = self.reverse_bytes(self.previous_block_hash)
        bits_le = self.reverse_bytes(self.bits)
        merkleroot_le = self.reverse_bytes(self.merkleroot)
        
        return (version_le + previous_block_hash_le + merkleroot_le + 
                      time_le + bits_le + nonce_le)
    
    @classmethod
    def generate_block(cls,block:BlockRequest):
        if len(block.txids)==0:
            raise ValueError("txidsを入力してください")
        
        instance = cls(
            **block.model_dump(),
            hash="0" * 64,  # 一時的な値
            merkleroot="0" * 64,# 一時的な値
        )
        
        instance.merkleroot=instance.get_merkleroot()
        instance.hash = instance.calculate_hash(instance.get_block_raw_data())
        return instance

    def get_merkleroot(self):
        if not self.txids:
            return ""
        
        txids = self.txids[:]
        while len(txids) > 1:
            next_level = []
            for i in range(0, len(txids), 2): 
                left = txids[i]
                right = txids[i + 1] if i + 1 < len(txids) else left
                
                combined = self.reverse_bytes(left) + self.reverse_bytes(right)
                hash_result = self.calculate_double_hash256(binascii.unhexlify(combined))
                next_level.append(hash_result)
            
            txids = next_level
        
        return txids[0]

class BitcoinAddress(BaseBitcoinEntity):
    private_key:Optional[str]=None
    public_key:Optional[str]=None
    p2pkh_address:Optional[str]=None
    p2wpkh_address:Optional[str]=None
    
    def get_p2pkhaddress(self):
        if not self.private_key:
            return None
        pk=PrivateKey(b=bytes.fromhex(self.private_key))
        to_hash160=pk.get_public_key().to_hash160()
        pre_hash160="00"+to_hash160
        cksum=self.calculate_hash(pre_hash160,False)
        raw_data=pre_hash160+cksum[:8]
        p2pkhaddress=b58encode(binascii.unhexlify(raw_data)).decode()
        return p2pkhaddress
    
    def get_p2wpkhaddress(self):
        if not self.private_key:
            return None
        
        pk = PrivateKey(b=bytes.fromhex(self.private_key))
        to_hash160 = pk.get_public_key().to_hash160()
        p2wpkh_wp = "0014" + to_hash160
        all_bits = "".join([format(byte, '08b') for byte in binascii.unhexlify(p2wpkh_wp)])
        five_bit_groups = []
        for i in range(0, 160, 5):
            five_bit_group = all_bits[i:i+5]
            five_bit_groups.append(int(five_bit_group, 2))
        
        data_for_checksum = [0] + five_bit_groups
        checksum = bech32.bech32_create_checksum(hrp="bc", data=data_for_checksum)
        
        bech32_data=bech32.bech32_encode(hrp="bc",data=(data_for_checksum+checksum))
        
        print("five_bit_groups (integers):", five_bit_groups)
        print("checksum:", checksum)
        print("checksum:", checksum)
        print("bech32:", bech32_data)
        
        return bech32_data
    
    @classmethod
    def generate_address(cls,private_key:Optional[str]=None):
        pk_hex=private_key if private_key else hashlib.sha256(uuid.uuid4().bytes).hexdigest()
        pk=PrivateKey(b=bytes.fromhex(pk_hex))
        instance=cls(private_key=pk_hex,public_key=pk.get_public_key().to_hex())
        instance.p2pkh_address=instance.get_p2pkhaddress()
        instance.p2wpkh_address=instance.get_p2wpkhaddress()
        return instance
            
            
        

class BitcoinWallet(BaseModel):
    """
    レガシー、Segwit、P2SH-Segwitアドレスの生成とメッセージ署名機能を提供
    """
    
    # プライベートフィールド（シリアライゼーション時に除外）
    secret_exponent: Optional[int] = Field(default=None, exclude=True)
    wif_key: Optional[str] = Field(default=None, exclude=True)
    
    # パブリックフィールド
    network: str = Field(default="mainnet", description="Bitcoin network (mainnet/testnet)")
    compressed: bool = Field(default=True, description="Use compressed public key format")
    address_type: Literal["legacy", "segwit", "p2sh_segwit"] = Field(
        default="legacy", 
        description="Address type to generate"
    )
    
    # 計算されるフィールド（読み取り専用）
    private_key_wif: Optional[str] = Field(default=None, description="Private key in WIF format")
    public_key_hex: Optional[str] = Field(default=None, description="Public key in hex format")
    
    # 各種アドレス情報
    legacy_address: Optional[str] = Field(default=None, description="Legacy P2PKH address")
    legacy_hash160: Optional[str] = Field(default=None, description="Hash160 of legacy address")
    
    segwit_address: Optional[str] = Field(default=None, description="Native Segwit address (P2WPKH)")
    segwit_witness_program: Optional[str] = Field(default=None, description="Segwit witness program")
    segwit_version: Optional[str] = Field(default=None, description="Segwit version")
    
    p2sh_segwit_address: Optional[str] = Field(default=None, description="P2SH wrapped Segwit address")
    
    # メインアドレス（選択されたタイプ）
    address: Optional[str] = Field(default=None, description="Main address (based on address_type)")
    
    class Config:
        # Pydantic設定
        validate_assignment = True
        arbitrary_types_allowed = True
        
    def __init__(self, **data):
        super().__init__(**data)
        # ネットワークのセットアップ
        setup(self.network)
        
        # プライベートキーの初期化
        if self.secret_exponent is not None:
            self._private_key = PrivateKey(secret_exponent=self.secret_exponent)
        elif self.wif_key is not None:
            self._private_key = PrivateKey.from_wif(self.wif_key)
        else:
            # デフォルトとして secret_exponent=1 を使用
            self._private_key = PrivateKey(secret_exponent=1)
        
        # 各種値を計算して設定
        self._update_derived_fields()
    
    def _update_derived_fields(self):
        """派生フィールドを更新"""
        # WIF形式のプライベートキー
        self.private_key_wif = self._private_key.to_wif(compressed=self.compressed)
        
        # パブリックキーを取得
        pub_key = self._private_key.get_public_key()
        self.public_key_hex = pub_key.to_hex(compressed=self.compressed)
        
        # レガシーアドレス（P2PKH）
        legacy_addr = pub_key.get_address()
        self.legacy_address = legacy_addr.to_string()
        self.legacy_hash160 = legacy_addr.to_hash160()
        
        # Segwitアドレス（P2WPKH）
        segwit_addr = pub_key.get_segwit_address()
        self.segwit_address = segwit_addr.to_string()
        self.segwit_witness_program = segwit_addr.to_witness_program()
        self.segwit_version = segwit_addr.get_type()
        
        # P2SH-Segwitアドレス（P2SH-P2WPKH）
        p2sh_segwit_addr = P2shAddress.from_script(segwit_addr.to_script_pub_key())
        self.p2sh_segwit_address = p2sh_segwit_addr.to_string()
        
        # メインアドレスを設定
        if self.address_type == "legacy":
            self.address = self.legacy_address
        elif self.address_type == "segwit":
            self.address = self.segwit_address
        elif self.address_type == "p2sh_segwit":
            self.address = self.p2sh_segwit_address
    
    @field_validator('network')
    @classmethod
    def validate_network(cls, v):
        """ネットワークの検証"""
        if v not in ['mainnet', 'testnet']:
            raise ValueError('Network must be either "mainnet" or "testnet"')
        return v
    
    @field_validator('secret_exponent')
    @classmethod
    def validate_secret_exponent(cls, v):
        """秘密指数の検証"""
        if v is not None and (v <= 0 or v >= 2**256):
            raise ValueError('Secret exponent must be between 1 and 2^256-1')
        return v
    
    def sign_message(self, message: str) -> Optional[str]:
        """
        メッセージに署名する
        
        Args:
            message: 署名するメッセージ
            
        Returns:
            署名文字列（失敗時はNone）
        """
        try:
            return self._private_key.sign_message(message)
        except Exception:
            return None
    
    def verify_message(self, message: str, signature: str, address_type: Optional[str] = None) -> bool:
        """
        メッセージ署名を検証する
        
        Args:
            message: 元のメッセージ
            signature: 署名文字列
            address_type: 検証に使用するアドレスタイプ（Noneの場合は現在の設定を使用）
            
        Returns:
            署名が有効かどうか
        """
        try:
            if address_type is None:
                address_type = self.address_type
                
            if address_type == "legacy":
                verify_address = self.legacy_address
            elif address_type == "segwit":
                verify_address = self.segwit_address
            elif address_type == "p2sh_segwit":
                verify_address = self.p2sh_segwit_address
            else:
                return False
                
            return PublicKey.verify_message(verify_address, signature, message)
        except Exception:
            return False
    
    def get_all_addresses(self) -> Dict[str, str]:
        """
        全てのアドレスタイプを辞書で取得
        
        Returns:
            アドレスタイプをキーとした辞書
        """
        return {
            "legacy": self.legacy_address,
            "segwit": self.segwit_address,
            "p2sh_segwit": self.p2sh_segwit_address
        }
    
    def display_info(self, show_all: bool = False):
        """
        ウォレット情報を表示
        
        Args:
            show_all: 全てのアドレスタイプを表示するか
        """
        print(f"\nPrivate key WIF: {self.private_key_wif}")
        print(f"Public key: {self.public_key_hex}")
        print(f"Address type: {self.address_type}")
        
        if show_all:
            print("\n--- All Address Types ---")
            print(f"Legacy (P2PKH): {self.legacy_address}")
            print(f"Legacy Hash160: {self.legacy_hash160}")
            print(f"Segwit (P2WPKH): {self.segwit_address}")
            print(f"Segwit Witness Program: {self.segwit_witness_program}")
            print(f"Segwit Version: {self.segwit_version}")
            print(f"P2SH-Segwit: {self.p2sh_segwit_address}")
        else:
            print(f"Main Address ({self.address_type}): {self.address}")
            
        print("\n--------------------------------------\n")
    
    def create_p2wsh_address(self, script_elements: list) -> str:
        """
        P2WSH（Pay to Witness Script Hash）アドレスを作成
        
        Args:
            script_elements: スクリプト要素のリスト
            
        Returns:
            P2WSHアドレス
        """
        try:
            script = Script(script_elements)
            p2wsh_addr = P2wshAddress.from_script(script)
            return p2wsh_addr.to_string()
        except Exception:
            return None
    
    def create_p2sh_p2wsh_address(self, script_elements: list) -> str:
        """
        P2SH-P2WSH（P2SH wrapped P2WSH）アドレスを作成
        
        Args:
            script_elements: スクリプト要素のリスト
            
        Returns:
            P2SH-P2WSHアドレス
        """
        try:
            script = Script(script_elements)
            p2wsh_addr = P2wshAddress.from_script(script)
            p2sh_p2wsh_addr = P2shAddress.from_script(p2wsh_addr.to_script_pub_key())
            return p2sh_p2wsh_addr.to_string()
        except Exception:
            return None
    
    @classmethod
    def from_wif(cls, wif_key: str, network: str = "mainnet", compressed: bool = True, 
                 address_type: str = "legacy"):
        """
        WIFキーからウォレットを作成
        
        Args:
            wif_key: WIF形式のプライベートキー
            network: ネットワーク
            compressed: 圧縮形式を使用するか
            address_type: アドレスタイプ
            
        Returns:
            BitcoinWalletインスタンス
        """
        return cls(wif_key=wif_key, network=network, compressed=compressed, 
                  address_type=address_type)
    
    @classmethod
    def from_secret(cls, secret_exponent: int, network: str = "mainnet", 
                   compressed: bool = True, address_type: str = "segwit"):
        """
        秘密指数からウォレットを作成
        
        Args:
            secret_exponent: 秘密指数
            network: ネットワーク
            compressed: 圧縮形式を使用するか
            address_type: アドレスタイプ
            
        Returns:
            BitcoinWalletインスタンス
        """
        return cls(secret_exponent=secret_exponent, network=network, 
                  compressed=compressed, address_type=address_type)