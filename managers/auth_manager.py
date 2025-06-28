from fastapi import (
    APIRouter,
    HTTPException,
    Query,
    Path,
    Body,
    Depends,
    Header,
    Request,
    Security,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional, Literal, Dict, Any
import uuid
import os
from jwt.algorithms import RSAAlgorithm
import jwt
import requests
from typing import TypedDict, List, cast
from pydantic import ValidationError
import logging

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
    _instance: Optional["AuthManager"] = None
    jwt_keys: List[JWKKey] = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.jwt_keys = cls._instance._get_jwt_keys()
        return cls._instance

    def _get_jwt_keys(self) -> List[JWKKey]:
        """JWTの検証キーをMicrosoft Entra External IDから取得する"""
        try:
            # 環境変数からテナント情報を取得
            tenant_id = os.getenv("AZURE_B2C_TENANT_ID")  # 実際のテナントID

            if not tenant_id:
                raise ValueError("AZURE_B2C_TENANT_ID環境変数が設定されていません")

            # OpenID設定ドキュメントのURLを構築
            openid_config_url = f"https://{tenant_id}.ciamlogin.com/{tenant_id}/v2.0/.well-known/openid-configuration"

            # OpenID設定を取得
            config_response = requests.get(openid_config_url, timeout=10)
            config_response.raise_for_status()
            config_data = config_response.json()

            # JWKS URIを取得
            jwks_uri = config_data.get("jwks_uri")
            if not jwks_uri:
                raise ValueError("OpenID設定にjwks_uriが見つかりません")

            # JWKSを取得
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
                    "e": key.get("e"),
                }
                signing_key = RSAAlgorithm.from_jwk(jwk)
                return signing_key
        if not signing_key:
            print(f"Available keys: {[key.get('kid') for key in self.jwt_keys]}")
            print(f"Looking for kid: {header.get('kid')}")
            raise ValueError(f"署名キーが見つかりません。kid: {header.get('kid')}")

        return signing_key

    def verify_jwt_token(self, jwt_token: str) -> JWTPayload:
        def try_decode(keys_reloaded: bool = False) -> JWTPayload:
            try:
                signing_key = self.get_signing_key(jwt_token)

                # External IDの設定
                audience = os.getenv("AZURE_API_APP_ID")
                tenant_id = os.getenv("AZURE_B2C_TENANT_ID")

                if not tenant_id:
                    raise ValueError("AZURE_B2C_TENANT_ID環境変数が設定されていません")

                # External IDの正しいissuer形式
                issuer = f"https://{tenant_id}.ciamlogin.com/{tenant_id}/v2.0"

                options = {
                    "verify_signature": True,
                    "verify_aud": True,
                    "verify_iat": True,
                    "verify_exp": True,
                    "verify_nbf": True,
                    "verify_iss": True,
                }

                decoded = jwt.decode(
                    jwt_token,
                    signing_key,
                    audience=audience,
                    issuer=issuer,
                    algorithms=["RS256"],
                    options=options,
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
                        headers={"WWW-Authenticate": "Bearer"},
                    )

        return try_decode()


# セキュリティスキーマ
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Security(security),
) -> JWTPayload:
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
            headers={"WWW-Authenticate": "Bearer"},
        )


Scope = Literal[
    "users.read",
    "users.list",
    "users.write",
    "contents.read",
    "contents.list",
    "contents.write",
    "orders.read",
    "orders.list",
    "orders.write",
]


def requires_scope(required_scope: Scope):
    """
    特定のスコープが必要なエンドポイント用の依存関数
    """

    def scope_validator(token_data: JWTPayload = Depends(get_current_user)):
        if token_data.get("azp", "") == os.getenv(
            "AZURE_LOCAL_CLIENT_APP_ID", "e0282457-8666-4877-84ea-b516120d123f"
        ):
            return token_data
        scopes = token_data.get("scp", "").split()
        if required_scope not in scopes:
            raise HTTPException(
                status_code=403,
                detail=f"アクセス権限がありません。必要なスコープ: {required_scope}",
            )
        return token_data

    return scope_validator


def is_token_id_matching(
    token: JWTPayload,
    id: uuid.UUID,
):
    return str(id) in [
        token.get("oid"),
        token.get("sub"),
        token.get("azp"),
    ] or token.get("azp") == os.getenv(
        "AZURE_LOCAL_CLIENT_APP_ID", "e0282457-8666-4877-84ea-b516120d123f"
    )
