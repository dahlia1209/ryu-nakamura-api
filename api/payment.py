# api/payment.py
from fastapi import APIRouter, HTTPException, Request
from models.payment import PaymentIntent, PaymentResponse
import stripe
import os
import json

router = APIRouter()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@router.post("/create-payment-intent", response_model=PaymentResponse)
async def create_payment_intent(payment: PaymentIntent):
    try:
        # Stripeの支払いインテントを作成
        intent = stripe.PaymentIntent.create(
            amount=payment.amount,
            currency=payment.currency,
            metadata={"product_id": payment.product_id},
            description=payment.description,
        )
        
        return PaymentResponse(
            payment_intent_id=intent.id,
            client_secret=intent.client_secret,
            status=intent.status
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
    
    try:
        # Webhook署名を検証
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
        
        # イベントタイプに基づいて処理
        if event.type == "payment_intent.succeeded":
            payment_intent = event.data.object
            # 支払い成功時の処理
            # 例: 注文情報の更新やメール通知
            print(f"Payment succeeded: {payment_intent.id}")
            
        elif event.type == "payment_intent.payment_failed":
            payment_intent = event.data.object
            # 支払い失敗時の処理
            print(f"Payment failed: {payment_intent.id}")
        
        return {"status": "success"}
    except stripe.error.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payment-status/{payment_id}")
async def get_payment_status(payment_id: str):
    try:
        payment_intent = stripe.PaymentIntent.retrieve(payment_id)
        return {
            "id": payment_intent.id,
            "status": payment_intent.status,
            "amount": payment_intent.amount,
            "currency": payment_intent.currency
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))