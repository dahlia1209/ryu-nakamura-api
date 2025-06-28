from fastapi import APIRouter, HTTPException, Query, Path, Body, Depends,Header,Request
import stripe
import os
from models.order import OrderItem,Order,OrderStatus,OrderResponse
from models.query import QueryFilter
from typing import Dict, Any,List,Optional
from repository import user as user_repo
from repository import content as content_repo
from repository import order as order_repo
from managers.auth_manager import  JWTPayload,get_current_user,requires_scope,is_token_id_matching
import uuid

router = APIRouter()



@router.get("/orders", response_model=List[Order], tags=["orders"])
async def list_orders(
    limit: int = Query(50, description="Maximum number of users to return"),
    user_id:str= Query(...,description="Filter by user_id"),
    content_id:Optional[str]= Query(None,description="Filter by content_id"),
    status:Optional[OrderStatus]= Query(None,description="Filter by content_id"),
    token_data: JWTPayload  = Depends(requires_scope("orders.read"))
):
    """注文情報一覧を取得する"""
    if not is_token_id_matching(token_data,user_id):
            raise HTTPException(
                status_code=403,
                detail=f"user_id {user_id} とトークンのidが一致しません"
            )
    qf=QueryFilter()
    qf.add_filter(f"user_id eq @user_id",{"user_id":user_id})
    qf.add_filter(f"content_id eq @content_id",{"content_id":content_id})
    qf.add_filter(f"checkout_status eq @status",{"status":status})
    orders = order_repo.query_orders(qf,limit)
    return orders

@router.post("/orders/checkout", response_model=OrderResponse, status_code=201, tags=["orders"])
async def make_checkout_session(
        order_item: OrderItem=Body(...,description="Checkout to create"),
        success_url:str= Query(os.getenv("FRONT_URL"), description="The URL to which Stripe should send customers when payment or setup is complete. "),
        cancel_url:str= Query(os.getenv("FRONT_URL"), description="If set, Checkout displays a back button and customers will be directed to this URL if they decide to cancel payment and return to your website. "),
        token_data = Depends(requires_scope("orders.write"))
    ):
    try:
        user=user_repo.get_user(str(order_item.user_id))
        content=content_repo.get_content(str(order_item.content_id))
        order=Order(content=content,user=user,**order_item.model_dump())
        
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[order.to_line_item()],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            locale='ja',
            customer_email=order.user.email,
            metadata={
                'order_id': order.id,
                'user_id': order.user.id,
                'content_id': order.content.id,
            } ,
            payment_method_options={"card": {"request_three_d_secure": "any"}},
        )
        
        order.checkout_id=session.id
        order_repo.create_order(order)
        
        return OrderResponse(
            session_id=session.id,
            url=session.url
        )
    except stripe.StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    
@router.get("/orders/{order_id}", response_model=Order, tags=["orders"])
async def get_order(
    order_id: uuid.UUID = Path(..., description="Order ID to retrieve"),
    token_data: JWTPayload  = Depends(requires_scope("orders.read"))
):
    """指定されたIDの注文情報を取得する"""
    try:
        order = order_repo.get_order(str(order_id))
        
        if not is_token_id_matching(token_data,order.user.id):
            raise HTTPException(
                status_code=403,
                detail=f"指定されたID {order_id} の注文情報の取得権限がありません"
            )
        return order
    
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=f"指定されたID {order_id} の注文情報が見つかりません"
        )

@router.delete("/orders/{order_id}", status_code=204,tags=["orders"])
async def delete_order(
    order_id: uuid.UUID = Path(..., description="Order ID to delete"),
    token_data: JWTPayload  = Depends(requires_scope("orders.admin"))
):
    """指定されたIDの注文情報を削除する"""
    try:
        order = order_repo.get_order(str(order_id))
        order_repo.delete_order(str(order_id))
        return True
    
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=f"指定されたID {order_id} の注文情報が見つかりません"
        )

