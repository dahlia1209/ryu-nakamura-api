from fastapi import APIRouter, HTTPException, Request, Response,Body,Query
import stripe
import os
from models.order import OrderItem,Order
from models.query import QueryFilter
from typing import Dict, Any
from repository import user as user_repo
from repository import content as content_repo
from repository import order as order_repo
from managers.email_manager import EmailManager
from models.email import EmailResponse,EmailMessage
import datetime
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
    
    retsult=None
    if event.type== 'checkout.session.expired' or event.type== 'checkout.session.completed':
        status=event.data.object.get("status")
        order_id = event.data.object.get('metadata', {}).get('order_id')
        order_item=order_repo.update_order_status(order_id,status)
        retsult=order_item
        
        if event.type=='checkout.session.completed':
            content=content_repo.get_content(str(order_item.content_id))
            user=user_repo.get_user(str(order_item.user_id))
            dt=datetime.datetime.fromtimestamp(event.data.object.get("created"))
            email_manager=EmailManager()

            purchased_order_reply=EmailMessage.create_purchased_order_reply(
                to_address=user.email,
                order_id=order_id,
                content_html=content.content_html,
                content_title=content.title,
                name=user.email,
                order_date=dt.strftime('%Y年%m月%d日 %H時%M分'),
                payment_method="クレジットカード",
                price=str(int(content.price)),
            )
            poller = email_manager.client.begin_send(purchased_order_reply.model_dump())
            mail_result = poller.result()

    
    return retsult

@router.post("/webhooks/singinsignup",tags=["webhooks"])
async def webhook(request: Request):
    payload = await request.body()
    
    print(payload)
    return payload