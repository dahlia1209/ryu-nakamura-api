import fastapi
from . import connection,email
from fastapi.middleware.cors import CORSMiddleware

app = fastapi.FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","https://www.ryu-nakamura.com"],  # フロントエンドのオリジン
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # 許可するHTTPメソッド
    allow_headers=["*"],  # すべてのヘッダーを許可
)
    
app.include_router(connection.router)
app.include_router(email.router)