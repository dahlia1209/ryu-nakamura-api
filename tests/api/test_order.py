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
from models.order import OrderItem,Order,OrderStatus,OrderResponse
import uuid
import subprocess
import time
import requests

client = TestClient(app)


@pytest.fixture()
def test_prepare(auth_headers):
    user_id=os.getenv("AZURE_LOCAL_CLIENT_APP_ID")
    user=User(id=user_id,email='wakyaroya@cocoro.uk',provider='local')
    response= client.put(
            f"/users/{user_id}",
            headers=auth_headers,
            json=json.loads(user.model_dump_json()),
            params={'mode':'upsert'}
        )
    return True

@pytest.fixture()
def test_post(auth_headers):
    user_id=os.getenv("AZURE_LOCAL_CLIENT_APP_ID")
    order_id='fff31094-2c50-450f-b689-00b7d5868b38'
    response= client.delete(
            f"/orders/{order_id}",
            headers=auth_headers,
        )
    response= client.delete(
            f"/users/{user_id}",
            headers=auth_headers,
        )
    return True

def test_make_checkout_session(auth_headers,test_prepare):
    order_item=OrderItem(
        id='fff31094-2c50-450f-b689-00b7d5868b38',
        user_id=os.getenv("AZURE_LOCAL_CLIENT_APP_ID"),
        content_id='769eb42a-710c-4faa-98cb-78d21713b8ee', #1
    )
    response= client.post(
            f"/orders/checkout",
            headers=auth_headers,
            json=json.loads(order_item.model_dump_json()),
            params={'success_url':'https://www.ryu-nakamura/1.html?purchased=complete','cancel_url':'https://www.ryu-nakamura/1.html'}
        )
    print(response.json())
    assert response.status_code==201
    order_response=OrderResponse(**response.json())
    assert order_response.url.startswith("https://checkout.stripe.com/c/pay/")

def test_webhook(auth_headers):
    order_id='fff31094-2c50-450f-b689-00b7d5868b38'
    result = subprocess.run([
        'C:\\src\\ryu-nakamura-api\\.venv\\stripe.exe', 
        'trigger',
        'checkout.session.completed',
        '--add', 
        f'checkout_session:metadata[order_id]={order_id}'  
    ], capture_output=True, text=True)
    # print(json.loads(result.stdout))
    print("15秒間待機")
    time.sleep(15)
    response= client.get(
            f"/orders/{order_id}",
            headers=auth_headers,
        )
    order_response=Order(**response.json())
    assert response.status_code==200
    assert order_response.checkout_status=="complete"
    
    
def test_get_purchased_orders(auth_headers):
    user_id=os.getenv("AZURE_LOCAL_CLIENT_APP_ID"),
    response= client.get(
            f"/orders",
            headers=auth_headers,
            params={'user_id':user_id,'sas':str(True)}
        )
    assert response.status_code==200
    order_response=[Order(**order) for order in response.json()]
    assert len(order_response)==1
    assert str(order_response[0].content.id)=="769eb42a-710c-4faa-98cb-78d21713b8ee"
    sas_req_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    sas_response=requests.get(order_response[0].content.full_speech_url, headers=sas_req_headers)
    assert sas_response.status_code==200
    
def test_post_process(test_post):
    pass
    
