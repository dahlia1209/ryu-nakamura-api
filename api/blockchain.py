from fastapi import APIRouter,Body,BackgroundTasks,Query,Path
from fastapi import HTTPException
from models.blockchain import TransactionRequest
from api.email import notify_contact_message
import uuid
from typing import List, Optional,Dict,Tuple
from repository import blockchain as blockchain_repo
from azure.core.exceptions import ResourceNotFoundError
from bitcoinutils.script import Script
import json
import traceback
from bitcoinutils.setup import setup
from models.query import QueryFilter
import struct
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
from cryptography.exceptions import InvalidSignature


router = APIRouter()

@router.post("/chain/transaction/verify_signature", tags=["blockchain"])
async def verify_signature(
    tran_req:Optional[TransactionRequest]=Body(None,examples=[
        #1d5308ff12cb6fdb670c3af673a6a1317e21fa14fc863d5827f9d704cd5e14dc
        {
                "version": 1,
                "locktime": 0,
                "vin": [
                    {
                        "txid": "4ba5cfbbeb418055e412682dddb01ccec683a80dd9e12792a273f3b20d4a99b7",
                        "vout": 0,
                        "script_sig": {
                            "hex": "473044022008f4f37e2d8f74e18c1b8fde2374d5f28402fb8ab7fd1cc5b786aa40851a70cb02201f40afd1627798ee8529095ca4b205498032315240ac322c9d8ff0f205a93a580121024aeaf55040fa16de37303d13ca1dde85f4ca9baa36e2963a27a1c0c1165fe2b1",
                            "utxo_scriptpubkey_hex":"76a9144299ff317fcd12ef19047df66d72454691797bfc88ac"
                        },
                        "sequence": 4294967295,
                    }
                ],
                "outputs": [
                    {
                        "value": 15000,
                        "script_pubkey": {
                            "hex": "76a914b3e2819b6262e0b1f19fc7229d75677f347c91ac88ac",
                        },
                    },
                    
                ],
            },
        ])
):
    try:
        message_hash,raw=tran_req.get_hash_message()
        verified_sig=[]
        for v in  tran_req.vin:
            parse_script = Script.from_raw(v.script_sig.hex).get_script()
            if len(parse_script) != 2:
                raise HTTPException(status_code=400, detail=f"不正なパラメータです")
            
            signature = parse_script[0][:-2]  # 最後の2文字（SIGHASH_ALL）を除去
            pubkey = parse_script[1]
            
            pubkey_object = ec.EllipticCurvePublicKey.from_encoded_point(
                ec.SECP256K1(), 
                bytes.fromhex(pubkey)
            )
            
            result = pubkey_object.verify(
                bytes.fromhex(signature),
                bytes.fromhex(message_hash),
                ec.ECDSA(Prehashed(hashes.SHA256()))
            )
            verified_sig.append(v.script_sig.hex)
            
        return verified_sig
        
    except HTTPException as e:
        raise
    except InvalidSignature as e:
        raise HTTPException(status_code=400, detail=f"署名が正しく検証できませんでした。")
    except Exception as e:
        tb_str = traceback.format_exc()
        raise HTTPException(status_code=500, detail=f"エラーがスローされました：{tb_str}")
