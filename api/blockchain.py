from fastapi import APIRouter, Body, BackgroundTasks, Query, Path,Depends
from fastapi import HTTPException
from models.blockchain import Block, Transaction, TransactionVin, TransactionOutput
from repository import blockchain as blockchain_repo
from cryptography.hazmat.primitives.asymmetric.utils import Prehashed
from managers.auth_manager import (
    JWTPayload,
    requires_scope,
)

router = APIRouter()


@router.post("/blockchain/block", tags=["blockchain"])
async def generate_block(
    block: Block = Body(
        ...,
        examples=[
            # 0 genesys block
            {
                "hash": "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
                "version": 1,
                "previous_hash": "0000000000000000000000000000000000000000000000000000000000000000",
                "merkle_root": "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b",
                "timestamp": 1231006505,
                "bits": "1d00ffff",
                "nonce": 2083236893,
                "transactions": [
                    {
                        "txid": "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b",
                        "version": 1,
                        "locktime": 0,
                        "vin": [
                            {
                                "utxo_txid": "0000000000000000000000000000000000000000000000000000000000000000",
                                "utxo_vout": 4294967295,
                                "sequence": 0xFFFFFFFF,
                                "script_sig_hex": "04ffff001d0104455468652054696d65732030332f4a616e2f32303039204368616e63656c6c6f72206f6e206272696e6b206f66207365636f6e64206261696c6f757420666f722062616e6b73",
                            },
                        ],
                        "outputs": [
                            {
                                "value": 5000000000,
                                "script_pubkey_hex": "4104678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5fac",
                            }
                        ],
                    },
                ],
            },
            # 170 block
            {
                "hash": "00000000d1145790a8694403d4063f323d499e655c83426834d4ce2f8dd4a2ee",
                "version": 1,
                "previous_hash": "000000002a22cfee1f2c846adbd12b3e183d4f97683f85dad08a79780a84bd55",
                "merkle_root": "7dac2c5666815c17a3b36427de37bb9d2e2c5ccec3f8633eb91a4205cb4c10ff",
                "timestamp": 1231731025,
                "bits": "1d00ffff",
                "nonce": 1889418792,
                "transactions": [
                    {
                        "txid": "b1fea52486ce0c62bb442b530a3f0132b826c74e473d1f2c220bfa78111c5082",
                        "version": 1,
                        "locktime": 0,
                        "vin": [
                            {
                                "utxo_txid": "0000000000000000000000000000000000000000000000000000000000000000",
                                "utxo_vout": 4294967295,
                                "sequence": 0xFFFFFFFF,
                                "script_sig_hex": "04ffff001d0102",
                            },
                        ],
                        "outputs": [
                            {
                                "value": 5000000000,
                                "script_pubkey_hex": "4104d46c4968bde02899d2aa0963367c7a6ce34eec332b32e42e5f3407e052d64ac625da6f0718e7b302140434bd725706957c092db53805b821a85b23a7ac61725bac",
                            }
                        ],
                    },
                    {
                        "txid": "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16",
                        "version": 1,
                        "locktime": 0,
                        "vin": [
                            {
                                "utxo_txid": "0437cd7f8525ceed2324359c2d0ba26006d92d856a9c20fa0241106ee5a597c9",
                                "utxo_vout": 0,
                                "sequence": 0xFFFFFFFF,
                                "script_sig_hex": "47304402204e45e16932b8af514961a1d3a1a25fdf3f4f7732e9d624c6c61548ab5fb8cd410220181522ec8eca07de4860a4acdd12909d831cc56cbbac4622082221a8768d1d0901",
                            },
                        ],
                        "outputs": [
                            {
                                "value": 1000000000,
                                "script_pubkey_hex": "4104ae1a62fe09c5f51b13905f07f06b99a2f7159b2225f374cd378d71302fa28414e7aab37397f554a7df5f142c21c1b7303b8a0626f1baded5c72a704f7e6cd84cac",
                            },
                            {
                                "value": 4000000000,
                                "script_pubkey_hex": "410411db93e1dcdb8a016b49840f8c53bc1eb68a382e97b1482ecad7b148a6909a5cb2e0eaddfb84ccf9744464f82e160bfa9b8b64f9d4c03f999b8643f656b412a3ac",
                            },
                        ],
                    },
                ],
            },
        ],
    ),
):
    try:
        blockchain_repo.create_block(block)

        return block
    except ValueError as e:
        raise HTTPException(status_code=400,detail=f"{e}")
    except Exception:
        raise
    finally:
        pass

@router.get("/blockchain/block/current", tags=["blockchain"])
async def get_block_current():
    try:
        current_block=blockchain_repo.get_block("CURRENT","0"*64)

        return current_block
    except:
        raise
    finally:
        pass

@router.delete("/blockchain/block/current", tags=["blockchain"])
async def get_block_current(
    token_data: JWTPayload = Depends(requires_scope("blockchain.delete")),
):
    try:
        blockchain_repo.delete_block("CURRENT","0"*64)

        return True
    except ValueError as e:
        raise HTTPException(status_code=400,detail=str(e))
    except Exception:
        raise
    finally:
        pass


@router.post("/blockchain/transaction", tags=["blockchain"])
async def post_transaction(
    transaction: Transaction = Body(
        ...,
        examples=[
            # 0 block coinbase transaction
            {
                "txid": "4a5e1e4baab89f3a32518a88c31bc87f618f76673e2cc77ab2127b7afdeda33b",
                "version": 1,
                "locktime": 0,
                "vin": [
                    {
                        "utxo_txid": "0000000000000000000000000000000000000000000000000000000000000000",
                        "utxo_vout": 4294967295,
                        "sequence": 0xFFFFFFFF,
                        "script_sig_asm": "OP_PUSHBYTES_4 ffff001d OP_PUSHBYTES_1 04 OP_PUSHBYTES_69 5468652054696d65732030332f4a616e2f32303039204368616e63656c6c6f72206f6e206272696e6b206f66207365636f6e64206261696c6f757420666f722062616e6b73",
                    },
                ],
                "outputs": [
                    {
                        "value": 5000000000,
                        "script_pubkey_asm": "OP_PUSHBYTES_65 04678afdb0fe5548271967f1a67130b7105cd6a828e03909a67962e0ea1f61deb649f6bc3f4cef38c4f35504e51ec112de5c384df7ba0b8d578a4c702b6bf11d5f OP_CHECKSIG",
                    }
                ],
            }
        ],
    )
):
    return transaction


@router.post("/blockchain/transaction/input", tags=["blockchain"])
async def post_transaction_input(
    txin: TransactionVin = Body(
        ...,
        examples=[
            # 227,836 Block Coinbase Transaction
            {
                "utxo_txid": "0" * 64,
                "utxo_vout": 4294967295,
                "sequence": 0x00000000,
                "script_sig_hex": "47304402204e45e16932b8af514961a1d3a1a25fdf3f4f7732e9d624c6c61548ab5fb8cd410220181522ec8eca07de4860a4acdd12909d831cc56cbbac4622082221a8768d1d0901",
            },
            # 170 Block 1 Transaction (halfin)
            {
                "utxo_txid": "f4184fc596403b9d638783cf57adfe4c75c605f6356fbc91338530e9831e9e16",
                "utxo_vout": 0,
                "sequence": 0xFFFFFFFF,
                "script_sig_asm": "OP_PUSHBYTES_71 304402204e45e16932b8af514961a1d3a1a25fdf3f4f7732e9d624c6c61548ab5fb8cd410220181522ec8eca07de4860a4acdd12909d831cc56cbbac4622082221a8768d1d0901",
            },
        ],
    )
):
    return txin


@router.post("/blockchain/transaction/output", tags=["blockchain"])
async def post_transaction_output(
    txout: TransactionOutput = Body(
        ...,
        examples=[
            {
                "value": 4000000000,
                "script_pubkey_asm": "OP_PUSHBYTES_65 0411db93e1dcdb8a016b49840f8c53bc1eb68a382e97b1482ecad7b148a6909a5cb2e0eaddfb84ccf9744464f82e160bfa9b8b64f9d4c03f999b8643f656b412a3 OP_CHECKSIG",
            }
        ],
    )
):
    return txout
