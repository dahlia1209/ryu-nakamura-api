from fastapi import APIRouter, HTTPException, Path, Body
from pydantic import BaseModel

from models.content import Content
from models.query import QueryFilter
from repository import content as content_repo
from managers.appstore_manager import AppStoreManager, product_id_for_title_no
from utils.app_free import app_free_title_nos

router = APIRouter()


class UnlockRequest(BaseModel):
    signed_transaction: str


def _get_content_or_404(title_no: int) -> Content:
    qf = QueryFilter()
    qf.add_filter("title_no eq @title_no", {"title_no": title_no})
    contents = content_repo.query_contents(qf)
    if not contents:
        raise HTTPException(status_code=404, detail=f"title_no={title_no}のコンテンツが見つかりません")
    return contents[0]


@router.get("/app/contents/{title_no}", response_model=Content, tags=["app"])
async def get_app_free_content(
    title_no: int = Path(..., description="無料公開されているか確認する記事のtitle_no"),
):
    """RyuNakamuraApp(iOS)向けに、アプリ内無料公開指定された記事のみ本文を返す（購入不要）"""
    if title_no not in app_free_title_nos():
        raise HTTPException(
            status_code=403,
            detail="この記事はアプリ内では無料公開されていません。購入してください。",
        )
    return _get_content_or_404(title_no)


@router.post("/app/contents/{title_no}/unlock", response_model=Content, tags=["app"])
async def unlock_content(
    title_no: int = Path(..., description="解除する記事のtitle_no"),
    body: UnlockRequest = Body(...),
):
    """RyuNakamuraApp(iOS)からのStoreKit購入情報を検証し、購入済み記事の本文を返す"""
    try:
        transaction = AppStoreManager().verify_transaction(body.signed_transaction)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if transaction.revocationDate is not None:
        raise HTTPException(status_code=403, detail="この購入は返金・取り消しされています")

    expected_product_id = product_id_for_title_no(title_no)
    if transaction.productId != expected_product_id:
        raise HTTPException(
            status_code=403,
            detail=f"購入商品(product_id={transaction.productId})はtitle_no={title_no}に対応していません",
        )

    return _get_content_or_404(title_no)
