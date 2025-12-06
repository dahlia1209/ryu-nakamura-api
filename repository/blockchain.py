from managers.table_manager import TableConnectionManager
from models.query import QueryFilter
from typing import List, Optional, Dict, Any,Literal
from models.blockchain import Block,BlockEntity,PartitionType,Transaction,TransactionVin,TransactionOutput,TransactionEntity,TransactionVinEntity,TransactionOutputEntity
from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import EntityProperty, EdmType
from cryptography.hazmat.primitives.asymmetric import ec
from utils.blockchain import execute_script

#utilyty
def int_to_int64(entity_dict: dict) -> dict:
    for key, value in list(entity_dict.items()):
        if key not in ['PartitionKey', 'RowKey'] and isinstance(value, int):
            entity_dict[key] = EntityProperty(value, EdmType.INT64)
    return entity_dict

def unwrap_entity_properties(entity_dict: dict) -> dict:
    result = {}
    for key, value in entity_dict.items():
        if isinstance(value, EntityProperty):
            result[key] = value.value
        else:
            result[key] = value
    return result

#CLUD
def get_block(partition_type:PartitionType,row_key:str):
    try:
        block_entity=get_block_entity(partition_type, row_key)
        if not block_entity:
            return None
        
        qf=QueryFilter()
        qf.add_filter(f"PartitionKey eq @PartitionKey", {"PartitionKey": block_entity.hash})
        transactions=query_transaction(qf)

        return Block.model_construct(**block_entity.model_dump(),transactions=transactions)
    
    except ResourceNotFoundError as e:
        print(f"エンティティが見つかりません: {e}")
        return None
        
    except Exception as e:
        raise

def get_block_entity(partition_type:PartitionType,row_key:str):
    try:
        manager = TableConnectionManager()
        
        table_entity=manager.blockchain_block_table.get_entity(
            partition_key=partition_type,
            row_key=row_key
        )

        unwrapped_entity = unwrap_entity_properties(table_entity)
        return BlockEntity.model_validate(unwrapped_entity)
    
    except ResourceNotFoundError as e:
        print(f"エンティティが見つかりません: {e}")
        return None
        
    except Exception as e:
        raise

def create_block(block: Block) :
    try:
        manager = TableConnectionManager()

        current_block = get_block_entity("CURRENT", "0"*64)

        #previous hash check
        if current_block is None:
            if block.previous_hash != "0" * 64:
                raise ValueError(
                    f"genesis blockのprevious hashは{'0'*64}を指定してください"
                )
        elif current_block.hash != block.previous_hash:
            raise ValueError(
                f"previous_hashが不正です。現在のhash:{current_block.hash}, 対象のhash:{block.previous_hash}"
            )
        
        # vin utxo_txid check
        for t in block.transactions:
            if t.is_coinbase():
                continue
            
            for i,vin in enumerate(t.vin):
                # UTXOの存在確認
                qf = QueryFilter()
                qf.add_filter(f"PartitionKey eq @PartitionKey", {"PartitionKey": vin.utxo_txid})
                qf.add_filter(f"n eq @n", {"n": f"{vin.utxo_vout:020d}"})
                table_entities = manager.blockchain_transaction_output_table.query_entities(**qf.model_dump())
                table_entities_list = list(table_entities)
                
                # UTXOが存在しない
                if not table_entities_list:
                    # 同じブロック内の他のトランザクションでUTXOが生成されているかチェック
                    utxo_found_in_block = False
                    for tx in block.transactions:
                        if tx.txid == vin.utxo_txid:
                            if vin.utxo_vout < len(tx.outputs):
                                utxo_found_in_block = True
                                break
                    
                    if not utxo_found_in_block:
                        raise ValueError(f"指定されたUTXOが存在しません, utxo:{vin.utxo_txid}, vout:{vin.utxo_vout}")
                    else:
                        # 同一ブロック内のトランザクションからUTXO情報を取得
                        for tx in block.transactions:
                            if tx.txid == vin.utxo_txid:
                                utxo_output = tx.outputs[vin.utxo_vout]
                                vin.utxo_block_hash = block.hash
                                vin.script_type = utxo_output.script_type
                                vin.utxo_script_pubkey = utxo_output.script_pubkey_hex
                                
                                # 署名検証
                                raw_message = t.get_hash_raw_message(i)
                                message = t.hash256_hex(raw_message, False)
                                if not execute_script(vin.script_sig_asm, utxo_output.script_pubkey_asm, message, block.timestamp):
                                    raise ValueError(f"署名検証エラーです。script sig:{vin.script_sig_asm},script pubkey:{utxo_output.script_pubkey_asm},script type:{utxo_output.script_type}")
                                break
                        # 次のvinへ続行
                        continue
                
                # UTXOが複数存在（データ整合性エラー）
                if len(table_entities_list) > 1:
                    raise ValueError(f"指定されたUTXOが複数存在します, utxo:{vin.utxo_txid}, vout:{vin.utxo_vout}")
                
                # UTXOの使用済みチェック
                qf2 = QueryFilter()
                qf2.add_filter(f"utxo_txid eq @utxo_txid", {"utxo_txid": vin.utxo_txid})
                qf2.add_filter(f"utxo_vout eq @utxo_vout", {"utxo_vout": f"{vin.utxo_vout:020d}"})
                table2_entities = manager.blockchain_transaction_vin_table.query_entities(**qf2.model_dump())
                table2_entities_list = list(table2_entities)
                
                if table2_entities_list:
                    raise ValueError(f"指定されたUTXOは利用済みです, utxo:{vin.utxo_txid}, vout:{vin.utxo_vout}")
                
                # UTXOの情報を取得してvinに設定
                utxo_output = TransactionOutputEntity.model_validate(
                    unwrap_entity_properties(table_entities_list[0])
                )
                vin.utxo_block_hash = utxo_output.block_hash
                vin.script_type = utxo_output.script_type
                vin.utxo_script_pubkey=utxo_output.script_pubkey_hex

                #verify signature
                raw_message=t.get_hash_raw_message(i)
                print("raw_message",raw_message)
                message=t.hash256_hex(raw_message,False)
                if not execute_script(vin.script_sig_asm,utxo_output.script_pubkey_asm,message,block.timestamp):
                    raise ValueError(f"署名検証エラーです。script sig:{vin.script_sig_asm},script pubkey:{utxo_output.script_pubkey_asm},script type:{utxo_output.script_type}")
                

        #height更新
        block.height = current_block.height + 1 if current_block else 0
        for t in block.transactions:
            t.block_height=block.height

        # CURRENTエンティティを更新
        current_entity = block.to_entity("CURRENT", "0"*64)
        entity_dict=int_to_int64(current_entity.model_dump(exclude_none=True))
        manager.blockchain_block_table.upsert_entity(entity_dict)
        
        # HISTORYエンティティを作成
        history_entity = block.to_entity("HISTORY", block.hash)
        entity_dict=int_to_int64(history_entity.model_dump(exclude_none=True))
        manager.blockchain_block_table.create_entity(entity_dict)

        #Transactionエンティティ作成
        for t in block.transactions:
            create_transaction(t)
            for vin in t.vin:
                create_transaction_vin(vin)
            for output in t.outputs:
                create_transaction_output(output)
        
        return block
        
    except Exception as e:
        raise

def delete_block(partition_type: PartitionType, row_key: str):
    try:
        manager = TableConnectionManager()
        
        # 削除対象のブロックを取得
        block_entity = get_block_entity(partition_type, row_key)
        if not block_entity:
            print(f"削除対象のブロックが見つかりません: {row_key}")
            return False
        
        block_hash = block_entity.hash
        
        # ブロックに紐づくトランザクションを取得
        qf = QueryFilter()
        qf.add_filter(f"PartitionKey eq @PartitionKey", {"PartitionKey": block_hash})
        transaction_entities = query_transaction_entity(qf)
        
        # 各トランザクションのvin/outputを削除
        for tx_entity in transaction_entities:
            txid = tx_entity.txid
            
            # トランザクションのvinを削除
            qf_tx = QueryFilter()
            qf_tx.add_filter(f"PartitionKey eq @PartitionKey", {"PartitionKey": txid})
            vin_entities = query_transaction_vin_entity(qf_tx)
            
            for vin_entity in vin_entities:
                manager.blockchain_transaction_vin_table.delete_entity(
                    partition_key=vin_entity.PartitionKey,
                    row_key=vin_entity.RowKey
                )
            
            # トランザクションのoutputを削除
            output_entities = query_transaction_output_entity(qf_tx)
            
            for output_entity in output_entities:
                manager.blockchain_transaction_output_table.delete_entity(
                    partition_key=output_entity.PartitionKey,
                    row_key=output_entity.RowKey
                )
            
            # トランザクション自体を削除
            manager.blockchain_transaction_table.delete_entity(
                partition_key=tx_entity.PartitionKey,
                row_key=tx_entity.RowKey
            )
        
        # 前のブロックを取得（CURRENTエンティティ更新用）
        if block_entity.previous_hash and block_entity.previous_hash != "0" * 64:
            previous_block_entity = get_block_entity("HISTORY", block_entity.previous_hash)
            
            if previous_block_entity:
                # 前のブロックの完全な情報を取得
                previous_block = get_block("HISTORY", block_entity.previous_hash)
                
                if previous_block:
                    # CURRENTエンティティを前のブロック情報に更新
                    current_entity = previous_block.to_entity("CURRENT", "0" * 64)
                    entity_dict = int_to_int64(current_entity.model_dump(exclude_none=True))
                    manager.blockchain_block_table.upsert_entity(entity_dict)
                    print(f"CURRENTエンティティを前のブロックに更新しました: {block_entity.previous_hash}")
            else:
                print(f"警告: 前のブロックが見つかりません: {block_entity.previous_hash}")
        else:
            # ジェネシスブロックを削除する場合、CURRENTエンティティを削除
            try:
                manager.blockchain_block_table.delete_entity(
                    partition_key="CURRENT",
                    row_key="0" * 64
                )
                print("ジェネシスブロック削除のため、CURRENTエンティティを削除しました")
            except ResourceNotFoundError:
                print("CURRENTエンティティが存在しません")
        
        # HISTORYエンティティ（削除対象ブロック）を削除
        manager.blockchain_block_table.delete_entity(
            partition_key="HISTORY",
            row_key=block_hash
        )
        
        
        print(f"ブロックを削除しました: {block_hash}")
        return True
    
    except ResourceNotFoundError as e:
        print(f"エンティティが見つかりません: {e}")
        return False
        
    except Exception as e:
        print(f"ブロック削除中にエラーが発生しました: {e}")
        raise

def query_transaction(query_filter:QueryFilter):
    try:
        transaction_entities=query_transaction_entity(query_filter)

        transactions:List[Transaction]=[]
        for e in transaction_entities:
            qf=QueryFilter()
            qf.add_filter(f"PartitionKey eq @PartitionKey", {"PartitionKey": e.txid})
            vin=query_transaction_vin(qf)
            output=query_transaction_output(qf)
            transactions.append(Transaction.model_construct(**e.model_dump(exclude={"PartitionKey","RowKey"}),vin=vin,outputs=output))
        return transactions

    except ResourceNotFoundError as e:
        print(f"エンティティが見つかりません: {e}")
        return None
        
    except Exception as e:
        raise

def query_transaction_entity(query_filter:QueryFilter):
    try:
        manager = TableConnectionManager()
        
        table_entities=manager.blockchain_transaction_table.query_entities(**query_filter.model_dump())
        return [TransactionEntity.model_validate(unwrap_entity_properties(e)) for e in table_entities]
    
    except ResourceNotFoundError as e:
        print(f"エンティティが見つかりません: {e}")
        return None
        
    except Exception as e:
        raise

def get_transaction_entity(block_hash:str,txid:str):
    try:
        manager = TableConnectionManager()
        
        table_entity=manager.blockchain_transaction_table.get_entity(
            partition_key=block_hash,
            row_key=txid
        )

        unwrapped_entity = unwrap_entity_properties(table_entity)
        return TransactionEntity.model_validate(unwrapped_entity)
    
    except ResourceNotFoundError as e:
        print(f"エンティティが見つかりません: {e}")
        return None
        
    except Exception as e:
        raise

def create_transaction(tran: Transaction) :
    try:
        manager = TableConnectionManager()

        #block check
        block_entity = get_block_entity("HISTORY", tran.block_hash)
        if not block_entity:
            raise ValueError(
                f"blockが存在しません。対象のblock hash:{tran.block_hash}"
            )

        #エンティティ作成
        tran_entity= tran.to_entity()
        entity_dict=int_to_int64(tran_entity.model_dump(exclude_none=True))
        manager.blockchain_transaction_table.create_entity(entity_dict)

        return tran
        
    except Exception as e:
        raise

def query_transaction_vin(query_filter:QueryFilter):
    try:
        transaction_vin_entities=query_transaction_vin_entity(query_filter)
        return [e.to_original() for e in transaction_vin_entities]

    except ResourceNotFoundError as e:
        print(f"エンティティが見つかりません: {e}")
        return None
        
    except Exception as e:
        raise

def query_transaction_vin_entity(query_filter:QueryFilter):
    try:
        manager = TableConnectionManager()
        
        table_entities=manager.blockchain_transaction_vin_table.query_entities(**query_filter.model_dump())
        return [TransactionVinEntity.model_validate(unwrap_entity_properties(e)) for e in table_entities]
    
    except ResourceNotFoundError as e:
        print(f"エンティティが見つかりません: {e}")
        return None
        
    except Exception as e:
        raise

def create_transaction_vin(vin: TransactionVin):
    try:
        manager = TableConnectionManager()

        #transaction check
        tran_entity = get_transaction_entity(vin.spent_block_hash,vin.spent_txid)
        if not tran_entity:
            raise ValueError(
                f"transactionが存在しません。対象のtxid:{vin.spent_block_hash},block hash:{vin.spent_txid}"
            )
        
        #エンティティ作成
        vin_entity = vin.to_entity()
        entity_dict=int_to_int64(vin_entity.model_dump(exclude_none=True))
        manager.blockchain_transaction_vin_table.create_entity(entity_dict)
        return vin
        
    except Exception as e:
        raise

def query_transaction_output_entity(query_filter:QueryFilter):
    try:
        manager = TableConnectionManager()
        
        table_entities=manager.blockchain_transaction_output_table.query_entities(**query_filter.model_dump())
        return [TransactionOutputEntity.model_validate(unwrap_entity_properties(e)) for e in table_entities]
    
    except ResourceNotFoundError as e:
        print(f"エンティティが見つかりません: {e}")
        return None
        
    except Exception as e:
        raise

def query_transaction_output(query_filter:QueryFilter):
    try:
        transaction_output_entities=query_transaction_output_entity(query_filter)
        return [e.to_original() for e in transaction_output_entities]

    except ResourceNotFoundError as e:
        print(f"エンティティが見つかりません: {e}")
        return None
        
    except Exception as e:
        raise

def create_transaction_output(output: TransactionOutput) -> bool:
    try:
        manager = TableConnectionManager()

        #transaction check
        tran_entity = get_transaction_entity(output.block_hash,output.txid)
        if not tran_entity:
            raise ValueError(
                f"transactionが存在しません。対象のtxid:{output.block_hash},block hash:{output.txid}"
            )
        
        #エンティティ作成
        output_entity=output.to_entity()
        entity_dict=int_to_int64(output_entity.model_dump(exclude_none=True))

        manager.blockchain_transaction_output_table.create_entity(entity_dict)
        return output
        
    except Exception as e:
        raise 
