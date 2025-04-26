from fastapi import APIRouter, HTTPException, Request, Response,Body,Query
import stripe
import os
from models.order import OrderItem,Order
from models.query import QueryFilter
from typing import Dict, Any
from repository import user as user_repo
from repository import content as content_repo
from repository import order as order_repo

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

@router.post("/webhooks",tags=["webhooks"])
async def webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get('stripe-signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        # Invalid payload
        raise HTTPException(status_code=400, detail=str(e))
    except stripe.SignatureVerificationError as e:
        # Invalid signature
        raise HTTPException(status_code=400, detail=str(e))
    
    # イベントタイプによって分岐
    retsult=None
    if event.type== 'checkout.session.expired' or event.type== 'checkout.session.completed':
        status=event.data.object.get("status")
        order_id = event.data.object.get('metadata', {}).get('order_id')
        order_item=order_repo.update_order_status(order_id,status)
        retsult=order_item
    
    return retsult

async def handle_checkout_completion(session):
    """
    チェックアウト完了時の処理
    - 注文をデータベースに保存
    - 在庫を減らす
    - 注文確認メールを送信
    - など
    """
    # TODO: 実際の実装
    print(f"Processing completed checkout: {session.id}")
    
    
    return True