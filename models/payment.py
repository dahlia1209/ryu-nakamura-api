# models/payment.py
from pydantic import BaseModel
from typing import Optional, Dict, Any

class PaymentIntent(BaseModel):
    amount: int  # 金額（日本円の場合は整数）
    currency: str = "jpy"  # 通貨（デフォルトは日本円）
    product_id: Optional[str] = None  # 商品ID
    description: Optional[str] = None  # 支払いの説明
    customer_email: Optional[str] = None  # 顧客のメールアドレス
    metadata: Optional[Dict[str, Any]] = None  # メタデータ

class PaymentResponse(BaseModel):
    payment_intent_id: str  # Stripe Payment Intent ID
    client_secret: str  # フロントエンドで支払いを完了するために必要
    status: str  # 支払いステータス

class PaymentConfirmation(BaseModel):
    order_id: str
    payment_id: str
    amount: int
    status: str
    customer_email: Optional[str] = None
    created_at: str