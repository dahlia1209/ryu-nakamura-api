import azure.functions as func
import logging
import datetime
from api import app as fastapi_app
from managers.table_manager import TableConnectionManager
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient,generate_blob_sas,BlobSasPermissions
import os

app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.ANONYMOUS)
