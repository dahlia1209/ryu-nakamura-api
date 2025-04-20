import fastapi
from . import connection,email,payment,checkout ,content,user
from fastapi.middleware.cors import CORSMiddleware

app = fastapi.FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","https://www.ryu-nakamura.com"],  # フロントエンドのオリジン
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS","PUT"],  # 許可するHTTPメソッド
    allow_headers=["*"],  # すべてのヘッダーを許可
)
    
app.include_router(connection.router)
app.include_router(email.router)
app.include_router(payment.router)
app.include_router(checkout.router)
app.include_router(content.router)
app.include_router(user.router)