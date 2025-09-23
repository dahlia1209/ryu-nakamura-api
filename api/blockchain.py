from fastapi import APIRouter,Body,BackgroundTasks,Query,Path
from fastapi import HTTPException
from models.blockchain import BitcoinTransaction,BitcoinBlock,TransactionRequest,BlockRequest,BitcoinWallet,BitcoinAddress,BitcoinTransactionOutput,BitcoinTransactionInput,BitcoinTransactionScriptSignature
from api.email import notify_contact_message
import uuid
from typing import List, Optional,Dict,Tuple
from repository import blockchain as blockchain_repo
from azure.core.exceptions import ResourceNotFoundError
from bitcoinutils.script import Script
from bitcoinutils.transactions import Transaction, TxInput, TxOutput
from bitcoinutils.keys import PrivateKey, PublicKey, P2wpkhAddress, P2wshAddress, P2shAddress,b58encode,b58decode,sigencode_der
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

@router.post("/chain/generate_block", tags=["blockchain"])
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


@router.post("/chain/generate_transaction", tags=["blockchain"])
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


@router.post("/chain/generate_keypair", tags=["blockchain"])
async def generate_keypair(
):
    ba=BitcoinAddress.generate_address()
    return ba

@router.post("/chain/address", tags=["blockchain"])
async def create_address(
    address:BitcoinAddress=Body(
        default_factory=lambda:BitcoinAddress(),
        examples=[{
        "id": uuid.uuid4()
    }])
):
    ba=BitcoinAddress.generate_address(address.id,address.private_key)
    blockchain_repo.create_address(ba)
    return ba

@router.get("/chain/address/{address_id}", tags=["blockchain"],response_model=BitcoinAddress)
async def get_address(
    address_id: uuid.UUID=Path(..., description="ADDRESS ID to get")
):
    try:
        ba=blockchain_repo.get_address(str(address_id))
        if ba is None:
            raise HTTPException(
                status_code=404,
                detail=f"指定されたID {address_id} のデータが見つかりません"
            )
            
        return ba

    except HTTPException:
        raise
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"不正なパラメータ形式です: {e}"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="内部サーバーエラーが発生しました"
        )

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
        
@router.post("/chain/transaction", tags=["blockchain"])
async def create_transaction(
    tran_req:TransactionRequest=Body(...,examples=[
        #first sent
        {
                "version": 1,
                "locktime": 0,
                "vin": [
                    {
                        "txid": "c074b77b29c640bcd5af354302ed02063a5c410d79a6a5c6add5f86864b6c289",
                        "vout": 0,
                        "script_sig": {
                            "hex": "00",
                        },
                        "sequence": 4294967295,
                    }
                ],
                "outputs": [
                    {
                        "value": 1000000000,
                        "script_pubkey": {
                            "hex": "76a9145e294708a0fae7c70d7dafa5920083dbaf0ee66488ac",
                        },
                    },
                    {
                        "value": 4000000000,
                        "script_pubkey": {
                            "hex": "76a9145e294708a0fae7c70d7dafa5920083dbaf0ee66488ac",
                        },
                    },
                ],
            },
        #coinbase
        {
                "version": 1,
                "locktime": 0,
                "vin": [
                    {
                        "txid": "0000000000000000000000000000000000000000000000000000000000000000",
                        "vout": 4294967295,
                        "script_sig": {
                            "hex": "030000001976a914d60175b6845c4e6076f7b7a2353f280ef838a79f88ac",
                        },
                        "sequence": 4294967295,
                    }
                ],
                "outputs": [
                    {
                        "value": 5000000000,
                        "script_pubkey": {
                            "hex": "76a914d60175b6845c4e6076f7b7a2353f280ef838a79f88ac", #
                        },
                    }
                ],
            },
        
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
        ]),
    address_ids_for_signature:List[str]=Body(...,examples=[["086f17d0-7caa-43e4-9de2-ce7c2269a956","bdeb0274-151f-46aa-a552-f48b81f5886c"]]),
    # is_coinbase:bool=Body(False)
):
    try:
        tr=tran_req.model_copy()
        #アドレス取得
        addresses=[blockchain_repo.get_address(str(address_id)) for address_id in address_ids_for_signature]
        
        #トランザクション作成
        txins:List[BitcoinTransactionInput]=[]
        txouts:List[BitcoinTransactionOutput]=[]
        addrs:List[BitcoinAddress]=[]
        for v in tr.vin:
            if v.is_coinbase():
                height=format(0, '06X') #ブロック高0
                previous_scriptpubkey=f"03+{height}+1976a914d60175b6845c4e6076f7b7a2353f280ef838a79f88ac" #Mined by Ryu nakamuraのスクリプト
                txin=BitcoinTransactionInput(script_sig=BitcoinTransactionScriptSignature(hex=previous_scriptpubkey),**v.model_dump(exclude={"script_sig"}))
                txins.append(txin)
                addrs.append(addresses[0])
                break
            else:
                #UTXOが存在し、かつ、未使用か検証
                utxo=blockchain_repo.get_transaction(v.txid)
                if utxo is None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"UTXOが存在しません。trid:{v.txid}",
                    )
                qf = QueryFilter()
                qp=utxo.reverse_bytes(utxo.txid)+v.vout_to_hex()
                qf.add_filter(f"RowKey ge @RowKey", {"RowKey": qp})
                spent_utxo=blockchain_repo.list_transaction_vin(qf)
                if spent_utxo:
                    raise HTTPException(
                        status_code=400,
                        detail=f"UTXOはすでに使用されています。UTXOのtxid:{spent_utxo[0].txid}",
                    )
                    
                #UTXOのスクリプト公開鍵のアドレスが指定されているか確認
                previous_scriptpubkey=utxo.outputs[v.vout].script_pubkey.hex
                pkh=utxo.outputs[v.vout].get_pkh()
                if pkh is None:
                    raise HTTPException(
                        status_code=400,
                        detail=f"UTXOのスクリプト公開鍵にPKHが含まれていません。script_pubkey:{previous_scriptpubkey})",
                    )
                    
                tar_address=[a for a in addresses if a is not None and a.to_hash160()==pkh]
                if not tar_address:
                    raise HTTPException(
                        status_code=400,
                        detail=f"公開鍵ハッシュ {pkh} を含むアドレスが存在しません",
                    )
                
                txin=BitcoinTransactionInput(script_sig=BitcoinTransactionScriptSignature(hex=v.script_sig.hex,utxo_scriptpubkey_hex=previous_scriptpubkey),**v.model_dump(exclude={"script_sig"}))
                txins.append(txin)
                addrs.append(tar_address[0])
        for i,o in enumerate(tr.outputs):
            #todoスクリプト公開鍵の検証
            
            o.n=i
            txouts.append(o)
        
        #署名処理
        #1. Remove existing ScriptSigs  (done)
        #2. Put the ScriptPubKey as a placeholder in the ScriptSig (done)
        #3. Append signature hash type to transaction data (done)
        #4. Hash the transaction data 
        tran_req.vin=txins
        tran_req.outputs=txouts
        hash_data,transaction_raw_data=tran_req.get_hash_message()
        
        for i,(txin,addr) in enumerate(zip(txins,addrs)):
            if txin.is_coinbase():
                tr.vin[i]=txin
                break

            #5. Sign the transaction hash
            #6. Use the low s value
            privatekey_object=addr.to_privatekey_object()
            if privatekey_object is None:
                raise ValueError("privatekey_objectが生成できません")
            signature, r, s = addr.sign_with_low_s(privatekey_object, hash_data)
            
            #7. DER encode the signature 
            der_hex=addr.encode_ecdsa_signature_der(r,s).hex()
            
            #8. Append signature hash type to DER encoded signature 
            sighash_hex=struct.pack('B', tran_req.sighash).hex() #sighash追加。ここでは１バイト
            der_hex+=sighash_hex
            der_hex_length=struct.pack('B',len(der_hex)//2).hex()
            pk=addr.public_key
            pk_length=struct.pack('B',len(pk)//2).hex()
            
            #9. Construct the ScriptSig
            scriptsig=der_hex_length+der_hex+pk_length+pk
            
            #10. Insert the ScriptSig into the transaction
            txin.script_sig=BitcoinTransactionScriptSignature(hex=scriptsig,utxo_scriptpubkey_hex=txin.script_sig.utxo_scriptpubkey_hex)
            
            tr.vin[i]=txin
            
            # 署名の検証実行
            pubkey_objct=privatekey_object.public_key()
            result=pubkey_objct.verify(signature,bytes.fromhex(hash_data),ec.ECDSA(Prehashed(hashes.SHA256())))
        
        #レコード更新
        tran=BitcoinTransaction.generate_transaction(tr)
        blockchain_repo.create_transaction(tran)
        for v in tran.vin:
            blockchain_repo.create_transaction_vin(v)
        for o in tran.outputs:
            blockchain_repo.create_transaction_output(o)

        return tran
    
    except HTTPException:
        raise
    
    except Exception as e:
        tb_str = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail=f"エラーがスローされました:{e}.\nトレース情報:{tb_str}",
        )
        
@router.get("/chain/transaction/{transaction_id}", tags=["blockchain"])
async def get_transaction(
    transaction_id: str = Path(..., description="トランザクションID")
):
    try:
        tran = blockchain_repo.get_transaction(str(transaction_id))
        if tran is None:
            raise HTTPException(
                status_code=404,
                detail=f"指定されたID {transaction_id} のトランザクションが見つかりません"
            )
        
        return tran

    except HTTPException:
        raise
        
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"不正なトランザクションID形式です: {e}"
        )
    
    except Exception as e:
        tb_str = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail=f"エラーがスローされました:{e}.\nトレース情報:{tb_str}"
        )

@router.delete("/chain/transaction", tags=["blockchain"])
async def delete_transaction(
    partitionkey:str=Body(...,examples=["976d603e12976c66a3657be5a288f31d5e7c8fa6b7c19ce46628b4fbf0bfc2f6"]),
    rawkey:str=Body(...,examples=["89c2b66468f8d5adc6a5a6790d415c3a0602ed024335afd5bc40c6297bb774c0000000006a4730440220719019f0284a4fbd7602db29207931b31734863cab02900c417447ace74db4010220705314e92e7c7b2e40050d758cf2af3cb77e1171b0811a4e823674879c1837720121028484e9454c1a1f746f7aacd6b818ef80b39e986e2389e4d8d339143a87a883c9ffffffff"]),
):
    try:
        blockchain_repo.delete_transaction_vin(partitionkey,rawkey)
    except Exception as e:
        tb_str = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail=f"エラーがスローされました:{e}.\nトレース情報:{tb_str}"
        )

@router.get("/chain/scriptpubkey/{scriptpubkey}", tags=["blockchain"])
async def get_scriptpubkey(
    scriptpubkey: str = Path(..., description="16進文字列形式",examples=["76a91455ae51684c43435da751ac8d2173b2652eb6410588ac"]),
):
    script=Script.from_raw(scriptpubkey)
    
    return script.get_script()

@router.get("/chain/transaction/input/", tags=["blockchain"])
async def get_tran_in(
    txid: Optional[str] = Query(None, description="完全一致",examples=["c074b77b29c640bcd5af354302ed02063a5c410d79a6a5c6add5f86864b6c289"]),
    raw_data: Optional[str] = Query(None, description="前方一致",examples=["0000000000000000000000000000000000000000000000000000000000000000ffffffff1e"]),
):
    qf = QueryFilter()
    qf.add_filter(f"PartitionKey eq @PartitionKey", {"PartitionKey": txid})
    qf.add_filter(f"RowKey ge @RowKey", {"RowKey": raw_data})
    results=blockchain_repo.list_transaction_vin(qf)
    
    transaction_vins:List[BitcoinTransactionInput]=[]
    for input in results:
        if raw_data is None:
            transaction_vins=results
            break
        
        if input.raw_data.startswith(raw_data):
            transaction_vins.append(input)
    
    return transaction_vins