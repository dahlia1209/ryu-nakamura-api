# api/checkout.py
from fastapi import APIRouter, HTTPException, Request, Response
import stripe
import os
from models.checkout import CheckoutSession, CheckoutResponse
from typing import Dict, Any

router = APIRouter()
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

@router.post("/create-checkout", response_model=CheckoutResponse)
async def create_checkout_session(checkout: CheckoutSession):
    try:
        # 商品ラインアイテムを構築
        line_items = []
        for item in checkout.items:
            line_items.append({
                'price_data': {
                    'currency': 'jpy',
                    'product_data': {
                        'name': item.name,
                        'description': item.description,
                        'images': item.images if item.images else [],
                    },
                    'unit_amount': item.price,
                },
                'quantity': item.quantity,
            })
        
        # Checkoutセッションを作成 - 正しいメソッド名: Session (大文字・単数形)
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=line_items,
            mode='payment',
            success_url=checkout.success_url,
            cancel_url=checkout.cancel_url,
            locale=checkout.locale or 'ja',
            customer_email=checkout.customer_email,
            metadata={
                'order_id': checkout.order_id,
                'customer_id': checkout.customer_id
            } if checkout.order_id else {},
            shipping_address_collection=(
                {
                    'allowed_countries': ['JP'],
                } if checkout.collect_shipping_address else None
            ),
        )
        
        return CheckoutResponse(
            session_id=session.id,
            url=session.url
        )
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
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
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        # セッションのメタデータから注文情報を取得
        order_id = session.get('metadata', {}).get('order_id')
        customer_id = session.get('metadata', {}).get('customer_id')
        
        # 注文処理を実行（データベース更新など）
        await handle_checkout_completion(session)
        
    elif event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        print(f"PaymentIntent {payment_intent['id']} succeeded")
        
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        error_message = payment_intent.get('last_payment_error', {}).get('message')
        print(f"Payment failed: {error_message}")
    
    return {"status": "success"}

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
    
    # 例: 確認メール送信処理
    customer_email = session.get('customer_email')
    if customer_email:
        # メール送信ロジック（既存のEmailクラスを活用可能）
        pass
    
    return True

@router.get("/session-status/{session_id}")
async def get_session_status(session_id: str):
    try:
        # ここも Session (大文字・単数形) に修正
        session = stripe.checkout.Session.retrieve(session_id)
        return {
            "id": session.id,
            "status": session.status,
            "payment_status": session.payment_status,
            "customer_email": session.customer_email,
            "amount_total": session.amount_total
        }
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"Session not found: {str(e)}")