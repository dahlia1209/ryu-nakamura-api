from fastapi import APIRouter,Body,BackgroundTasks,Query,Path
from fastapi import HTTPException
from models.blockchain import Transaction,Block,TransactionRequest,BlockRequest,Address,TransactionOutput,TransactionInput,TransactionScriptSignature,TransactionScriptPubkey
from api.email import notify_contact_message
import uuid
from typing import List, Optional,Dict,Tuple
from repository import blockchain as blockchain_repo
from azure.core.exceptions import ResourceNotFoundError
from bitcoinutils.script import Script
from bitcoinutils.transactions import Transaction as UtilTransaction, TxInput, TxOutput
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
from azure.data.tables import TableTransactionError
from datetime import datetime

router = APIRouter()

@router.post("/blockchain/address", tags=["blockchain"])
async def create_address(
    address:Address=Body(
        default_factory=lambda:Address(),
        examples=[{
        "id": uuid.uuid4()
    }]),
    start_with:List[str]=Body([],)
):
    for i in  range(10000):
        
        ba=Address.generate_address(address.id,address.private_key)
        blockchain_repo.create_address(ba)
        if not start_with:
            return ba
        for s in start_with:
            if ba.public_key.startswith(s):
                print(f"試行回数:{i+1}")
                return ba
        continue
    
    raise HTTPException(
        status_code=400,
        detail=f"'{start_with}' から始まる公開鍵を生成できませんでした"
    )

@router.post("/blockchain/mining", tags=["blockchain"])
async def generate_block(
    bits:str=Body("1d00ffff"),
    txids:List[str]=Body([]),
    to_scriptpubkey:str=Body(...,examples=["76a9147fc9ea0badb18a27533949c1c60e629fe0d6250988ac"]),
    locktime:int=Body(0),
    time: Optional[int] = Body(None,example=[])
):
    try:
        if not time:
            time = int(datetime.now().timestamp())
        if int(bits,16) < int("1e000000",16):
            raise HTTPException(status_code=400,detail=f"bits:{bits} は1e000000より上の値を指定してください")
        #DBから取得
        latest_block=blockchain_repo.get_block()
        block_height=latest_block.height+1 if latest_block else  0 
        previous_block_hash=latest_block.hash if latest_block  else  "0"*64 
        print("previous_block_hash",previous_block_hash)
        
        coinbase_scriptpubkey=TransactionScriptPubkey.coinbase(block_height=block_height)
        coinbase_tran=Transaction.generate_coinbase(coinbase_scriptpubkey.hex,to_scriptpubkey,1,locktime)
        
        txids.insert(0,coinbase_tran.txid)
        block_req=BlockRequest(version=1,previous_block_hash=previous_block_hash,bits=bits,nonce=0,txids=txids,time=time)
        for i in range(1000000000):
            block_req.nonce=i
            block= Block.generate_block(block_req)
            block.height=block_height
            if block.is_valid_hash():
                coinbase_tran.blockhash=block.hash
                blockchain_repo.create_block(block)
                blockchain_repo.create_transaction(coinbase_tran)
                blockchain_repo.batch_transaction_vin(coinbase_tran.vin)
                blockchain_repo.batch_transaction_output(coinbase_tran.outputs)
                return block
            continue
            
        raise HTTPException(
            status_code=400,
            detail=f"bits {bits}を満たすハッシュ値を生成できませんでした。"
        )
        
    except HTTPException as e:
        raise
    
    except Exception as e:
        tb_str = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail=f"エラーがスローされました:{e}.\nトレース情報:{tb_str}"
        )

@router.post("/blockchain/transaction/verify_signature", tags=["blockchain"])
async def verify_signature(
    tran_req: Optional[TransactionRequest] = Body(
        None,
        examples=[
            # 4e8bfd86468e5b9fda9b8529f7b16af83df9657e0c7864c8113b9dd581066886
            {
                "version": 1,
                "locktime": 0,
                "vin": [
                    {
                        "txid": "abc9a90f8f9a6040a812b9a5c822e007b9a6e4e1384978182a311e6cfcd3c0a2",
                        "vout": 0,
                        "script_sig": {
                            "hex": "4930460221008cc4db53ecd7163df0103d2065963dc538a261f6d81c6b2f9c8e793a7c8932330221008dafd760d7dc8db84ee05b077a5aabc1dfd5ddcc32ad88ff083c47842a8ade46014104c1a686fb757d72fb2e4a2b5284742efcae6c27dc03c0a149bcf4b6236504649b33e320ad890b0abf0c866d78f61c089eb7917a580308d50b0bbc312d2e9b2843",
                            "utxo_scriptpubkey_hex": "76a914c64ece4b21a927f9920c52906854fc838b521f3c88ac",
                        },
                        "sequence": 4294967295,
                    },
                    {
                        "txid": "251490baffd0d3d5175b77bf334ba866c4fd416fcc686a1001e188fba83b4ccb",
                        "vout": 0,
                        "script_sig": {
                            "hex": "48304502203e64f60a03537efa83b33abc922837925cf5d6922599ae8e8205aee5c70877cf0221008feebb20702724a716afe48d65d1990fb004404f3b528785c189a30ae81832a0014104242113ea5e212fba90be4ec3fd3c572844ed43f42eaa8e394ccce4a865c6d60296517f2667095178e409463f211d9aacdfd404585d4f3048405eb08c626d029b",
                            "utxo_scriptpubkey_hex": "76a9146f34d3811aded1df870359f311c2a11a015e945388ac",
                        },
                        "sequence": 4294967295,
                    },
                ],
                "outputs": [
                    {
                        "value": 16000000,
                        "script_pubkey": {
                            "hex": "76a914fed389f0e3b7b5b10036a278521bbc13224ce18e88ac"
                        },
                    },
                    {
                        "value": 5000000000,
                        "script_pubkey": {
                            "hex": "76a91487bb67c38d076bd88dc87bd75037ddfbb83a136988ac"
                        },
                    },
                ],
            },
            # 1d5308ff12cb6fdb670c3af673a6a1317e21fa14fc863d5827f9d704cd5e14dc
            {
                "version": 1,
                "locktime": 0,
                "vin": [
                    {
                        "txid": "4ba5cfbbeb418055e412682dddb01ccec683a80dd9e12792a273f3b20d4a99b7",
                        "vout": 0,
                        "script_sig": {
                            "hex": "473044022008f4f37e2d8f74e18c1b8fde2374d5f28402fb8ab7fd1cc5b786aa40851a70cb02201f40afd1627798ee8529095ca4b205498032315240ac322c9d8ff0f205a93a580121024aeaf55040fa16de37303d13ca1dde85f4ca9baa36e2963a27a1c0c1165fe2b1",
                            "utxo_scriptpubkey_hex": "76a9144299ff317fcd12ef19047df66d72454691797bfc88ac",
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
            
        ],
    )
):
    try:

        verified_sig=[]
        for (i,v) in  enumerate(tran_req.vin):
            parse_script = Script.from_raw(v.script_sig.hex).get_script()
            if len(parse_script) != 2:
                raise HTTPException(status_code=400, detail=f"不正なパラメータです")

            signature = parse_script[0][:-2]  # 最後の2文字（SIGHASH_ALL）を除去
            pubkey = parse_script[1]

            pubkey_object = ec.EllipticCurvePublicKey.from_encoded_point(
                ec.SECP256K1(), 
                bytes.fromhex(pubkey)
            )

            message_hash,raw=tran_req.get_hash_message(i)
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
