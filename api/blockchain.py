from fastapi import APIRouter,Body,BackgroundTasks,Query
from fastapi import HTTPException
from models.blockchain import BitcoinTransaction,BitcoinBlock,TransactionRequest,BlockRequest,BitcoinWallet,BitcoinAddress
from azure.communication.email import EmailClient
from managers.email_manager import EmailManager
from api.email import notify_contact_message
import uuid
from typing import List, Optional,Dict


router = APIRouter()

@router.post("/chain/generate_block", tags=["blcokchain"])
async def generate_block(
    block: BlockRequest = Body(
        ...,
        examples=[
            #2009 年に Hal Finney に行われた初のビットコイン取引
            {
                "version": 1,
                "previous_block_hash": "000000002a22cfee1f2c846adbd12b3e183d4f97683f85dad08a79780a84bd55",
                "time": 1231731025,
                "bits": "1d00ffff",
                "nonce": 1889418792,
                "txids":[
                    "b1fea52486ce0c62bb442b530a3f0132b826c74e473d1f2c220bfa78111c5082",
                    "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16"
                ]
            },
            # #0 block
            {
                "version": 1,
                "previous_block_hash": "0000000000000000000000000000000000000000000000000000000000000000",
                "time": 1231006505,
                "bits": "1d00ffff",
                "nonce": 2083236893,
                "txids":[
                    "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b",
                ]
            },
            
            
        ],
    )
):
    return BitcoinBlock.generate_block(block)


@router.post("/chain/generate_transaction", tags=["blcokchain"])
async def generate_transaction(
    transaction: TransactionRequest = Body(
        ...,
        examples=[
            # Basic Segwit Transaction
            {
                "version": 1,
                "locktime": 0,
                "vin": [
                    {
                        "txid": "719d8331113ba717255873adf6b4c5843085701411aa7ddbeb11b93f717112f1",
                        "vout": 0,
                        "script_sig": {
                            "hex": "473044022001187384d8b30020a0ad6976805f0676da8e5fd219ffec084f7c22d2acd4838f0220074e3195a6e624b7ac5cb8e072d77f3b6363968040fc99f268affd4c08e11ac7012103510f10304c99bd53af8b3e47b3e282a75a50dad6f459c4c985898fd800a9e9a8",
                        },
                        "sequence": 4294967295,
                    },
                    {
                        "txid": "719d8331113ba717255873adf6b4c5843085701411aa7ddbeb11b93f717112f1",
                        "vout": 1,
                        "script_sig": {
                            "hex": "",
                        },
                        "txinwitness":[
                            "3044022035345342616cb5d6eefbbffc1de179ee514587dd15efe5ca892602f50336e30502207864061776e39992f317aee92dcc9595cc754b8f13957441d5ccd9ebd1b5cc0c01",
                            "022ed6c7d33a59cc16d37ad9ba54230696bd5424b8931c2a68ce76b0dbbc222f65"
                        ],
                        "sequence": 4294967295,
                    }
                ],
                "outputs": [
                    {
                        "value": 10000,
                        "script_pubkey": {
                            "hex": "0014858e1f88ff6f383f45a75088e15a095f20fc663f",
                        },
                    },
                    {
                        "value": 6700,
                        "script_pubkey": {
                            "hex": "76a9142241a6c3d4cc3367efaa88b58d24748caef79a7288ac",
                        },
                    },
                ],
            },
            # Basic Segwit Transaction 
            {
                "version": 1,
                "locktime": 0,
                "vin": [
                    {
                        "txid": "1163ca119acb40dbf943f4faa3328ce1ac71b24f5535e7f25a11a0c1815f733c",
                        "vout": 0,
                        "script_sig": {
                            "hex": "",
                        },
                        "txinwitness":[
                            "30440220424772d4ad659960d4f1b541fd853f7da62e8cf505c2f16585dc7c8cf643fe9a02207fbc63b9cf317fc41402b2e7f6fdc1b01f1b43c5456cf9b547fe9645a16dcb1501",
                            "032533cb19cf37842556dd2168b1c7b6f3a70cff25a6ff4d4b76f2889d2c88a3f2"
                        ],
                        "sequence": 4294967295,
                    }
                ],
                "outputs": [
                    {
                        "value": 201649,
                        "script_pubkey": {
                            "hex": "0014689a681c462536ad7d735b497511e527e9f59245",
                        },
                    },
                    {
                        "value": 4815,
                        "script_pubkey": {
                            "hex": "00148859f1e9ef3ba438e2ec317f8524ed41f8f06c6a",
                        },
                    },
                ],
            },
            # #0 block transaction
            {
                "version": 1,
                "locktime": 0,
                "vin": [
                    {
                        "txid": "0000000000000000000000000000000000000000000000000000000000000000",
                        "vout": 4294967295,
                        "script_sig": {
                            "hex": "04ffff001d0104455468652054696d65732030332f4a616e2f32303039204368616e63656c6c6f72206f6e206272696e6b206f66207365636f6e64206261696c6f757420666f722062616e6b73",
                        },
                        "sequence": 4294967295,
                    }
                ],
                "outputs": [
                    {
                        "value": 5000000000,
                        "script_pubkey": {
                            "hex": "4104678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5fac",
                        },
                    }
                ],
            },
            
            
        ],
    ),
):
    return BitcoinTransaction.generate_transaction(transaction)

# @router.post("/chain/generate_keypair", tags=["blcokchain"])
# async def generate_keypair(
#     wallet:BitcoinWallet=Body(...)
# ):
#     return wallet

@router.post("/chain/generate_keypair", tags=["blcokchain"])
async def generate_keypair(
):
    ba=BitcoinAddress.generate_address()
    return ba

