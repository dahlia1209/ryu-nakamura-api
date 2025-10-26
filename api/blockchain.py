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

@router.post("/blockchain/block", tags=["blockchain"])
async def generate_block(
    block: BlockRequest = Body(
        ...,
        examples=[
            # #0 block
            {
                "version": 1,
                "previous_block_hash": "0000000000000000000000000000000000000000000000000000000000000000",
                "time": 1231006505,
                "bits": "1d00ffff",
                "nonce": 2083236893,
                "txids":[
                ]
            },
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
            
            
            
        ],
    ),
    to_scriptpubkey:str=Body(...,examples=["76a9147fc9ea0badb18a27533949c1c60e629fe0d6250988ac"]),
    locktime:int=Body(0)
):
    coinbase_scriptpubkey=TransactionScriptPubkey.coinbase(block_height=0)
    coinbase_tran=Transaction.generate_coinbase(coinbase_scriptpubkey.hex,to_scriptpubkey,block.version,locktime)
    block.txids.append(coinbase_tran.txid)
    print("coinbase_tran",coinbase_tran)
    return Block.generate_block(block)


##後で削除 なにこれ？
@router.get("/blockchain/address", tags=["blockchain"],response_model=Address)
async def get_address(
    address: str=Query(..., description="address to get")
):
    try:
        addr=Address.from_address(address)
        scriptpubkey=addr.get_scriptpubkey()
        
        # ba=blockchain_repo.get_address(str(address_id))
        # if ba is None:
        #     raise HTTPException(
        #         status_code=404,
        #         detail=f"指定されたID {address_id} のデータが見つかりません"
        #     )
            
        return addr

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

@router.get("/blockchain/address/{address_id}", tags=["blockchain"],response_model=Address)
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


@router.post("/blockchain/transaction", tags=["blockchain"])
async def create_transaction(
    tran_req:TransactionRequest=Body(...,examples=[
        #first sent
        {
                "version": 1,
                "locktime": 0,
                "vin": [
                    {
                        "txid": "59087cd860fc409fa135f3420d53cccb21a091df55892d8d49aac54a58f39aaa",
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
                            "hex": "76a9147fc9ea0badb18a27533949c1c60e629fe0d6250988ac", #
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
    address_ids_for_signature:List[str]=Body(...,examples=[["b8a1027c-985c-4744-9704-d312f2711176"]]),
):
    try:
        tr=tran_req.model_copy()
        #アドレス取得
        addresses=[blockchain_repo.get_address(str(address_id)) for address_id in address_ids_for_signature]
        
        #トランザクション作成
        txins:List[TransactionInput]=[]
        txouts:List[TransactionOutput]=[]
        addrs:List[Address]=[]
        for v in tr.vin:
            if v.is_coinbase():
                height=format(0, '06X') #ブロック高0
                previous_scriptpubkey=f"03{height}1976a914d60175b6845c4e6076f7b7a2353f280ef838a79f88ac" #Mined by Ryu nakamuraのスクリプト
                txin=TransactionInput(script_sig=TransactionScriptSignature(hex=previous_scriptpubkey),**v.model_dump(exclude={"script_sig"}))
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
                qf.add_filter(f"txid eq @txid", {"txid": v.txid})
                qf.add_filter(f"vout eq @vout", {"vout": v.vout})
                spent_utxo=blockchain_repo.list_transaction_vin(qf)
                if spent_utxo:
                    raise HTTPException(
                        status_code=400,
                        detail=f"UTXOはすでに使用されています。UTXOのtxid:{spent_utxo[0].parent_id},output:{spent_utxo[0].n_to_hex()}",
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
                
                txin=TransactionInput(script_sig=TransactionScriptSignature(hex=v.script_sig.hex,utxo_scriptpubkey_hex=previous_scriptpubkey),**v.model_dump(exclude={"script_sig"}))
                txins.append(txin)
                addrs.append(tar_address[0])
        for i,o in enumerate(tr.outputs):
            #todoスクリプト公開鍵の検証
            
            o.n=i
            txouts.append(o)
        
        #署名処理
        
        tran_req.vin=txins
        tran_req.outputs=txouts
        
        
        for i,(txin,addr) in enumerate(zip(txins,addrs)):
            if txin.is_coinbase():
                tr.vin[i]=txin
                break
            
            #1. Remove existing ScriptSigs  (done)
            #2. Put the ScriptPubKey as a placeholder in the ScriptSig (done)
            #3. Append signature hash type to transaction data (done)
            #4. Hash the transaction data 
            hash_data,transaction_raw_data=tran_req.get_hash_message(i)
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
            txin.script_sig=TransactionScriptSignature(hex=scriptsig,utxo_scriptpubkey_hex=txin.script_sig.utxo_scriptpubkey_hex)
            
            tr.vin[i]=txin
            
            # 署名の検証実行
            pubkey_objct=privatekey_object.public_key()
            result=pubkey_objct.verify(signature,bytes.fromhex(hash_data),ec.ECDSA(Prehashed(hashes.SHA256())))
        
        #レコード更新
        tran=Transaction.generate_transaction(tr)
        blockchain_repo.create_transaction(tran)
        blockchain_repo.batch_transaction_vin(tran.vin)
        blockchain_repo.batch_transaction_output(tran.outputs)

        return tran
    
    except TableTransactionError as e:
        tb_str = traceback.format_exc()
        raise HTTPException(status_code=400,
            detail=f"トランザクションエラー: {e}.\nトレース情報:{tb_str}"
            )
    
    except HTTPException:
        raise
    
    except Exception as e:
        tb_str = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail=f"エラーがスローされました:{e}.\nトレース情報:{tb_str}",
        )

# なにこれ？
@router.get("/blockchain/transaction/txid", tags=["blockchain"])
async def get_transaction(
   address: list[str] = Query(default=[]),
):
    try:
        
        addr=Address.from_address(address)
        scriptpubkey=addr.get_scriptpubkey()
        
        results:List[Transaction]=[]
        if not address:
            raise HTTPException(status_code=400,detail=f"addressは1つ以上指定してください")
        elif len(address)>10:
            raise HTTPException(status_code=400,detail=f"addressの数は10以下にしてください")
        
        qf=QueryFilter()
        for a in address:
            qf.add_filter(f"category eq @category", {"category": category})
        tran = blockchain_repo.query_transaction(str(transaction_id))
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

@router.get("/blockchain/transaction/{transaction_id}", tags=["blockchain"])
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

@router.delete("/blockchain/transaction", tags=["blockchain"])
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

@router.get("/blockchain/scriptpubkey/{scriptpubkey}", tags=["blockchain"])
async def get_scriptpubkey(
    scriptpubkey: str = Path(..., description="16進文字列形式",examples=["76a91455ae51684c43435da751ac8d2173b2652eb6410588ac"]),
):
    script=Script.from_raw(scriptpubkey)
    
    return script.get_script()

@router.get("/blockchain/transaction/input/", tags=["blockchain"])
async def get_tran_in(
    txid: Optional[str] = Query(None, description="完全一致",examples=["c074b77b29c640bcd5af354302ed02063a5c410d79a6a5c6add5f86864b6c289"]),
    raw_data: Optional[str] = Query(None, description="前方一致",examples=["0000000000000000000000000000000000000000000000000000000000000000ffffffff1e"]),
):
    qf = QueryFilter()
    qf.add_filter(f"PartitionKey eq @PartitionKey", {"PartitionKey": txid})
    qf.add_filter(f"RowKey ge @RowKey", {"RowKey": raw_data})
    results=blockchain_repo.list_transaction_vin(qf)
    
    transaction_vins:List[TransactionInput]=[]
    for input in results:
        if raw_data is None:
            transaction_vins=results
            break
        
        if input.raw_data.startswith(raw_data):
            transaction_vins.append(input)
    
    return transaction_vins
