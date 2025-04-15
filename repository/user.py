from azure.data.tables import TableServiceClient
from azure.identity import DefaultAzureCredential
from azure.core.exceptions import ResourceExistsError
from managers.table_connection import TableConnectionManager
from models.content import Content,ContentTableEntity
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import uuid