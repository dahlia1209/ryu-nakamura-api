from fastapi import APIRouter, HTTPException, Query, Path, Body, Depends, Header, Request, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Literal, Dict, Any
import uuid
import os
from jwt.algorithms import RSAAlgorithm
import jwt
import requests
from typing import TypedDict, List, cast
from pydantic import ValidationError
from functools import lru_cache

class JWKKey(TypedDict):
    kty: str
    use: str
    kid: str
    x5t: str
    n: str
    e: str
    x5c: List[str]
    cloud_instance_name: str
    issuer: str

class JWTPayload(TypedDict, total=False):
    sub: str
    name: str
    oid: str
    scp: str  
    emails: List[str]  
    exp: int  
    nbf: int  
    iat: int  
    iss: str 
    aud: str 

class AuthManager:
    _instance: Optional['AuthManager'] = None
    jwt_keys: List[JWKKey] = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.jwt_keys = cls._instance._get_jwt_keys()
        return cls._instance
    
    def _get_jwt_keys(self) -> List[JWKKey]:
        """JWTの検証キーをAzure ADから取得する"""
        try:
            tenant_id = os.getenv('AZURE_B2C_TENANT_ID')
            if not tenant_id:
                raise ValueError("AZURE_B2C_TENANT_ID環境変数が設定されていません")
                
            jwks_uri = f"https://ryunakamura.b2clogin.com/{os.getenv('AZURE_B2C_TENANT_ID')}/discovery/v2.0/keys?p=B2C_1_signupsignin1"
            keys_response = requests.get(jwks_uri, timeout=10)
            keys_response.raise_for_status()
            
            return cast(List[JWKKey], keys_response.json()["keys"])
        except requests.exceptions.RequestException as e:
            raise ValueError(f"JWT検証キーの取得に失敗しました: {e}")
    
    def reload_jwt_keys(self) -> None:
        self.jwt_keys = self._get_jwt_keys()
    
    def get_signing_key(self, jwt_token: str) -> Any:
        header = jwt.get_unverified_header(jwt_token)
        signing_key = None
        
        for key in self.jwt_keys:
            if key.get("kid") == header.get("kid"):
                jwk = {
                    "kty": key.get("kty"),
                    "kid": key.get("kid"),
                    "use": key.get("use"),
                    "n": key.get("n"),
                    "e": key.get("e")
                }
                signing_key = RSAAlgorithm.from_jwk(jwk)
                return signing_key
            
        if not signing_key:
            raise ValueError(f"署名キーが見つかりません。kid: {header.get('kid')}")
        
        return signing_key
    
    def verify_jwt_token(self, jwt_token: str) -> JWTPayload:
        def try_decode(keys_reloaded: bool = False) -> JWTPayload:
            try:
                signing_key = self.get_signing_key(jwt_token)
                
                # B2Cトークンの場合、audienceは通常リソースIDになります
                audience = os.getenv('AZURE_API_APP_ID')
                issuer = f"https://ryunakamura.b2clogin.com/{os.getenv('AZURE_B2C_TENANT_ID')}/v2.0/"
                
                options = {
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_iat": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                }
                
                decoded = jwt.decode(
                    jwt_token,
                    signing_key,
                    audience=audience,
                    issuer=issuer,
                    algorithms=["RS256"],
                    options=options
                )
                
                return cast(JWTPayload, decoded)
                
            except jwt.exceptions.InvalidTokenError as e:
                print(f"Token validation error: {str(e)}")
                if not keys_reloaded:
                    self.reload_jwt_keys()
                    return try_decode(keys_reloaded=True)
                else:
                    raise HTTPException(
                        status_code=401,
                        detail=f"不正なIDトークンです: {str(e)}",
                        headers={"WWW-Authenticate": "Bearer"}
                    )
        
        return try_decode()
    
    
    
# セキュリティスキーマ
security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> JWTPayload:
    """
    トークンを検証して現在のユーザー情報を取得
    """
    try:
        auth_manager = AuthManager()
        token_data = auth_manager.verify_jwt_token(credentials.credentials)
        return token_data
    except ValueError as e:
        raise HTTPException(
            status_code=401,
            detail=f"認証エラー: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
Scope= Literal[
    'users.read',
    'users.list',
    'users.write',
    'contents.read',
    'contents.list',
    'contents.write',
    'orders.read',
    'orders.list',
    'orders.write'
]

def requires_scope(required_scope: Scope):
    """
    特定のスコープが必要なエンドポイント用の依存関数
    """
    def scope_validator(token_data: JWTPayload = Depends(get_current_user)):
        scopes = token_data.get("scp", "").split()
        if required_scope not in scopes:
            raise HTTPException(
                status_code=403,
                detail=f"アクセス権限がありません。必要なスコープ: {required_scope}"
            )
        return token_data
    return scope_validator

def is_token_sub_matching(
    token: JWTPayload,
    id: uuid.UUID,
):
    return str(id) == token.get("sub")