from managers.table_manager import TableConnectionManager
from models.query import QueryFilter
from typing import List, Optional, Dict, Any
from models.blockchain import Address,AddressTableEnitity,Transaction,TransactionTableEntity,TransactionVinTableEntity,TransactionInput,TransactionOutputTableEntity,TransactionOutput,Block,BlockTableEnitity
import json
from azure.core.exceptions import ResourceNotFoundError
from azure.data.tables import TransactionOperation,TableTransactionError,TableEntity
from datetime import datetime

def get_address(address_id:str) :
    try:
        manager = TableConnectionManager()
        
        entity=manager.blockchain_address_table.get_entity(partition_key='address',row_key=address_id)
        address=AddressTableEnitity.from_entity(entity).to_address()
        
        return address
    
    except ResourceNotFoundError as e:
        print(f"エンティティが見つかりません: {e}")
        return None
        
    except Exception as e:
        raise ValueError(f"Error retrieving adderess: {str(e)}")

def create_address(address: Address) -> bool:
    """アドレスの作成または更新"""

    try:
        manager = TableConnectionManager()
        address_entity=AddressTableEnitity.from_address(address)
        
        manager.blockchain_address_table.create_entity(address_entity.model_dump(exclude_none=True))
        return True
        
    except Exception as e:
        raise ValueError(f"Error retrieving addresss: {str(e)}")

def get_block(hash:str="0" * 64):
    try:
        manager = TableConnectionManager()
        
        # entity=TableEntity()
        # if hash is None:
        #     qf=QueryFilter()
        #     results=manager.blockchain_block_table.query_entities(
        #          **qf.model_dump(),
        #          results_per_page=1,
                 
        #     )
        #     entities=[BlockTableEnitity.from_entity(e) for e in results]
            
        #     if entities:
        #         entity=entities[0]
        #     else:
        #         raise ResourceNotFoundError(f"エンティティが見つかりません")
        # else:
        entity=manager.blockchain_block_table.get_entity(
            partition_key="blockchain_block",
            row_key=hash
        )
        block=BlockTableEnitity.from_entity(entity).to_block()
        
        return block
    
    except ResourceNotFoundError as e:
        print(f"エンティティが見つかりません: {e}")
        return None
        
    except Exception as e:
        raise
    
def create_block(block: Block) -> bool:
    try:
        
        manager = TableConnectionManager()
        block_entity=BlockTableEnitity.from_block(block)
        current_block_entity=block_entity.model_copy()
        current_block_entity.RowKey="0"*64
        
        block_entities = [
            (TransactionOperation.UPSERT,current_block_entity.model_dump(exclude_none=True)),
            (TransactionOperation.CREATE,block_entity.model_dump(exclude_none=True)),
        ]
        manager.blockchain_block_table.submit_transaction(block_entities)
        
        # manager.blockchain_block_table.create_entity(block_entity.model_dump(exclude_none=True))
        return True
        
    except Exception as e:
        raise
    
def get_transaction(transaction_id:str):
    try:
        manager = TableConnectionManager()
        
        entity=manager.blockchain_transaction_table.get_entity(partition_key='blockchain_transaction',row_key=transaction_id)
        transaction_entity=TransactionTableEntity.from_entity(entity)
        qf=QueryFilter()
        qf.add_filter(f"PartitionKey eq @PartitionKey", {"PartitionKey": transaction_entity.RowKey})
        vins=list_transaction_vin(qf)
        outs=list_transaction_output(qf)
        # tran=BitcoinTransaction.from_trancsation_entity(transaction_entity,vin_entities,out_entities)
        tran=Transaction(txid=transaction_entity.RowKey,vin=vins,outputs=outs,
                **transaction_entity.model_dump(exclude={"PartitionKey","RowKey","vin","outputs","txid"}))
        
        return tran
    
    except ResourceNotFoundError as e:
        print(f"エンティティが見つかりません: {e}")
        return None
        
    except Exception as e:
        raise

def create_transaction(tran: Transaction) -> bool:
    try:
        manager = TableConnectionManager()
        tran_entity=TransactionTableEntity.from_transaction(tran)
        
        manager.blockchain_transaction_table.create_entity(tran_entity.model_dump(exclude_none=True))
        return True
        
    except Exception as e:
        raise

def list_transaction_vin(query_filter:QueryFilter):
    try:
        manager = TableConnectionManager()

        entities=manager.blockchain_transaction_vin_table.query_entities(**query_filter.model_dump())
        transaction_vin_entity=[TransactionVinTableEntity.from_entity(e).to_transaction_vin() for e in entities]

        return transaction_vin_entity

    except ResourceNotFoundError as e:
        print(f"エンティティが見つかりません: {e}")
        result:List[TransactionInput]= []
        return result

    except Exception as e:
        raise ValueError(f"Error: {str(e)}")
    
def list_transaction_output(query_filter:QueryFilter):
    try:
        manager = TableConnectionManager()

        entities=manager.blockchain_transaction_output_table.query_entities(**query_filter.model_dump())
        transaction_output_entity=[TransactionOutputTableEntity.from_entity(e).to_transaction_output() for e in entities]

        return transaction_output_entity

    except ResourceNotFoundError as e:
        print(f"エンティティが見つかりません: {e}")
        result:List[TransactionOutput]= []
        return result

    except Exception as e:
        raise ValueError(f"Error: {str(e)}")


def batch_transaction_vin(tran_inputs: List[TransactionInput]) -> bool:
    try:
        manager = TableConnectionManager()
        tran_entities = [
            (
                TransactionOperation.CREATE,
                TransactionVinTableEntity.from_transaction_vin(tran_input).model_dump(
                    exclude_none=True
                ),
            )
            for tran_input in tran_inputs
        ]
        manager.blockchain_transaction_vin_table.submit_transaction(tran_entities)
        return True

    except TableTransactionError as e:
        print(f"トランザクションエラー: {e}")
    
    except Exception as e:
        raise


def create_transaction_vin(tran_input: TransactionInput) -> bool:
    try:
        manager = TableConnectionManager()
        tran_entity=TransactionVinTableEntity.from_transaction_vin(tran_input)
        manager.blockchain_transaction_vin_table.create_entity(tran_entity.model_dump(exclude_none=True))
        return True
        
    except Exception as e:
        raise 

def delete_transaction_vin(partitionkey:str,rawkey:str) -> bool:
    try:
        manager = TableConnectionManager()
        manager.blockchain_transaction_vin_table.delete_entity({
    "PartitionKey": partitionkey,
    "RowKey": rawkey
})
        return True
        
    except Exception as e:
        raise ValueError(f"Error: {str(e)}")

def get_transaction_output(pk:str,rk:str):
    try:
        manager = TableConnectionManager()

        entity=manager.bc_transaction_output_table.get_entity(partition_key=pk,row_key=rk)
        transaction_outputs_entity=TransactionOutputTableEntity.from_entity(entity).to_transaction_output()

        return transaction_outputs_entity

    except ResourceNotFoundError as e:
        print(f"エンティティが見つかりません: {e}")
        return None

    except Exception as e:
        raise 


def batch_transaction_output(tran_outputs: List[TransactionOutput]) -> bool:
    try:
        manager = TableConnectionManager()
        tran_entities = [
            (
                TransactionOperation.CREATE,
                TransactionOutputTableEntity.from_transaction_output(
                    tran_output
                ).model_dump(exclude_none=True),
            )
            for tran_output in tran_outputs
        ]
        manager.blockchain_transaction_output_table.submit_transaction(tran_entities)
        return True

    except Exception as e:
        raise


def create_transaction_output(tran_output: TransactionOutput) -> bool:
    try:
        manager = TableConnectionManager()
        tran_entity=TransactionOutputTableEntity.from_transaction_output(tran_output)
        manager.blockchain_transaction_output_table.create_entity(tran_entity.model_dump(exclude_none=True))
        return True
        
    except Exception as e:
        raise 
