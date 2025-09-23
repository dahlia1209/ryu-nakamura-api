from managers.table_manager import TableConnectionManager
from models.query import QueryFilter
from typing import List, Optional, Dict, Any
from models.blockchain import BitcoinAddress,AddressTableEnitity,BitcoinTransaction,TransactionTableEntity,TransactionVinTableEntity,BitcoinTransactionInput,TransactionOutputTableEntity,BitcoinTransactionOutput
import json
from azure.core.exceptions import ResourceNotFoundError

def get_address(address_id:str) :
    try:
        manager = TableConnectionManager()
        
        entity=manager.address_table.get_entity(partition_key='address',row_key=address_id)
        address=AddressTableEnitity.from_entity(entity).to_address()
        
        return address
    
    except ResourceNotFoundError as e:
        print(f"エンティティが見つかりません: {e}")
        return None
        
    except Exception as e:
        raise ValueError(f"Error retrieving adderess: {str(e)}")

def create_address(address: BitcoinAddress) -> bool:
    """アドレスの作成または更新"""

    try:
        manager = TableConnectionManager()
        address_entity=AddressTableEnitity.from_address(address)
        
        manager.address_table.create_entity(address_entity.model_dump(exclude_none=True))
        return True
        
    except Exception as e:
        raise ValueError(f"Error retrieving addresss: {str(e)}")
    
def get_transaction(transaction_id:str):
    try:
        manager = TableConnectionManager()
        
        entity=manager.coin_transaction_table.get_entity(partition_key='coin_transaction',row_key=transaction_id)
        transaction_entity=TransactionTableEntity.from_entity(entity)
        # tran_vin=[TransactionVinTableEntity.from_entity(manager.coin_transaction_vin_table.get_entity(partition_key='coin_transaction_vin',row_key=id)).to_transaction_vin() for id in  json.loads(transaction_entity.vin)]
        # tran_outputs=[TransactionOutputTableEntity.from_entity(manager.coin_transaction_output_table.get_entity(partition_key='coin_transaction_output',row_key=id)).to_transaction_output() for id in  json.loads(transaction_entity.outputs)]
        tran=BitcoinTransaction.from_trancsation_entity(transaction_entity)
        
        return tran
    
    except ResourceNotFoundError as e:
        print(f"エンティティが見つかりません: {e}")
        return None
        
    except Exception as e:
        raise
    
def create_transaction(tran: BitcoinTransaction) -> bool:
    try:
        manager = TableConnectionManager()
        tran_entity=TransactionTableEntity.from_transaction(tran)
        
        manager.coin_transaction_table.create_entity(tran_entity.model_dump(exclude_none=True))
        return True
        
    except Exception as e:
        raise ValueError(f"Error: {str(e)}")
    
def list_transaction_vin(query_filter:QueryFilter):
    try:
        manager = TableConnectionManager()
        
        entities=manager.coin_transaction_vin_table.query_entities(**query_filter.model_dump())
        transaction_vin_entity=[TransactionVinTableEntity.from_entity(e).to_transaction_vin() for e in entities]
        
        return transaction_vin_entity
    
    except ResourceNotFoundError as e:
        print(f"エンティティが見つかりません: {e}")
        return None
        
    except Exception as e:
        raise ValueError(f"Error: {str(e)}")
    
def create_transaction_vin(tran_input: BitcoinTransactionInput) -> bool:
    try:
        manager = TableConnectionManager()
        tran_entity=TransactionVinTableEntity.from_transaction_vin(tran_input)
        manager.coin_transaction_vin_table.create_entity(tran_entity.model_dump(exclude_none=True))
        return True
        
    except Exception as e:
        raise ValueError(f"Error: {str(e)}")

def delete_transaction_vin(partitionkey:str,rawkey:str) -> bool:
    try:
        manager = TableConnectionManager()
        manager.coin_transaction_vin_table.delete_entity({
    "PartitionKey": partitionkey,
    "RowKey": rawkey
})
        return True
        
    except Exception as e:
        raise ValueError(f"Error: {str(e)}")
    
def get_transaction_output(pk:str,rk:str):
    try:
        manager = TableConnectionManager()
        
        entity=manager.coin_transaction_output_table.get_entity(partition_key=pk,row_key=rk)
        transaction_outputs_entity=TransactionOutputTableEntity.from_entity(entity).to_transaction_output()
        
        return transaction_outputs_entity
    
    except ResourceNotFoundError as e:
        print(f"エンティティが見つかりません: {e}")
        return None
    
    except Exception as e:
        raise ValueError(f"Error: {str(e)}")
    
def create_transaction_output(tran_output: BitcoinTransactionOutput) -> bool:
    try:
        manager = TableConnectionManager()
        tran_entity=TransactionOutputTableEntity.from_transaction_output(tran_output)
        manager.coin_transaction_output_table.create_entity(tran_entity.model_dump(exclude_none=True))
        return True
        
    except Exception as e:
        raise ValueError(f"Error: {str(e)}")