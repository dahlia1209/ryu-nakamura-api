from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Optional,Dict,Any,Literal
from datetime import datetime
import re
import uuid
from azure.data.tables import TableEntity
import json


class QueryFilter(BaseModel):
    query_filter:Optional[str]=None
    parameters:Dict[str, Any]={}
    
    def add_filter(self,filter:str,param:Dict[str, Any],operator:Literal['and','or']='and'):
        """
        Examples:
            >>> add_filter(f"PartitionKey eq @PartitionKey", {"PartitionKey": "01234"})
        """
        def query_filter_append(val:str):
            if self.query_filter:
                self.query_filter+=f" {operator} {val}"
            else:
                self.query_filter=val
        first_key, first_value = next(iter(param.items()))
        if first_value:
            query_filter_append(filter)
            self.parameters.update(param)
    
    def is_query(self):
        return True if  self.query_filter is not None else False

    
    