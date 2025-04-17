from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import List, Optional,Dict,Any
from datetime import datetime
import re
import uuid
from azure.data.tables import TableEntity
import json


class QueryFilter(BaseModel):
    query_filter:Optional[str]=None
    parameters:Dict[str, Any]={}
    private_filters:List[str]=Field(default_factory=list, alias="_filters")
    private_params:Dict[str, Any]=Field(default={}, alias="_params")
    
    def add_filter(self,filter:str,param:Dict[str, Any]):
        first_key, first_value = next(iter(param.items()))
        if first_value:
            self.private_filters.append(filter)
            self.private_params.update(param)
    
    def dump(self):
        self.query_filter=" and ".join(self.private_filters)
        self.parameters=self.private_params
        return self.model_dump(include={"query_filter","parameters"})
        
    
    