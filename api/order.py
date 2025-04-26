from fastapi import APIRouter, HTTPException, Request, Response,Body,Query,Path
import stripe
import os
from models.order import OrderItem,Order,OrderStatus,OrderResponse
from models.query import QueryFilter
from typing import Dict, Any,List,Optional
from repository import user as user_repo
from repository import content as content_repo
from repository import order as order_repo
import uuid

router = APIRouter()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
endpoint_secret = os.getenv("STRIPE_WEBHOOK_SECRET")


@router.get("/orders", response_model=List[Order], tags=["orders"])
async def list_orders(
    limit: int = Query(50, description="Maximum number of users to return"),
    user_id:Optional[str]= Query(None,description="Filter by user_id"),
    content_id:Optional[str]= Query(None,description="Filter by content_id"),
    status:Optional[OrderStatus]= Query(None,description="Filter by content_id"),
    # token_data = Depends(requires_scope("users.read"))
):
    """注文情報一覧を取得する"""
    if not user_id or not content_id:
        raise HTTPException(
            status_code=400,
            detail=(f"user_idとcontent_idを指定してください")
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
    ):
    try:
        user=user_repo.get_user(str(order_item.user_id))
        content=content_repo.get_content(str(order_item.content_id))
        order=Order(content=content,user=user,**order_item.model_dump())
        
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
        print("ValueError",e)
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


    
@router.get("/orders/{order_id}", response_model=Order, tags=["orders"])
async def get_order(
    order_id: uuid.UUID = Path(..., description="Order ID to retrieve"),
    # token_data = Depends(requires_scope("users.read"))
):
    """指定されたIDの注文情報を取得する"""
    try:
        order = order_repo.get_order(str(order_id))
        return order
    
    except ValueError as e:
        raise HTTPException(
            status_code=404,
            detail=f"指定されたID {order_id} の注文情報が見つかりません"
        )

@router.put("/orders/{order_id}/status", response_model=OrderItem, tags=["orders"])
async def update_order_status(
    order_id: uuid.UUID = Path(..., description="User ID to update"),
    status: OrderStatus = Body(..., description="Status to update"),
    # token_data = Depends(requires_scope("users.write"))
):
    """指定された注文IDのステータスを更新する"""
    try:
        result=order_repo.update_order_status(str(order_id),status)
    except ValueError as e:
        print("error",e)
        raise HTTPException(
            status_code=404,
            detail=f"指定されたID {order_id} の注文情報が見つかりません"
        )
    
    return result