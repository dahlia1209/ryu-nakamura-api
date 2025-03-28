from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class CheckoutItem(BaseModel):
    name: str  # 商品名
    price: int  # 単価（円）
    quantity: int  # 数量
    description: Optional[str] = None  # 商品説明
    images: Optional[List[str]] = None  # 商品画像URL配列

class CheckoutSession(BaseModel):
    items: List[CheckoutItem]  # 商品リスト
    success_url: str  # 支払い成功時のリダイレクトURL
    cancel_url: str  # キャンセル時のリダイレクトURL
    order_id: Optional[str] = None  # 注文ID
    customer_id: Optional[str] = None  # 顧客ID
    customer_email: Optional[str] = None  # 顧客メールアドレス
    locale: Optional[str] = None  # 言語設定（デフォルト: ja）
    collect_shipping_address: bool = False  # 配送先住所を収集するか
    metadata: Optional[Dict[str, Any]] = None  # 追加メタデータ

class CheckoutResponse(BaseModel):
    session_id: str  # Stripeセッションフロントエンドで使用
    url: str  # Checkoutページの直接URL