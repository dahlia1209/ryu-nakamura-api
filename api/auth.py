# api/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from jose import jwt, JWTError  # jwt モジュールの代わりに jose を使用
from pydantic import BaseModel
from typing import List, Optional
import httpx
from models.auth import TokenData

# OAuth2スキームのセットアップ
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="https://ryunakamura.b2clogin.com/ryunakamura.onmicrosoft.com/b2c_1_signupsignin1/oauth2/v2.0/authorize",
    tokenUrl="https://ryunakamura.b2clogin.com/ryunakamura.onmicrosoft.com/b2c_1_signupsignin1/oauth2/v2.0/token"
)

# JWT検証設定
AZURE_B2C_TENANT_ID = "51fd4a1a-c226-4c7e-9c7f-db4ccd880bf9"
AUDIENCE = "c90f8e2a-8896-4a7c-ab5a-30f17c088e1f"  # トークンから取得
ISSUER = f"https://ryunakamura.b2clogin.com/{AZURE_B2C_TENANT_ID}/v2.0/"
JWKS_URI = f"https://ryunakamura.b2clogin.com/{AZURE_B2C_TENANT_ID}/discovery/v2.0/keys"

# JWKSからキーを取得する関数
async def get_jwks():
    async with httpx.AsyncClient() as client:
        response = await client.get(JWKS_URI)
        return response.json()

# トークンの取得と検証を行う関数
async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="認証情報が無効です",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # 本番環境ではJWKSを使用して署名を検証
        # jwks = await get_jwks()
        
        # 開発環境では簡易的にオプションを指定して検証
        payload = jwt.decode(
            token,
            options={"verify_signature": False},  # 本番環境では署名を必ず検証する必要があります
            audience=AUDIENCE,
            issuer=ISSUER
        )
        
        sub: str = payload.get("sub")
        if sub is None:
            raise credentials_exception
            
        # スコープの抽出
        scopes = []
        if "scp" in payload:
            scopes = payload["scp"].split()
        
        return TokenData(sub=sub, scopes=scopes)
        
    except JWTError:  # PyJWTError の代わりに JWTError を使用
        raise credentials_exception

# スコープチェック用の依存関係
def requires_scope(required_scope: str):
    # Azure B2Cで定義された完全なスコープURIを使用
    api_scope_prefix = "https://ryunakamura.onmicrosoft.com/ryu-nakamura-api/"
    full_scope = f"{api_scope_prefix}{required_scope}"
    
    def scope_checker(token_data: TokenData = Depends(get_current_user)):
        if full_scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"権限が不足しています。必要なスコープ: {required_scope}",
            )
        return token_data
    return scope_checker