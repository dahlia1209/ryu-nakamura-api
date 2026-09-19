import os
from typing import Optional

from appstoreserverlibrary.signed_data_verifier import SignedDataVerifier, VerificationException
from appstoreserverlibrary.models.Environment import Environment
from appstoreserverlibrary.models.JWSTransactionDecodedPayload import JWSTransactionDecodedPayload

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CERT_DIR = os.path.join(BASE_DIR, "appstore_certs")

PRODUCT_ID_PREFIX = "ryu-nakamura.RyuNakamuraApp.content."


def product_id_for_title_no(title_no: int) -> str:
    return f"{PRODUCT_ID_PREFIX}{title_no}"


def title_no_from_product_id(product_id: str) -> Optional[int]:
    if not product_id.startswith(PRODUCT_ID_PREFIX):
        return None
    suffix = product_id[len(PRODUCT_ID_PREFIX):]
    return int(suffix) if suffix.isdigit() else None


class AppStoreManager:
    _instance: Optional["AppStoreManager"] = None
    verifier: SignedDataVerifier

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.verifier = cls._instance._build_verifier()
        return cls._instance

    def _load_root_certificates(self) -> list:
        certificates = []
        for filename in sorted(os.listdir(CERT_DIR)):
            if filename.endswith(".cer"):
                with open(os.path.join(CERT_DIR, filename), "rb") as f:
                    certificates.append(f.read())
        if not certificates:
            raise ValueError(f"Apple証明書が見つかりません: {CERT_DIR}")
        return certificates

    def _build_verifier(self) -> SignedDataVerifier:
        bundle_id = os.getenv("APPSTORE_BUNDLE_ID")
        if not bundle_id:
            raise ValueError("APPSTORE_BUNDLE_ID環境変数が設定されていません")

        environment = Environment(os.getenv("APPSTORE_ENVIRONMENT", "Sandbox"))

        app_apple_id_raw = os.getenv("APPSTORE_APP_APPLE_ID")
        app_apple_id = int(app_apple_id_raw) if app_apple_id_raw else None

        return SignedDataVerifier(
            root_certificates=self._load_root_certificates(),
            enable_online_checks=environment == Environment.PRODUCTION,
            environment=environment,
            bundle_id=bundle_id,
            app_apple_id=app_apple_id,
        )

    def verify_transaction(self, signed_transaction: str) -> JWSTransactionDecodedPayload:
        try:
            return self.verifier.verify_and_decode_signed_transaction(signed_transaction)
        except VerificationException as e:
            raise ValueError(f"購入情報の検証に失敗しました: {e.status.name}")
