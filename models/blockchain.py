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
from bitcoinutils.keys import PrivateKey, PublicKey, P2wpkhAddress, P2wshAddress, P2shAddress,b58encode,b58decode,sigencode_der,ripemd160
from bitcoinutils.script import Script
from bitcoinutils.transactions import Transaction, TxInput, TxOutput
import bech32
from azure.data.tables import TableEntity
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature,Prehashed
import hashlib

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
        
    def int_to_hex(self,d:int):
        hex_bytes_le=struct.pack('<I', d)
        return hex_bytes_le.hex()
    
    @staticmethod
    def decode_varint(data, offset=0):
        """
        可変長整数をデコード
        Returns: (value, new_offset)
        """
        if offset >= len(data):
            raise ValueError("データが不足しています")
        
        first_byte = data[offset]
        
        if first_byte < 0xfd:
            return first_byte, offset + 1
        elif first_byte == 0xfd:
            if offset + 3 > len(data):
                raise ValueError("データが不足しています")
            value = struct.unpack('<H', data[offset+1:offset+3])[0]
            return value, offset + 3
        elif first_byte == 0xfe:
            if offset + 5 > len(data):
                raise ValueError("データが不足しています")
            value = struct.unpack('<I', data[offset+1:offset+5])[0]
            return value, offset + 5
        else:  # first_byte == 0xff
            if offset + 9 > len(data):
                raise ValueError("データが不足しています")
            value = struct.unpack('<Q', data[offset+1:offset+9])[0]
            return value, offset + 9

class BitcoinTransactionScriptSignature(BaseModel):
    asm:Optional[str] = Field(None,description="デジタル署名とトランザクションをアンロックするためのスクリプト（asm形式）")
    hex:str = Field(...,description="デジタル署名とトランザクションをアンロックするためのスクリプト（16進数文字列）")
    utxo_scriptpubkey_hex:Optional[str]=None
    

class BitcoinTransactionInput(BaseBitcoinEntity):
    parent_id:str=""
    txid:str = Field(..., min_length=64, max_length=64, description="前のトランザクションのハッシュ値（16進数文字列）")
    vout:int= Field(..., ge=0, le=2**32 - 1, description="前のトランザクションの出力インデックス (0から開始)")
    scriptsigsize:Optional[int]=None
    script_sig:Optional[BitcoinTransactionScriptSignature]=None
    txinwitness:Optional[List[str]]=None
    sequence:int= Field(..., ge=1, le=2**32 - 1, description="シーケンス番号 (通常は0xffffffff = 4294967295)")
    raw_data:Optional[str]=None
    
    def vout_to_hex(self):
        return struct.pack('<I', self.vout).hex()
    
    def serialize_legacy(self):
        """
        ハッシュ計算前の生データを生成
        """
        previous_txid_hash_le = self.reverse_bytes(self.txid)
        previous_output_index_le = self.vout_to_hex()
        script_signature_size=self.encode_varint(self.script_sig.hex).hex()
        sequence_le = struct.pack('<I', self.sequence).hex()
        
        # 全てを連結
        return (previous_txid_hash_le + previous_output_index_le +script_signature_size+ self.script_sig.hex+sequence_le)
    
    def get_unsigned_data(self):
        if self.script_sig.utxo_scriptpubkey_hex is None:
            return ""
        previous_txid_hash_le = self.reverse_bytes(self.txid)
        previous_output_index_le = self.vout_to_hex()
        script_signature_size=self.encode_varint(self.script_sig.utxo_scriptpubkey_hex).hex()
        sequence_le = struct.pack('<I', self.sequence).hex()
        
        # 全てを連結
        return (previous_txid_hash_le + previous_output_index_le +script_signature_size+ self.script_sig.utxo_scriptpubkey_hex+sequence_le)
    
    
    def serialize_witness(self):
        if not self.txinwitness:
            return "00"
        stack_items = struct.pack('<B', len(self.txinwitness)).hex()
        size_item="".join([self.encode_varint(txinwitness).hex()+txinwitness for txinwitness  in self.txinwitness])
        return (stack_items+size_item)
    
    def is_coinbase(self):
        return self.txid=="0"*64 
    
    @classmethod
    def from_hex(cls,hex:str):
        data = bytes.fromhex(hex)
        offset = 0
        # 1. Previous TXID (32バイト、リトルエンディアン)
        if offset + 32 > len(data):
            raise ValueError("TXIDのデータが不足しています")
        previous_txid_le = data[offset:offset+32]
        txid = previous_txid_le[::-1].hex()
        offset += 32
        
        # 2. Previous Output Index (4バイト、リトルエンディアン)
        if offset + 4 > len(data):
            raise ValueError("Output Indexのデータが不足しています")
        vout = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        
        # 3. Script Signature Size (varint)
        script_sig_size, offset = BaseBitcoinEntity.decode_varint(data, offset)
        
        # 4. Script Signature
        if offset + script_sig_size > len(data):
            raise ValueError("Script Signatureのデータが不足しています")
        
        script_sig = data[offset:offset+script_sig_size].hex()
        offset += script_sig_size
        
        # 5. Sequence (4バイト、リトルエンディアン)
        if offset + 4 > len(data):
            raise ValueError("Sequenceのデータが不足しています")
        
        sequence = struct.unpack('<I', data[offset:offset+4])[0]
        offset += 4
        
        instance=cls(txid=txid,vout=vout,scriptsigsize=script_sig_size,script_sig=BitcoinTransactionScriptSignature(hex=script_sig),sequence=sequence,raw_data=hex)
        return instance

ScriptPubkeyType = Literal["P2PK","P2PKH","P2SH","P2WPKH","P2WSH","P2SH-P2WPKH","P2SH-P2WSH","P2TR","OP_RETURN","Nonstandard Scripts"]

class BitcoinTransactionScriptPubkey(BaseModel):
    asm:Optional[str] = Field(None,description="デジタル署名とトランザクションをアンロックするためのスクリプト（asm形式）")
    hex:str = Field(...,description="デジタル署名とトランザクションをアンロックするためのスクリプト（16進数文字列）")
    type:Optional[ScriptPubkeyType]=None

class BitcoinTransactionOutput(BaseBitcoinEntity):
    parent_id:str=""
    value:int = Field(..., ge=1, le=2**64 - 1, description="送金額 (サトシ単位: 1 BTC = 100,000,000 satoshi)")
    n:Optional[int]=None
    script_pubkey:BitcoinTransactionScriptPubkey
    raw_data:Optional[str]=None #データを一意にするため本来のrawdataの先頭にnを追加。valueとscript_pubkeyが完全に一致するとレコード格納時にエラーになる。

    def serialize(self):
        """
        ハッシュ計算前の生データを生成
        """
        amount_le = struct.pack('<Q', self.value).hex()
        script_pubkey_size=self.encode_varint(self.script_pubkey.hex).hex()
        
        # 全てを連結
        return (amount_le +script_pubkey_size+ self.script_pubkey.hex)
    
    def _is_hex_string(self,s:str):
        try:
            int(s, 16)
            return True
        except ValueError:
            return False
        
    
    def get_script(self):
        script=Script.from_raw(self.script_pubkey.hex)
        return script.get_script()
    
    def get_pkh(self):
        for s in self.get_script():
            if self._is_hex_string(s):
                if len(s)==40:
                    return str(s)
                else:
                    return None
            else:
                continue
            
    def to_rawkey(self,with_n:bool=True):
        raw_data=self.serialize() 
        num = struct.pack('<B', self.n).hex() if with_n else ""
        
        return (num+raw_data)
    
    @classmethod
    def from_hex(cls,hex:str):
        # hex文字列をバイト配列に変換
        print("hex",hex)
        data = bytes.fromhex(hex)
        offset = 0
        
        # 1. Output Index (1バイト)
        if offset + 1 > len(data):
            raise ValueError("出力インデックスのデータが不足しています")
        
        n = struct.unpack('<B', data[offset:offset+1])[0]
        offset += 1
        
        # 2. Amount/Value (8バイト、リトルエンディアン)
        if offset + 8 > len(data):
            raise ValueError("Amountのデータが不足しています")
        
        value = struct.unpack('<Q', data[offset:offset+8])[0]
        offset += 8
        
        # 3. Script PubKey Size (varint)
        script_pubkey_size, offset = BaseBitcoinEntity.decode_varint(data, offset)
        
        # 4. Script PubKey
        if offset + script_pubkey_size > len(data):
            raise ValueError("Script PubKeyのデータが不足しています")
        
        script_pubkey = data[offset:offset+script_pubkey_size].hex()
        offset += script_pubkey_size
        
        instance=cls(value=value,script_pubkey=BitcoinTransactionScriptPubkey(hex=script_pubkey),n=n,raw_data=hex)
        return instance
                
        

class BitcoinTransactionStackItem(BaseBitcoinEntity):
    item:str= Field(...,description="The data to be pushed on to the stack (16進数文字列)",example="")
    
    def serialize(self):
        size = self.encode_varint(self.item).hex()
        return (size +self.item)


class TransactionRequest(BaseBitcoinEntity):
    version:int= Field(..., ge=1, le=2**32 - 1, description="ブロックバージョン番号")
    locktime:int= Field(..., ge=0, le=2**32 - 1, description="トランザクションが有効になる時刻またはブロック高 (0=即座に有効)")
    vin:List[BitcoinTransactionInput]
    outputs:List[BitcoinTransactionOutput]
    sighash:int=Field(default=1,description="default=1 (SIGHASH_ALL)")
    
    def get_hash_message(self):
        version_hex=self.int_to_hex(self.version)
        input_counts=struct.pack('B', len(self.vin)).hex() #必ず1つ？
        input_raw="".join([txin.get_unsigned_data()  for txin in self.vin if txin is not None]) #全部のinput?
        output_counts=struct.pack('B', (len(self.outputs))).hex()
        outputs_raw="".join([txout.to_rawkey(with_n=False) for txout in self.outputs if txout is not None])
        locktime_hex=self.int_to_hex(self.locktime)
        sighash_hex=self.int_to_hex(self.sighash)
        
        transaction_raw_data=version_hex+input_counts+input_raw+output_counts+outputs_raw+locktime_hex+sighash_hex
        hash_data=self.calculate_hash(transaction_raw_data,is_reverse=False)
        return hash_data,transaction_raw_data
    
    

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
    sighash:Optional[int]=None
    

    def _get_base_transaction_data(self) -> str:
        """
        共通のトランザクションデータ部分を生成（witness除く）
        """
        version_le = struct.pack('<I', self.version).hex()
        input_count = struct.pack('<B', len(self.vin)).hex()
        input_data = "".join([input.serialize_legacy() for input in self.vin])
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
        return "".join([vin.serialize_witness() for vin in self.vin])

    
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
        input_data = "".join([input.serialize_legacy() for input in self.vin])
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
    
    def sighash_to_hex(self):
        if self.sighash is None:
            return ""
        hex_bytes_le=struct.pack('<I', self.sighash)
        return hex_bytes_le.hex()
    
    
    
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
        for v in instance.vin:
            v.parent_id=instance.txid
            v.raw_data=v.serialize_legacy()
        for i,o in enumerate(instance.outputs):
            o.parent_id=instance.txid
            o.n=i
            o.raw_data=o.to_rawkey()
            
        return instance
    
    @classmethod
    def from_trancsation_entity(cls, entity: "TransactionTableEntity") :
        vin_raw_data:List[str]=json.loads(entity.vin)
        output_raw_data:List[str]=json.loads(entity.outputs)
        vin=[BitcoinTransactionInput.from_hex(v_str) for v_str in vin_raw_data]
        
        outputs=[BitcoinTransactionOutput.from_hex(o_str) for o_str in output_raw_data]
        
        return BitcoinTransaction(txid=entity.RowKey,vin=vin,outputs=outputs,
                **entity.model_dump(exclude={"PartitionKey","RowKey","vin","outputs","txid"}))

class TransactionVinTableEntity(BaseModel):
    PartitionKey: str 
    RowKey: str
    txid:str = Field(..., min_length=64, max_length=64, description="前のトランザクションのハッシュ値（16進数文字列）")
    vout:str= Field(...) #テーブル格納時にint64で自動的にキャストされないためstr型
    script_sig_hex:str
    utxo_scriptpubkey_hex:Optional[str]=None
    txinwitness:Optional[str]=None
    sequence:str= Field(...) #テーブル格納時にint64で自動的にキャストされないためstr型
    
    def to_transaction_vin(self) :
        deserialized_txinwitness= json.loads(self.txinwitness)
        deserialized_script_sig=BitcoinTransactionScriptSignature(hex=self.script_sig_hex,utxo_scriptpubkey_hex=self.utxo_scriptpubkey_hex)
        deserialized_vout=int(self.vout)
        deserialized_sequence=int(self.sequence)
        return BitcoinTransactionInput(parent_id=self.PartitionKey,raw_data=self.RowKey,txinwitness=deserialized_txinwitness,script_sig=deserialized_script_sig,vout=deserialized_vout,sequence=deserialized_sequence,
                       **self.model_dump(exclude={"PartitionKey","RowKey","txinwitness","script_sig_hex","vout","sequence","utxo_scriptpubkey_hex"}))
        
    
    @classmethod
    def from_transaction_vin(cls, transaction_vin: BitcoinTransactionInput) :
        raw_data=transaction_vin.serialize_legacy()
        serialized_txinwitness = json.dumps([str(v.id) for v in transaction_vin.txinwitness], ensure_ascii=False) if transaction_vin.txinwitness else "[]"
        serialized_script_sig=transaction_vin.script_sig.hex
        serialized_utxo_scriptpubkey_hex=transaction_vin.script_sig.utxo_scriptpubkey_hex
        serialized_vout=str(transaction_vin.vout)
        serialized_sequence=str(transaction_vin.sequence)
        
        return cls(PartitionKey=transaction_vin.parent_id,RowKey=raw_data,txinwitness=serialized_txinwitness,script_sig_hex=serialized_script_sig,vout=serialized_vout,sequence=serialized_sequence,utxo_scriptpubkey_hex=serialized_utxo_scriptpubkey_hex,
                   **transaction_vin.model_dump(exclude={"PartitionKey","RowKey","txinwitness","script_sig","vout","sequence"}))
    
    
    @classmethod
    def from_entity(cls, entity: TableEntity) :
        entity_dict = dict(entity)
        table_entity = TransactionVinTableEntity.model_validate(entity_dict)
        return table_entity

class TransactionOutputTableEntity(BaseModel):
    PartitionKey: str
    RowKey: str
    value:str = Field(...,) #INT64に対応できるようにstr型
    n:Optional[int]=None
    script_pubkey_hex:str

    def to_transaction_output(self) :
        deserialized_value= int(self.value)
        deserialized_script_pubkey=BitcoinTransactionScriptPubkey(hex=self.script_pubkey_hex)
        return BitcoinTransactionOutput(parent_id=self.PartitionKey,raw_data=self.RowKey,value=deserialized_value,script_pubkey=deserialized_script_pubkey,
                       **self.model_dump(exclude={"PartitionKey","RowKey","value","script_pubkey_hex"}))
    
    @classmethod
    def from_transaction_output(cls, transaction_output: BitcoinTransactionOutput) :
        raw_data=transaction_output.to_rawkey()
        serialized_value=str(transaction_output.value)
        serialized_script_pubkey=transaction_output.script_pubkey.hex
        
        return cls(PartitionKey=transaction_output.parent_id,RowKey=raw_data,value=serialized_value,script_pubkey_hex=serialized_script_pubkey,
                   **transaction_output.model_dump(exclude={"PartitionKey","RowKey","value","script_pubkey"}))
    
    @classmethod
    def from_entity(cls, entity: TableEntity) :
        entity_dict = dict(entity)
        table_entity = TransactionOutputTableEntity.model_validate(entity_dict)
        return table_entity
      

class TransactionTableEntity(BaseModel):
    PartitionKey: str ="coin_transaction"
    RowKey: str= Field(..., min_length=64, max_length=64, description="")
    txid:str
    wtxid:Optional[str]= None
    version:int= Field(..., ge=1, le=2**32 - 1, description="ブロックバージョン番号")
    size:Optional[int]=None
    weight:Optional[int]=None
    locktime:int= Field(..., ge=0, le=2**32 - 1, description="トランザクションが有効になる時刻またはブロック高 (0=即座に有効)")
    vin:Optional[str]=None
    outputs:Optional[str]=None
    blockhash:Optional[str]= Field(None, min_length=64, max_length=64, description="")
    sighash:Optional[int]=None
    
    #vinとoutputsの全情報がないためトランザクションデータの変換は不可
    # def to_transaction(self) :
    #     deserialized_id=uuid.UUID(self.RowKey)
    #     return BitcoinTransaction(id=deserialized_id,
    #                    **self.model_dump(exclude={"PartitionKey","RowKey",}))
        
    
    @classmethod
    def from_transaction(cls, tran: BitcoinTransaction) :
        serialized_id=tran.txid
        serialized_vin = json.dumps([str(v.raw_data) for v in tran.vin], ensure_ascii=False) if tran.vin else "[]"
        serialized_outputs = json.dumps([str(v.to_rawkey()) for v in tran.outputs], ensure_ascii=False) if tran.outputs else "[]"
        
        return cls(RowKey=serialized_id,vin=serialized_vin,outputs=serialized_outputs,
                   **tran.model_dump(exclude={"PartitionKey","RowKey","vin","outputs"}))
        
    
    @classmethod
    def from_entity(cls, entity: TableEntity) :
        entity_dict = dict(entity)
        table_entity = TransactionTableEntity.model_validate(entity_dict)
        return table_entity
        

class BitcoinAddress(BaseBitcoinEntity):
    id:uuid.UUID=Field(default_factory=uuid.uuid4)
    private_key:Optional[str]=None
    public_key:Optional[str]=None
    p2pkh_address:Optional[str]=None
    p2wpkh_address:Optional[str]=None
    p2pkh_scriptpubkey:Optional[str]=None
    p2wpkh_scriptpubkey:Optional[str]=None
    
    def to_hash160(self):
        if self.public_key is None:
            return
        byte_data = bytes.fromhex(self.public_key)
        sha256_hash = hashlib.sha256(byte_data).digest()
        ripemd160_hash = hashlib.new('ripemd160', sha256_hash).hexdigest()
        return ripemd160_hash
    
    def calculate_p2pkhaddress(self):
        if not self.private_key:
            return None
        pk=PrivateKey(b=bytes.fromhex(self.private_key))
        to_hash160=pk.get_public_key().to_hash160()
        pre_hash160="00"+to_hash160
        cksum=self.calculate_hash(pre_hash160,False)
        raw_data=pre_hash160+cksum[:8]
        p2pkhaddress=b58encode(binascii.unhexlify(raw_data)).decode()
        return p2pkhaddress
    
    def calculate_p2wpkhaddress(self):
        if not self.private_key:
            return None
        
        pk = PrivateKey(b=bytes.fromhex(self.private_key))
        to_hash160 = pk.get_public_key().to_hash160()
        all_bits = "".join([format(byte, '08b') for byte in binascii.unhexlify(to_hash160)])
        five_bit_groups = []
        for i in range(0, len(all_bits), 5):
            five_bit_group = all_bits[i:i+5]
            five_bit_groups.append(int(five_bit_group, 2))
        
        data_for_checksum = [0] + five_bit_groups
        # checksum = bech32.bech32_create_checksum(hrp="bc", data=data_for_checksum)
        # encode_tar=data_for_checksum+checksum
        
        bech32_data=bech32.bech32_encode(hrp="bc",data=data_for_checksum)
        
        return bech32_data
    
    @classmethod
    def generate_address(cls,id:Optional[str]=None,private_key:Optional[str]=None):
        pk_hex=private_key if private_key else hashlib.sha256(uuid.uuid4().bytes).hexdigest()
        pk=PrivateKey(b=bytes.fromhex(pk_hex))
        instance=cls(private_key=pk_hex,public_key=pk.get_public_key().to_hex())
        instance.id=id if id is not None else instance.id 
        instance.p2pkh_address=instance.calculate_p2pkhaddress()
        instance.p2wpkh_address=instance.calculate_p2wpkhaddress()
        instance.p2pkh_scriptpubkey=instance.get_scriptpubkey("p2pkh")
        instance.p2wpkh_scriptpubkey=instance.get_scriptpubkey("p2pwpkh")
        
        return instance
    
    
    def get_scriptpubkey(self,type:Literal["p2pkh","p2pwpkh"]):
        if type=="p2pkh":
            if self.p2pkh_address is None:
                print(f"p2pkh_addressが空です")
                return
            
            decode_str=b58decode(self.p2pkh_address).hex()
            ##todo チェックサム検証
            prefix = decode_str[:2]       
            hash160 = decode_str[2:42]      
            checksum = decode_str[42:]       
            
            ##
            scriptpubkey="76a914"+hash160+"88ac"
            return scriptpubkey
            
        elif type=="p2pwpkh":
            if self.p2wpkh_address is None:
                print(f"p2wpkh_addressが空です")
                return
            
            decoded_bech32= bech32.bech32_decode(self.p2wpkh_address)
            if decoded_bech32[0] is None or decoded_bech32[1] is None:
                print(f"bech32_decode不可")
                return
            
            bit_strings = "".join([format(num, '05b') for num in decoded_bech32[1][1:]])
            hex_groups:List[str] = []
            for i in range(0, len(bit_strings), 8):
                hex_str = format(int(bit_strings[i:i+8],2), '02x') 
                hex_groups.append(hex_str)
            return "".join(hex_groups)
        else:
            print("有効なtypeを指定してください")
            return
        
    
    
    def sign_with_low_s(self, private_key: ec.EllipticCurvePrivateKey, message_hex: str):
        SECP256K1_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
        
        try:
            message_bytes = bytes.fromhex(message_hex)
            signature = private_key.sign(message_bytes, ec.ECDSA(Prehashed(hashes.SHA256())))
            r, s = decode_dss_signature(signature)
            if s > SECP256K1_ORDER // 2:
                s = SECP256K1_ORDER - s
                signature = encode_dss_signature(r, s)
                print(f"Converted to Low-S: s = {hex(s)}")
            else:
                print(f"Already Low-S: s = {hex(s)}")
            
            # 検証
            is_low_s = s <= SECP256K1_ORDER // 2
            
            return signature,r,s
            
        except ValueError as e:
            raise ValueError(f"16進文字列の変換に失敗: {e}")
        except Exception as e:
            raise Exception(f"署名生成に失敗: {e}")
    
    def to_privatekey_object(self):
        if self.private_key is None:
            return
        private_key_bytes = bytes.fromhex(self.private_key)
        privatekey_object = ec.derive_private_key(
            int.from_bytes(private_key_bytes, 'big'),
            ec.SECP256K1()
        )
        return privatekey_object
    
    
    def encode_integer_der(self,value: int) -> bytes:
        """整数をDER INTEGER形式でエンコード"""
        # 整数をバイト配列に変換（最小限のバイト数）
        byte_length = (value.bit_length() + 7) // 8
        if byte_length == 0:
            byte_length = 1
        
        value_bytes = value.to_bytes(byte_length, 'big')
        
        # 最上位ビットが1の場合、0x00を前置してポジティブにする
        if value_bytes[0] & 0x80:
            value_bytes = b'\x00' + value_bytes
        
        # DER INTEGER: 0x02 + 長さ + 値
        length = len(value_bytes)
        return bytes([0x02, length]) + value_bytes

    def encode_ecdsa_signature_der(self,r: int, s: int) -> bytes:
        """r値とs値からDER署名を生成"""
        # r値とs値をそれぞれDER INTEGER形式にエンコード
        r_encoded = self.encode_integer_der(r)
        s_encoded = self.encode_integer_der(s)
        
        # SEQUENCE内容を結合
        sequence_content = r_encoded + s_encoded
        
        # DER SEQUENCE: 0x30 + 長さ + 内容
        sequence_length = len(sequence_content)
        der_signature = bytes([0x30, sequence_length]) + sequence_content
        
        return der_signature

    def analyze_der_signature(self,signature_hex: str):
        """DER署名を詳細に分析"""
        signature_bytes = bytes.fromhex(signature_hex)
        
        print(f"DER署名分析: {signature_hex}")
        print(f"総長: {len(signature_bytes)} バイト")
        print()
        
        offset = 0
        
        # SEQUENCE開始
        seq_type = signature_bytes[offset]
        seq_length = signature_bytes[offset + 1]
        print(f"SEQUENCE:")
        print(f"  type: {seq_type:02x} (0x30)")
        print(f"  length: {seq_length:02x} ({seq_length} バイト)")
        offset += 2
        
        # r値
        r_type = signature_bytes[offset]
        r_length = signature_bytes[offset + 1]
        r_bytes = signature_bytes[offset + 2:offset + 2 + r_length]
        r_value = int.from_bytes(r_bytes, 'big')
        
        print(f"  r INTEGER:")
        print(f"    type: {r_type:02x} (0x02)")
        print(f"    length: {r_length:02x} ({r_length} バイト)")
        print(f"    value: {r_bytes.hex()}")
        print(f"    decimal: {r_value}")
        offset += 2 + r_length
        
        # s値
        s_type = signature_bytes[offset]
        s_length = signature_bytes[offset + 1]
        s_bytes = signature_bytes[offset + 2:offset + 2 + s_length]
        s_value = int.from_bytes(s_bytes, 'big')
        
        print(f"  s INTEGER:")
        print(f"    type: {s_type:02x} (0x02)")
        print(f"    length: {s_length:02x} ({s_length} バイト)")
        print(f"    value: {s_bytes.hex()}")
        print(f"    decimal: {s_value}")
        
        return r_value, s_value


        