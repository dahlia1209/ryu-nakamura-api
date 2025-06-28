from fastapi import FastAPI
from fastapi.testclient import TestClient
from api import app
import os
from unittest.mock import Mock, patch
from models.contact import ContactMessage
from models.user import User,UserTableEntity,AzureUser
import uuid
import json
import pytest

client = TestClient(app)

@pytest.fixture()
def test_prepare(auth_headers):
    user_id=os.getenv("AZURE_LOCAL_CLIENT_APP_ID")
    
    #ユーザ情報取得
    def get_user():
        return client.get(
            f"/users/{user_id}",
            headers=auth_headers,
        )
        
    #ユーザ削除
    def delete_user():
        return client.delete(
            f"/users/{user_id}",
            headers=auth_headers,
        )
        
    reponse=get_user()
    if not reponse.status_code==404:
        delete_user()
        reponse=get_user()
    return True
    
def test_create_user(auth_headers,test_prepare):
    user_id=os.getenv("AZURE_LOCAL_CLIENT_APP_ID")
    user=User(id=user_id,email='wakyaroya@cocoro.uk',provider='local')
    response= client.put(
            f"/users/{user_id}",
            headers=auth_headers,
            json=json.loads(user.model_dump_json()),
            params={'mode':'upsert'}
        )
    print(response.json())
    assert response.status_code==201
    
def test_get_user(auth_headers):
    user_id=os.getenv("AZURE_LOCAL_CLIENT_APP_ID")
    response= client.get(
            f"/users/{user_id}",
            headers=auth_headers,
        )
    assert response.status_code==200
    response_user=User(**response.json())
    assert str(response_user.id)==user_id

def test_upsert_user(auth_headers):
    user_id=os.getenv("AZURE_LOCAL_CLIENT_APP_ID")
    user=User(id=user_id,email='sohuma@meruado.uk',provider='local')
    response= client.put(
            f"/users/{user_id}",
            headers=auth_headers,
            json=json.loads(user.model_dump_json()),
        )
    assert response.status_code==200
    response_user=User(**response.json())
    assert response_user.email=='sohuma@meruado.uk'
    
def test_delete_user(auth_headers):
    user_id=os.getenv("AZURE_LOCAL_CLIENT_APP_ID")
    response= client.delete(
            f"/users/{user_id}",
            headers=auth_headers,
        )
    assert response.status_code==204

    
    

# def test_delete_user_item(auth_headers):
#     user_id=os.getenv("AZURE_LOCAL_CLIENT_APP_ID")

#     response=client.delete(
#         f"/users/{user_id}",
#         headers=auth_headers,
#     )
#     assert response.status_code==204
    
    
