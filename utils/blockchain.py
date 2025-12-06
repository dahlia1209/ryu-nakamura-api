from typing import Dict, Optional, Tuple,List,Literal,get_args
from pydantic import BaseModel, Field, field_validator, computed_field, model_validator
import hashlib
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
from coincurve import PublicKey
from datetime import datetime

class Base(BaseModel):
    def hash256_hex(self, hex_string: str, is_little: bool = True) -> str:
        data = bytes.fromhex(hex_string)
        hash1 = hashlib.sha256(data).digest()
        hash2 = hashlib.sha256(hash1).digest()
        hash256 = hash2.hex()
        if is_little:
            hash256 = self.hex_to_little_endian(hash256)
        return hash256

    def hex_to_little_endian(self, hex_string: str) -> str:
        return bytes.fromhex(hex_string)[::-1].hex()

    def int_to_hex(self, num: int, byte_size: int, is_little: bool = True) -> str:
        return num.to_bytes(byte_size, byteorder="little" if is_little else "big").hex()

    def hex_to_int(self, hex_string: str, is_little: bool = True) -> int:
        return int.from_bytes(
            bytes.fromhex(hex_string), byteorder="little" if is_little else "big"
        )

    def int_to_compact_size(self, value: int) -> str:
        if value < 0:
            raise ValueError("値は0以上である必要があります")
        if value < 253:
            return self.int_to_hex(value, 1)
        elif value <= 0xFFFF:  # 65535
            return "fd" + self.int_to_hex(value, 2)
        elif value <= 0xFFFFFFFF:  # 4294967295
            return "fe" + self.int_to_hex(value, 4)
        elif value <= 0xFFFFFFFFFFFFFFFF:  # 18446744073709551615
            return "ff" + self.int_to_hex(value, 8)
        else:
            raise ValueError(f"値が大きすぎます.{value}")

    def compact_size_to_int(self, data: str) -> int:
        if len(data) == 0:
            raise ValueError("データが空です")
        # 先頭バイトを取得
        leading_byte = self.hex_to_int(data[:2])
        # 長さとleading byteの組み合わせで検証・デコード
        if len(data) == 2:
            if leading_byte < 0xFD:  # 253未満
                return leading_byte
            else:
                raise ValueError(
                    f"compact sizeの形式が不正です。2桁の場合は0xFD未満である必要があります: {data}"
                )

        elif len(data) == 6:
            if leading_byte != 0xFD:
                raise ValueError(
                    f"compact sizeの形式が不正です。6桁の場合は先頭が0xFDである必要があります: {data}"
                )
            return self.hex_to_int(data[2:])

        elif len(data) == 10:
            if leading_byte != 0xFE:
                raise ValueError(
                    f"compact sizeの形式が不正です。10桁の場合は先頭が0xFEである必要があります: {data}"
                )
            return self.hex_to_int(data[2:])

        elif len(data) == 18:
            if leading_byte != 0xFF:
                raise ValueError(
                    f"compact sizeの形式が不正です。18桁の場合は先頭が0xFFである必要があります: {data}"
                )
            return self.hex_to_int(data[2:])

        else:
            raise ValueError(
                f"compact sizeの桁数は2,6,10,18桁である必要があります。実際: {len(data)}桁, データ: {data}"
            )

# Bitcoin Script Opcodeマッピング表
OPCODE_MAP: Dict[int, str] = {
    0x00: 'OP_0',
    0x01: 'OP_PUSHBYTES_1',
    0x02: 'OP_PUSHBYTES_2',
    0x03: 'OP_PUSHBYTES_3',
    0x04: 'OP_PUSHBYTES_4',
    0x05: 'OP_PUSHBYTES_5',
    0x06: 'OP_PUSHBYTES_6',
    0x07: 'OP_PUSHBYTES_7',
    0x08: 'OP_PUSHBYTES_8',
    0x09: 'OP_PUSHBYTES_9',
    0x0a: 'OP_PUSHBYTES_10',
    0x0b: 'OP_PUSHBYTES_11',
    0x0c: 'OP_PUSHBYTES_12',
    0x0d: 'OP_PUSHBYTES_13',
    0x0e: 'OP_PUSHBYTES_14',
    0x0f: 'OP_PUSHBYTES_15',
    0x10: 'OP_PUSHBYTES_16',
    0x11: 'OP_PUSHBYTES_17',
    0x12: 'OP_PUSHBYTES_18',
    0x13: 'OP_PUSHBYTES_19',
    0x14: 'OP_PUSHBYTES_20',
    0x15: 'OP_PUSHBYTES_21',
    0x16: 'OP_PUSHBYTES_22',
    0x17: 'OP_PUSHBYTES_23',
    0x18: 'OP_PUSHBYTES_24',
    0x19: 'OP_PUSHBYTES_25',
    0x1a: 'OP_PUSHBYTES_26',
    0x1b: 'OP_PUSHBYTES_27',
    0x1c: 'OP_PUSHBYTES_28',
    0x1d: 'OP_PUSHBYTES_29',
    0x1e: 'OP_PUSHBYTES_30',
    0x1f: 'OP_PUSHBYTES_31',
    0x20: 'OP_PUSHBYTES_32',
    0x21: 'OP_PUSHBYTES_33',
    0x22: 'OP_PUSHBYTES_34',
    0x23: 'OP_PUSHBYTES_35',
    0x24: 'OP_PUSHBYTES_36',
    0x25: 'OP_PUSHBYTES_37',
    0x26: 'OP_PUSHBYTES_38',
    0x27: 'OP_PUSHBYTES_39',
    0x28: 'OP_PUSHBYTES_40',
    0x29: 'OP_PUSHBYTES_41',
    0x2a: 'OP_PUSHBYTES_42',
    0x2b: 'OP_PUSHBYTES_43',
    0x2c: 'OP_PUSHBYTES_44',
    0x2d: 'OP_PUSHBYTES_45',
    0x2e: 'OP_PUSHBYTES_46',
    0x2f: 'OP_PUSHBYTES_47',
    0x30: 'OP_PUSHBYTES_48',
    0x31: 'OP_PUSHBYTES_49',
    0x32: 'OP_PUSHBYTES_50',
    0x33: 'OP_PUSHBYTES_51',
    0x34: 'OP_PUSHBYTES_52',
    0x35: 'OP_PUSHBYTES_53',
    0x36: 'OP_PUSHBYTES_54',
    0x37: 'OP_PUSHBYTES_55',
    0x38: 'OP_PUSHBYTES_56',
    0x39: 'OP_PUSHBYTES_57',
    0x3a: 'OP_PUSHBYTES_58',
    0x3b: 'OP_PUSHBYTES_59',
    0x3c: 'OP_PUSHBYTES_60',
    0x3d: 'OP_PUSHBYTES_61',
    0x3e: 'OP_PUSHBYTES_62',
    0x3f: 'OP_PUSHBYTES_63',
    0x40: 'OP_PUSHBYTES_64',
    0x41: 'OP_PUSHBYTES_65',
    0x42: 'OP_PUSHBYTES_66',
    0x43: 'OP_PUSHBYTES_67',
    0x44: 'OP_PUSHBYTES_68',
    0x45: 'OP_PUSHBYTES_69',
    0x46: 'OP_PUSHBYTES_70',
    0x47: 'OP_PUSHBYTES_71',
    0x48: 'OP_PUSHBYTES_72',
    0x49: 'OP_PUSHBYTES_73',
    0x4a: 'OP_PUSHBYTES_74',
    0x4b: 'OP_PUSHBYTES_75',
    0x4c: 'OP_PUSHDATA1',
    0x4d: 'OP_PUSHDATA2',
    0x4e: 'OP_PUSHDATA4',
    0x4f: 'OP_1NEGATE',
    0x50: 'OP_RESERVED',
    0x51: 'OP_1',
    0x52: 'OP_2',
    0x53: 'OP_3',
    0x54: 'OP_4',
    0x55: 'OP_5',
    0x56: 'OP_6',
    0x57: 'OP_7',
    0x58: 'OP_8',
    0x59: 'OP_9',
    0x5a: 'OP_10',
    0x5b: 'OP_11',
    0x5c: 'OP_12',
    0x5d: 'OP_13',
    0x5e: 'OP_14',
    0x5f: 'OP_15',
    0x60: 'OP_16',
    # Flow control
    0x61: 'OP_NOP',
    0x62: 'OP_VER',
    0x63: 'OP_IF',
    0x64: 'OP_NOTIF',
    0x65: 'OP_VERIF',
    0x66: 'OP_VERNOTIF',
    0x67: 'OP_ELSE',
    0x68: 'OP_ENDIF',
    0x69: 'OP_VERIFY',
    0x6a: 'OP_RETURN',
    # Stack operations
    0x6b: 'OP_TOALTSTACK',
    0x6c: 'OP_FROMALTSTACK',
    0x6d: 'OP_2DROP',
    0x6e: 'OP_2DUP',
    0x6f: 'OP_3DUP',
    0x70: 'OP_2OVER',
    0x71: 'OP_2ROT',
    0x72: 'OP_2SWAP',
    0x73: 'OP_IFDUP',
    0x74: 'OP_DEPTH',
    0x75: 'OP_DROP',
    0x76: 'OP_DUP',
    0x77: 'OP_NIP',
    0x78: 'OP_OVER',
    0x79: 'OP_PICK',
    0x7a: 'OP_ROLL',
    0x7b: 'OP_ROT',
    0x7c: 'OP_SWAP',
    0x7d: 'OP_TUCK',
    # Splice operations (disabled)
    0x7e: 'OP_CAT',
    0x7f: 'OP_SUBSTR',
    0x80: 'OP_LEFT',
    0x81: 'OP_RIGHT',
    0x82: 'OP_SIZE',
    # Bitwise logic (some disabled)
    0x83: 'OP_INVERT',
    0x84: 'OP_AND',
    0x85: 'OP_OR',
    0x86: 'OP_XOR',
    0x87: 'OP_EQUAL',
    0x88: 'OP_EQUALVERIFY',
    0x89: 'OP_RESERVED1',
    0x8a: 'OP_RESERVED2',
    # Arithmetic
    0x8b: 'OP_1ADD',
    0x8c: 'OP_1SUB',
    0x8d: 'OP_2MUL',
    0x8e: 'OP_2DIV',
    0x8f: 'OP_NEGATE',
    0x90: 'OP_ABS',
    0x91: 'OP_NOT',
    0x92: 'OP_0NOTEQUAL',
    0x93: 'OP_ADD',
    0x94: 'OP_SUB',
    0x95: 'OP_MUL',
    0x96: 'OP_DIV',
    0x97: 'OP_MOD',
    0x98: 'OP_LSHIFT',
    0x99: 'OP_RSHIFT',
    0x9a: 'OP_BOOLAND',
    0x9b: 'OP_BOOLOR',
    0x9c: 'OP_NUMEQUAL',
    0x9d: 'OP_NUMEQUALVERIFY',
    0x9e: 'OP_NUMNOTEQUAL',
    0x9f: 'OP_LESSTHAN',
    0xa0: 'OP_GREATERTHAN',
    0xa1: 'OP_LESSTHANOREQUAL',
    0xa2: 'OP_GREATERTHANOREQUAL',
    0xa3: 'OP_MIN',
    0xa4: 'OP_MAX',
    0xa5: 'OP_WITHIN',
    # Crypto
    0xa6: 'OP_RIPEMD160',
    0xa7: 'OP_SHA1',
    0xa8: 'OP_SHA256',
    0xa9: 'OP_HASH160',
    0xaa: 'OP_HASH256',
    0xab: 'OP_CODESEPARATOR',
    0xac: 'OP_CHECKSIG',
    0xad: 'OP_CHECKSIGVERIFY',
    0xae: 'OP_CHECKMULTISIG',
    0xaf: 'OP_CHECKMULTISIGVERIFY',
    # Locktime
    0xb0: 'OP_NOP1',
    0xb1: 'OP_CHECKLOCKTIMEVERIFY',
    0xb2: 'OP_CHECKSEQUENCEVERIFY',
    0xb3: 'OP_NOP4',
    0xb4: 'OP_NOP5',
    0xb5: 'OP_NOP6',
    0xb6: 'OP_NOP7',
    0xb7: 'OP_NOP8',
    0xb8: 'OP_NOP9',
    0xb9: 'OP_NOP10',
    0xba: 'OP_CHECKSIGADD',
    # Reserved opcodes (OP_RETURN_187 to OP_RETURN_254)
    0xbb: 'OP_RETURN_187',
    0xbc: 'OP_RETURN_188',
    0xbd: 'OP_RETURN_189',
    0xbe: 'OP_RETURN_190',
    0xbf: 'OP_RETURN_191',
    0xc0: 'OP_RETURN_192',
    0xc1: 'OP_RETURN_193',
    0xc2: 'OP_RETURN_194',
    0xc3: 'OP_RETURN_195',
    0xc4: 'OP_RETURN_196',
    0xc5: 'OP_RETURN_197',
    0xc6: 'OP_RETURN_198',
    0xc7: 'OP_RETURN_199',
    0xc8: 'OP_RETURN_200',
    0xc9: 'OP_RETURN_201',
    0xca: 'OP_RETURN_202',
    0xcb: 'OP_RETURN_203',
    0xcc: 'OP_RETURN_204',
    0xcd: 'OP_RETURN_205',
    0xce: 'OP_RETURN_206',
    0xcf: 'OP_RETURN_207',
    0xd0: 'OP_RETURN_208',
    0xd1: 'OP_RETURN_209',
    0xd2: 'OP_RETURN_210',
    0xd3: 'OP_RETURN_211',
    0xd4: 'OP_RETURN_212',
    0xd5: 'OP_RETURN_213',
    0xd6: 'OP_RETURN_214',
    0xd7: 'OP_RETURN_215',
    0xd8: 'OP_RETURN_216',
    0xd9: 'OP_RETURN_217',
    0xda: 'OP_RETURN_218',
    0xdb: 'OP_RETURN_219',
    0xdc: 'OP_RETURN_220',
    0xdd: 'OP_RETURN_221',
    0xde: 'OP_RETURN_222',
    0xdf: 'OP_RETURN_223',
    0xe0: 'OP_RETURN_224',
    0xe1: 'OP_RETURN_225',
    0xe2: 'OP_RETURN_226',
    0xe3: 'OP_RETURN_227',
    0xe4: 'OP_RETURN_228',
    0xe5: 'OP_RETURN_229',
    0xe6: 'OP_RETURN_230',
    0xe7: 'OP_RETURN_231',
    0xe8: 'OP_RETURN_232',
    0xe9: 'OP_RETURN_233',
    0xea: 'OP_RETURN_234',
    0xeb: 'OP_RETURN_235',
    0xec: 'OP_RETURN_236',
    0xed: 'OP_RETURN_237',
    0xee: 'OP_RETURN_238',
    0xef: 'OP_RETURN_239',
    0xf0: 'OP_RETURN_240',
    0xf1: 'OP_RETURN_241',
    0xf2: 'OP_RETURN_242',
    0xf3: 'OP_RETURN_243',
    0xf4: 'OP_RETURN_244',
    0xf5: 'OP_RETURN_245',
    0xf6: 'OP_RETURN_246',
    0xf7: 'OP_RETURN_247',
    0xf8: 'OP_RETURN_248',
    0xf9: 'OP_RETURN_249',
    0xfa: 'OP_RETURN_250',
    0xfb: 'OP_RETURN_251',
    0xfc: 'OP_RETURN_252',
    0xfd: 'OP_RETURN_253',
    0xfe: 'OP_RETURN_254',
    0xff: 'OP_INVALIDOPCODE',
}

# 逆マッピング
REVERSE_OPCODE_MAP: Dict[str, int] = {v: k for k, v in OPCODE_MAP.items()}


def get_opcode_name(hex_value: int) -> Optional[str]:
    """opcodeの数値から名前を取得"""
    return OPCODE_MAP.get(hex_value)


def get_opcode_hex(name: str) -> Optional[int]:
    """opcodeの名前から数値を取得"""
    return REVERSE_OPCODE_MAP.get(name)


def get_opcode_hex_string(name: str) -> Optional[str]:
    """opcodeの名前から16進数文字列を取得"""
    hex_value = REVERSE_OPCODE_MAP.get(name)
    return f"{hex_value:02x}" if hex_value is not None else None


def script_to_hex(script: str) -> str:
    """
    Bitcoin ScriptのASM形式を16進数に変換
    """
    tokens = script.strip().split()
    hex_result = ''
    i = 0

    while i < len(tokens):
        token = tokens[i]
        opcode_hex = get_opcode_hex(token)

        if opcode_hex is not None:
            hex_string = f"{opcode_hex:02x}"
            hex_result += hex_string

            # Push Data opcodeの場合、後続のデータを処理
            if 0x01 <= opcode_hex <= 0x4b:
                # OP_PUSHBYTES_1 to OP_PUSHBYTES_75
                i += 1
                if i < len(tokens):
                    data_bytes = tokens[i]
                    hex_result += data_bytes
            elif opcode_hex == 0x4c:
                # OP_PUSHDATA1
                i += 1
                if i < len(tokens):
                    length_byte = tokens[i]
                    hex_result += length_byte
                    i += 1
                    if i < len(tokens):
                        data_bytes = tokens[i]
                        hex_result += data_bytes
            elif opcode_hex == 0x4d:
                # OP_PUSHDATA2
                i += 1
                if i < len(tokens):
                    length_bytes = tokens[i]
                    hex_result += length_bytes
                    i += 1
                    if i < len(tokens):
                        data_bytes = tokens[i]
                        hex_result += data_bytes
            elif opcode_hex == 0x4e:
                # OP_PUSHDATA4
                i += 1
                if i < len(tokens):
                    length_bytes = tokens[i]
                    hex_result += length_bytes
                    i += 1
                    if i < len(tokens):
                        data_bytes = tokens[i]
                        hex_result += data_bytes
        else:
            # opcodeとして認識できない場合は16進数データとして扱う
            hex_result += token

        i += 1

    return hex_result

def hex_to_script(hex_string: str) -> str:
    # バイト配列に変換
    script_bytes = bytes.fromhex(hex_string)
    
    asm_parts = []
    i = 0
    
    while i < len(script_bytes):
        opcode = script_bytes[i]
        opcode_name = get_opcode_name(opcode)
        
        if opcode_name:
            asm_parts.append(opcode_name)
            
            # Push Data opcodeの処理
            if 0x01 <= opcode <= 0x4b:
                # OP_PUSHBYTES_1 to OP_PUSHBYTES_75
                data_length = opcode
                i += 1
                if i + data_length <= len(script_bytes):
                    data = script_bytes[i:i + data_length]
                    asm_parts.append(data.hex())
                    i += data_length - 1
                else:
                    raise ValueError(f"Insufficient data for OP_PUSHBYTES_{data_length}")
                    
            elif opcode == 0x4c:
                # OP_PUSHDATA1
                i += 1
                if i < len(script_bytes):
                    data_length = script_bytes[i]
                    asm_parts.append(f"{data_length:02x}")
                    i += 1
                    if i + data_length <= len(script_bytes):
                        data = script_bytes[i:i + data_length]
                        asm_parts.append(data.hex())
                        i += data_length - 1
                    else:
                        raise ValueError(f"Insufficient data for OP_PUSHDATA1")
                else:
                    raise ValueError("Missing length byte for OP_PUSHDATA1")
                    
            elif opcode == 0x4d:
                # OP_PUSHDATA2
                i += 1
                if i + 1 < len(script_bytes):
                    data_length = int.from_bytes(script_bytes[i:i+2], 'little')
                    asm_parts.append(script_bytes[i:i+2].hex())
                    i += 2
                    if i + data_length <= len(script_bytes):
                        data = script_bytes[i:i + data_length]
                        asm_parts.append(data.hex())
                        i += data_length - 1
                    else:
                        raise ValueError(f"Insufficient data for OP_PUSHDATA2")
                else:
                    raise ValueError("Missing length bytes for OP_PUSHDATA2")
                    
            elif opcode == 0x4e:
                # OP_PUSHDATA4
                i += 1
                if i + 3 < len(script_bytes):
                    data_length = int.from_bytes(script_bytes[i:i+4], 'little')
                    asm_parts.append(script_bytes[i:i+4].hex())
                    i += 4
                    if i + data_length <= len(script_bytes):
                        data = script_bytes[i:i + data_length]
                        asm_parts.append(data.hex())
                        i += data_length - 1
                    else:
                        raise ValueError(f"Insufficient data for OP_PUSHDATA4")
                else:
                    raise ValueError("Missing length bytes for OP_PUSHDATA4")
        else:
            # 未知のopcodeの場合は16進数として表示
            asm_parts.append(f"{opcode:02x}")
        
        i += 1
    
    return ' '.join(asm_parts)


def cast_to_bool(value: str) -> bool:
    """16進数文字列をブール値に変換"""
    if not value or value == '00' or value == '80':
        return False
    return True


def hex_to_int_signed(hex_str: str) -> int:
    """16進数文字列を符号付き整数に変換（Bitcoin Script形式）"""
    if not hex_str:
        return 0
    data = bytes.fromhex(hex_str)
    if len(data) == 0:
        return 0
    # 最上位ビットが符号ビット
    if data[-1] & 0x80:
        # 負の数
        data_abs = bytearray(data)
        data_abs[-1] &= 0x7f
        return -int.from_bytes(data_abs, 'little')
    else:
        return int.from_bytes(data, 'little')


def int_to_hex_signed(value: int) -> str:
    """整数を符号付き16進数文字列に変換（Bitcoin Script形式）"""
    if value == 0:
        return ''
    
    is_negative = value < 0
    abs_value = abs(value)
    
    # バイト列に変換
    if abs_value == 0:
        hex_bytes = b''
    else:
        hex_bytes = abs_value.to_bytes((abs_value.bit_length() + 7) // 8, 'little')
    
    hex_list = list(hex_bytes)
    
    if len(hex_list) == 0:
        return ''
    
    # 負の数の場合、符号ビットを設定
    if is_negative:
        if hex_list[-1] & 0x80:
            # 最上位バイトの最上位ビットが既に立っている場合、新しいバイトを追加
            hex_list.append(0x80)
        else:
            hex_list[-1] |= 0x80
    else:
        # 正の数で最上位ビットが立っている場合、0x00を追加
        if hex_list[-1] & 0x80:
            hex_list.append(0x00)
    
    return bytes(hex_list).hex()

SigHashType = Literal[
    0x01,  # SIGHASH_ALL
    0x02,  # SIGHASH_NONE
    0x03,  # SIGHASH_SINGLE
    0x81,  # SIGHASH_ANYONECANPAY | SIGHASH_ALL
    0x82,  # SIGHASH_ANYONECANPAY | SIGHASH_NONE
    0x83,  # SIGHASH_ANYONECANPAY | SIGHASH_SINGLE
]

# Literalから有効な値を取得
VALID_SIGHASH_TYPES = get_args(SigHashType)

def verify_signature(pubkey_hex: str, signature_hex: str, signature_message: str,timestamp:int) -> bool:
    
    # 1. 最小・最大サイズチェック
    if len(signature_hex) < 18:  # 最小DER署名サイズ + sighash (8+8+2 = 18バイト)
        return False
    if len(signature_hex) > 146:  # 最大DER署名サイズ + sighash (72*2+2 = 146バイト)
        return False
    
    # 2. Sighashタイプを検証
    sighash_type = int(signature_hex[-2:], 16)
    if sighash_type not in VALID_SIGHASH_TYPES:
        return False
    
    # 3. Signature取得（sighashを除く）
    signature_without_sighash = signature_hex[:-2]

    try:
        # 16進数文字列をバイト列に変換
        print("pubkey_hex,signature_without_sighash,signature_message",pubkey_hex,signature_without_sighash,signature_message)
        pubkey_bytes = bytes.fromhex(pubkey_hex)
        signature_bytes = bytes.fromhex(signature_without_sighash)
        message_bytes = bytes.fromhex(signature_message)
        # 4. 公開鍵の形式チェック
        if not is_valid_pubkey(pubkey_bytes):
            return False
        
        # 5. メッセージハッシュのサイズチェック
        if len(message_bytes) != 32:  # SHA256ハッシュは32バイト
            return False
        

        # 6. DER署名の形式チェック
        if not is_valid_der_signature(signature_bytes):
            return False
        
        # 7. Low-S値チェック
        if is_low_s(signature_bytes):
            pass
        else: #HIGH-S値
            if timestamp >= int(datetime(2014, 3, 12).timestamp()):# 2014年3月12日以降はBIP62適用 https://github.com/bitcoin/bips/blob/master/bip-0062.mediawiki
                return False
            else: # 2014年3月12日以前であれば正規化
                signature_bytes=normalize_to_low_s(signature_bytes)
        
        
        # 8. R, S値の範囲チェック（0 < r,s < n）
        if not is_valid_r_s_range(signature_bytes):
            return False
        
        # 9. 公開鍵オブジェクトを作成して署名を検証
        print("9. 公開鍵オブジェクトを作成して署名を検証")
        pubkey_object = PublicKey(pubkey_bytes)
        return pubkey_object.verify(
            signature_bytes,
            message_bytes,
            hasher=None
        )
        
    except (ValueError, TypeError) as e:
        return False
    except Exception:
        return False


def is_valid_pubkey(pubkey_bytes: bytes) -> bool:
    if len(pubkey_bytes) == 33:
        # 圧縮公開鍵: 0x02 or 0x03 + 32バイト
        return pubkey_bytes[0] in (0x02, 0x03)
    elif len(pubkey_bytes) == 65:
        # 非圧縮公開鍵: 0x04 + 64バイト
        return pubkey_bytes[0] == 0x04
    else:
        return False


def is_valid_der_signature(signature_der: bytes) -> bool:
    try:
        # 最小長チェック
        if len(signature_der) < 8:
            return False
        
        # DERシーケンスタグチェック
        if signature_der[0] != 0x30:
            return False
        
        # 全体の長さチェック
        total_length = signature_der[1]
        if total_length + 2 != len(signature_der):
            return False
        
        # R値のチェック
        if signature_der[2] != 0x02:  # INTEGERタグ
            return False
        
        r_length = signature_der[3]
        if r_length == 0 or r_length > 33:  # R値は最大33バイト
            return False
        
        # R値の先頭バイトチェック（負数でない、不要なゼロパディングなし）
        r_start = 4
        if signature_der[r_start] & 0x80:  # 負数は不正
            return False
        if r_length > 1 and signature_der[r_start] == 0x00:
            if not (signature_der[r_start + 1] & 0x80):  # 不要なゼロパディング
                return False
        
        # S値のチェック
        s_start = r_start + r_length
        if signature_der[s_start] != 0x02:  # INTEGERタグ
            return False
        
        s_length = signature_der[s_start + 1]
        if s_length == 0 or s_length > 33:  # S値は最大33バイト
            return False
        
        # S値の先頭バイトチェック
        s_value_start = s_start + 2
        if signature_der[s_value_start] & 0x80:  # 負数は不正
            return False
        if s_length > 1 and signature_der[s_value_start] == 0x00:
            if not (signature_der[s_value_start + 1] & 0x80):  # 不要なゼロパディング
                return False
        
        # 全体の長さ確認
        if s_value_start + s_length != len(signature_der):
            return False
        
        return True
        
    except (IndexError, ValueError):
        return False


def is_valid_r_s_range(signature_der: bytes) -> bool:
    SECP256K1_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    
    try:
        # R値の取得
        r_length = signature_der[3]
        r_bytes = signature_der[4:4 + r_length]
        r_value = int.from_bytes(r_bytes, byteorder='big')
        
        # S値の取得
        s_offset = 4 + r_length + 2
        s_length = signature_der[s_offset - 1]
        s_bytes = signature_der[s_offset:s_offset + s_length]
        s_value = int.from_bytes(s_bytes, byteorder='big')
        
        # 範囲チェック: 0 < r < n, 0 < s < n
        if r_value == 0 or r_value >= SECP256K1_ORDER:
            return False
        if s_value == 0 or s_value >= SECP256K1_ORDER:
            return False
        
        return True
        
    except (IndexError, ValueError):
        return False


def is_low_s(signature_der: bytes) -> bool:
    SECP256K1_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    HALF_ORDER = SECP256K1_ORDER // 2
    
    try:
        # R値の長さを取得
        r_length = signature_der[3]
        
        # S値の取得 (修正版)
        s_tag_offset = 4 + r_length  # INTEGERタグの位置
        s_length = signature_der[s_tag_offset + 1]  # 長さはタグの次
        s_bytes = signature_der[s_tag_offset + 2:s_tag_offset + 2 + s_length]
        s_value = int.from_bytes(s_bytes, byteorder='big')
        
        # S値がHALF_ORDER以下であることを確認
        return s_value <= HALF_ORDER
        
    except (IndexError, ValueError):
        return False
    
def normalize_to_low_s(sig: bytes) -> bytes:
    ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    
    # R値の長さと位置
    r_len = sig[3]
    r = sig[4:4 + r_len]
    
    # S値の位置と長さ
    s_off = 4 + r_len + 2
    s_len = sig[s_off - 1]
    s = sig[s_off:s_off + s_len]
    
    # S値をintに変換
    s_val = int.from_bytes(s, 'big')
    
    # High-S値の場合のみ正規化
    if s_val > ORDER // 2:
        s_val = ORDER - s_val
        # intをバイト列に変換（先頭の0x00を削除）
        s = s_val.to_bytes(32, 'big').lstrip(b'\x00')
        
        # 最上位ビットが1の場合、0x00を追加（DER形式の要件）
        if s[0] & 0x80:
            s = b'\x00' + s
    
    # DER形式で再構築
    r_der = b'\x02' + bytes([len(r)]) + r
    s_der = b'\x02' + bytes([len(s)]) + s
    
    return b'\x30' + bytes([len(r_der + s_der)]) + r_der + s_der
    
def execute_script(script_sig_asm: str, script_pubkey_asm: str,message:str,
                   timestamp:int,
                   debug: bool = True,base:Optional[Base]=None) -> bool:
        """
        ASM形式のスクリプトを実行
        """
        if base is None:
            base=Base()

        stacks: List[str] = []
        alt_stack: List[str] = []  # 代替スタック
        scripts = (script_sig_asm + ' ' + script_pubkey_asm).split()
        
        i = 0
        while i < len(scripts):
            s = scripts[i]
            
            if debug:
                print(f"[{i}] {s} | Stack: {stacks}")
            
            # オペコードでない場合（データ）
            if not s.startswith('OP_'):
                i += 1
                continue
            
            s_hex = get_opcode_hex(s)
            
            try:
                # OP_PUSHBYTES_X (0x01-0x4b)
                if 0x01 <= s_hex <= 0x4b:
                    if i + 1 < len(scripts):
                        stacks.append(scripts[i + 1])
                        i += 2
                    else:
                        return False
                        
                # OP_PUSHDATA1 (0x4c)
                elif s_hex == 0x4c:
                    if i + 2 < len(scripts):
                        stacks.append(scripts[i + 2])
                        i += 3
                    else:
                        return False
                        
                # OP_PUSHDATA2/4
                elif s_hex in [0x4d, 0x4e]:
                    if i + 2 < len(scripts):
                        stacks.append(scripts[i + 2])
                        i += 3
                    else:
                        return False
                
                # OP_0 / OP_FALSE
                elif s_hex == 0x00:
                    stacks.append('')
                    i += 1
                    
                # OP_1NEGATE
                elif s_hex == 0x4f:
                    stacks.append(int_to_hex_signed(-1))
                    i += 1
                    
                # OP_1 から OP_16 (0x51-0x60)
                elif 0x51 <= s_hex <= 0x60:
                    value = s_hex - 0x50
                    stacks.append(int_to_hex_signed(value))
                    i += 1
                
                # === Stack Operations ===
                
                # OP_DUP (0x76)
                elif s_hex == 0x76:
                    if len(stacks) < 1:
                        return False
                    stacks.append(stacks[-1])
                    i += 1
                    
                # OP_DROP (0x75)
                elif s_hex == 0x75:
                    if len(stacks) < 1:
                        return False
                    stacks.pop()
                    i += 1
                    
                # OP_2DUP (0x6e)
                elif s_hex == 0x6e:
                    if len(stacks) < 2:
                        return False
                    stacks.append(stacks[-2])
                    stacks.append(stacks[-2])
                    i += 1
                    
                # OP_3DUP (0x6f)
                elif s_hex == 0x6f:
                    if len(stacks) < 3:
                        return False
                    stacks.extend([stacks[-3], stacks[-2], stacks[-1]])
                    i += 1
                    
                # OP_2DROP (0x6d)
                elif s_hex == 0x6d:
                    if len(stacks) < 2:
                        return False
                    stacks.pop()
                    stacks.pop()
                    i += 1
                    
                # OP_SWAP (0x7c)
                elif s_hex == 0x7c:
                    if len(stacks) < 2:
                        return False
                    stacks[-1], stacks[-2] = stacks[-2], stacks[-1]
                    i += 1
                    
                # OP_OVER (0x78)
                elif s_hex == 0x78:
                    if len(stacks) < 2:
                        return False
                    stacks.append(stacks[-2])
                    i += 1
                    
                # OP_ROT (0x7b)
                elif s_hex == 0x7b:
                    if len(stacks) < 3:
                        return False
                    stacks.append(stacks.pop(-3))
                    i += 1
                    
                # OP_TOALTSTACK (0x6b)
                elif s_hex == 0x6b:
                    if len(stacks) < 1:
                        return False
                    alt_stack.append(stacks.pop())
                    i += 1
                    
                # OP_FROMALTSTACK (0x6c)
                elif s_hex == 0x6c:
                    if len(alt_stack) < 1:
                        return False
                    stacks.append(alt_stack.pop())
                    i += 1
                
                # === Comparison ===
                
                # OP_EQUAL (0x87)
                elif s_hex == 0x87:
                    if len(stacks) < 2:
                        return False
                    a = stacks.pop()
                    b = stacks.pop()
                    stacks.append(int_to_hex_signed(1) if a == b else '')
                    i += 1
                    
                # OP_EQUALVERIFY (0x88)
                elif s_hex == 0x88:
                    if len(stacks) < 2:
                        return False
                    a = stacks.pop()
                    b = stacks.pop()
                    if a != b:
                        return False
                    i += 1
                
                # === Arithmetic (Baseクラスを活用) ===
                
                # OP_1ADD (0x8b)
                elif s_hex == 0x8b:
                    if len(stacks) < 1:
                        return False
                    value = hex_to_int_signed(stacks.pop())
                    stacks.append(int_to_hex_signed(value + 1))
                    i += 1
                    
                # OP_1SUB (0x8c)
                elif s_hex == 0x8c:
                    if len(stacks) < 1:
                        return False
                    value = hex_to_int_signed(stacks.pop())
                    stacks.append(int_to_hex_signed(value - 1))
                    i += 1
                    
                # OP_NEGATE (0x8f)
                elif s_hex == 0x8f:
                    if len(stacks) < 1:
                        return False
                    value = hex_to_int_signed(stacks.pop())
                    stacks.append(int_to_hex_signed(-value))
                    i += 1
                    
                # OP_ABS (0x90)
                elif s_hex == 0x90:
                    if len(stacks) < 1:
                        return False
                    value = hex_to_int_signed(stacks.pop())
                    stacks.append(int_to_hex_signed(abs(value)))
                    i += 1
                    
                # OP_NOT (0x91)
                elif s_hex == 0x91:
                    if len(stacks) < 1:
                        return False
                    value = hex_to_int_signed(stacks.pop())
                    stacks.append(int_to_hex_signed(1 if value == 0 else 0))
                    i += 1
                    
                # OP_0NOTEQUAL (0x92)
                elif s_hex == 0x92:
                    if len(stacks) < 1:
                        return False
                    value = hex_to_int_signed(stacks.pop())
                    stacks.append(int_to_hex_signed(1 if value != 0 else 0))
                    i += 1
                    
                # OP_ADD (0x93)
                elif s_hex == 0x93:
                    if len(stacks) < 2:
                        return False
                    b = hex_to_int_signed(stacks.pop())
                    a = hex_to_int_signed(stacks.pop())
                    stacks.append(int_to_hex_signed(a + b))
                    i += 1
                    
                # OP_SUB (0x94)
                elif s_hex == 0x94:
                    if len(stacks) < 2:
                        return False
                    b = hex_to_int_signed(stacks.pop())
                    a = hex_to_int_signed(stacks.pop())
                    stacks.append(int_to_hex_signed(a - b))
                    i += 1
                    
                # OP_BOOLAND (0x9a)
                elif s_hex == 0x9a:
                    if len(stacks) < 2:
                        return False
                    b = hex_to_int_signed(stacks.pop())
                    a = hex_to_int_signed(stacks.pop())
                    result = 1 if (a != 0 and b != 0) else 0
                    stacks.append(int_to_hex_signed(result))
                    i += 1
                    
                # OP_BOOLOR (0x9b)
                elif s_hex == 0x9b:
                    if len(stacks) < 2:
                        return False
                    b = hex_to_int_signed(stacks.pop())
                    a = hex_to_int_signed(stacks.pop())
                    result = 1 if (a != 0 or b != 0) else 0
                    stacks.append(int_to_hex_signed(result))
                    i += 1
                    
                # OP_NUMEQUAL (0x9c)
                elif s_hex == 0x9c:
                    if len(stacks) < 2:
                        return False
                    b = hex_to_int_signed(stacks.pop())
                    a = hex_to_int_signed(stacks.pop())
                    stacks.append(int_to_hex_signed(1 if a == b else 0))
                    i += 1
                    
                # OP_NUMEQUALVERIFY (0x9d)
                elif s_hex == 0x9d:
                    if len(stacks) < 2:
                        return False
                    b = hex_to_int_signed(stacks.pop())
                    a = hex_to_int_signed(stacks.pop())
                    if a != b:
                        return False
                    i += 1
                    
                # OP_LESSTHAN (0x9f)
                elif s_hex == 0x9f:
                    if len(stacks) < 2:
                        return False
                    b = hex_to_int_signed(stacks.pop())
                    a = hex_to_int_signed(stacks.pop())
                    stacks.append(int_to_hex_signed(1 if a < b else 0))
                    i += 1
                    
                # OP_GREATERTHAN (0xa0)
                elif s_hex == 0xa0:
                    if len(stacks) < 2:
                        return False
                    b = hex_to_int_signed(stacks.pop())
                    a = hex_to_int_signed(stacks.pop())
                    stacks.append(int_to_hex_signed(1 if a > b else 0))
                    i += 1
                    
                # OP_MIN (0xa3)
                elif s_hex == 0xa3:
                    if len(stacks) < 2:
                        return False
                    b = hex_to_int_signed(stacks.pop())
                    a = hex_to_int_signed(stacks.pop())
                    stacks.append(int_to_hex_signed(min(a, b)))
                    i += 1
                    
                # OP_MAX (0xa4)
                elif s_hex == 0xa4:
                    if len(stacks) < 2:
                        return False
                    b = hex_to_int_signed(stacks.pop())
                    a = hex_to_int_signed(stacks.pop())
                    stacks.append(int_to_hex_signed(max(a, b)))
                    i += 1
                
                # === Crypto ===
                
                # OP_RIPEMD160 (0xa6)
                elif s_hex == 0xa6:
                    if len(stacks) < 1:
                        return False
                    data = stacks.pop()
                    result = hashlib.new('ripemd160', bytes.fromhex(data)).digest()
                    stacks.append(result.hex())
                    i += 1
                    
                # OP_SHA1 (0xa7)
                elif s_hex == 0xa7:
                    if len(stacks) < 1:
                        return False
                    data = stacks.pop()
                    result = hashlib.sha1(bytes.fromhex(data)).digest()
                    stacks.append(result.hex())
                    i += 1
                    
                # OP_SHA256 (0xa8)
                elif s_hex == 0xa8:
                    if len(stacks) < 1:
                        return False
                    data = stacks.pop()
                    result = hashlib.sha256(bytes.fromhex(data)).digest()
                    stacks.append(result.hex())
                    i += 1
                    
                # OP_HASH160 (0xa9)
                elif s_hex == 0xa9:
                    if len(stacks) < 1:
                        return False
                    data = stacks.pop()
                    sha256_hash = hashlib.sha256(bytes.fromhex(data)).digest()
                    ripemd160_hash = hashlib.new('ripemd160', sha256_hash).digest()
                    stacks.append(ripemd160_hash.hex())
                    i += 1
                    
                # OP_HASH256 (0xaa) 
                elif s_hex == 0xaa:
                    if len(stacks) < 1:
                        return False
                    data = stacks.pop()
                    # is_little=Falseでビッグエンディアンのまま取得
                    result = base.hash256_hex(data, is_little=False)
                    stacks.append(result)
                    i += 1
                
                # === Other ===
                
                # OP_VERIFY (0x69)
                elif s_hex == 0x69:
                    if len(stacks) < 1:
                        return False
                    value = stacks.pop()
                    if not cast_to_bool(value):
                        return False
                    i += 1
                
                # OP_CHECKSIG (0xac)
                elif s_hex == 0xac:
                    if len(stacks) < 2:
                        return False
                    
                    pubkey_hex = stacks.pop()
                    signature_hex = stacks.pop()
                    
                    # 空チェック
                    if not signature_hex or not pubkey_hex:
                        stacks.append('')
                        i += 1
                        continue
                    
                    # 署名検証
                    result=verify_signature(pubkey_hex,signature_hex,message,timestamp)

                        
                    if debug:
                        print(f"署名検証: {'成功' if result else '失敗'}")

                    stacks.append(int_to_hex_signed(1) if result else '')
                    i += 1
                    
                # OP_CHECKSIGVERIFY (0xad)
                elif s_hex == 0xad:
                    if len(stacks) < 2:
                        return False
                    pubkey = stacks.pop()
                    signature = stacks.pop()
                    result = len(signature) > 0 and len(pubkey) > 0
                    if not result:
                        return False
                    i += 1
                    
                # OP_NOP, OP_NOP1-10 (0x61, 0xb0-0xb9)
                elif s_hex == 0x61 or (0xb0 <= s_hex <= 0xb9):
                    i += 1
                    
                # OP_RETURN (0x6a)
                elif s_hex == 0x6a:
                    return False
                    
                else:
                    if debug:
                        print(f"未対応のオペコード: {s} ({hex(s_hex)})")
                    i += 1
                    
            except Exception as e:
                if debug:
                    print(f"エラー: {e}")
                return False
        
        # スタックに1つだけ要素が残り、それが非ゼロであれば有効
        if len(stacks) != 1:
            if debug:
                print(f"スタック検証失敗: {len(stacks)}個の要素が残っています")
            return False
        
        result = cast_to_bool(stacks[0])
        if debug:
            print(f"最終スタック: {stacks}")
            print(f"結果: {result}")
        return result


# 共通のバリデータ関数
def validate_hex_string(v: Optional[str]) -> Optional[str]:
    if v is None:
        return v
    
    hex_str = v.removeprefix('0x').removeprefix('0X')
    try:
        int(hex_str, 16)
    except ValueError:
        raise ValueError(f'{v} は有効な16進数ではありません')
    return v


def validate_script(obj, asm_field: str, hex_field: str):
    """ASMとHEXのペアをバリデーションして相互変換"""
    asm_value = getattr(obj, asm_field)
    hex_value = getattr(obj, hex_field)
    
    if (asm_value is None) == (hex_value is None):
        raise ValueError(f'{asm_field}または{hex_field}のどちらかを指定してください')
    
    if asm_value:
        setattr(obj, hex_field, script_to_hex(asm_value))
    
    if hex_value:
        setattr(obj, asm_field, hex_to_script(hex_value))
    
    return obj

def validate_readonly(v: Optional[str]) -> Optional[str]:
    if v is not None:
            raise ValueError('読み取り専用フィールドです')
    return v

def validate_script_type(self):
    """スクリプト公開鍵のタイプを判定するバリデーター"""
    script = bytes.fromhex(self.script_pubkey_hex)
    length = len(script)
    
    # P2PKH: OP_DUP OP_HASH160 <20 bytes> OP_EQUALVERIFY OP_CHECKSIG
    if (length == 25 and 
        script[0] == 0x76 and  # OP_DUP
        script[1] == 0xa9 and  # OP_HASH160
        script[2] == 0x14 and  # Push 20 bytes
        script[23] == 0x88 and  # OP_EQUALVERIFY
        script[24] == 0xac):    # OP_CHECKSIG
        self.script_type = "P2PKH"
    
    # P2PK: <33 or 65 bytes pubkey> OP_CHECKSIG
    elif ((length == 35 and script[0] == 0x21 and script[34] == 0xac) or
          (length == 67 and script[0] == 0x41 and script[66] == 0xac)):
        self.script_type = "P2PK"
    
    # P2SH: OP_HASH160 <20 bytes> OP_EQUAL
    elif (length == 23 and
          script[0] == 0xa9 and  # OP_HASH160
          script[1] == 0x14 and  # Push 20 bytes
          script[22] == 0x87):    # OP_EQUAL
        self.script_type = "P2SH"
    
    # P2WPKH: OP_0 <20 bytes>
    elif (length == 22 and
          script[0] == 0x00 and  # OP_0
          script[1] == 0x14):     # Push 20 bytes
        self.script_type = "P2WPKH"
    
    # P2WSH: OP_0 <32 bytes>
    elif (length == 34 and
          script[0] == 0x00 and  # OP_0
          script[1] == 0x20):     # Push 32 bytes
        self.script_type = "P2WSH"
    
    # P2TR: OP_1 <32 bytes>
    elif (length == 34 and
          script[0] == 0x51 and  # OP_1
          script[1] == 0x20):     # Push 32 bytes
        self.script_type = "P2TR"
    
    # OP_RETURN: OP_RETURN <data>
    elif length >= 1 and script[0] == 0x6a:  # OP_RETURN
        self.script_type = "OP_RETURN"
    
    # P2MS (Multisig): OP_M <pubkey1> <pubkey2> ... OP_N OP_CHECKMULTISIG
    elif (length >= 37 and
          script[-1] == 0xae and  # OP_CHECKMULTISIG
          0x51 <= script[0] <= 0x60 and  # OP_1 to OP_16 (M)
          0x51 <= script[-2] <= 0x60):    # OP_1 to OP_16 (N)
        self.script_type = "P2MS"
    
    else:
        self.script_type = "CUSTOM"
    
    return self
