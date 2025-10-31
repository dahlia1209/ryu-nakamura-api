import fastapi
from . import connection, contact,content,user,order,webhooks,blockchain
from fastapi.middleware.cors import CORSMiddleware

app = fastapi.FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173","http://localhost:4173","https://www.ryu-nakamura.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS","PUT"],  
    allow_headers=["*"],  
)
    
app.include_router(connection.router)
app.include_router(contact.router)
app.include_router(content.router)
app.include_router(user.router)
app.include_router(order.router)
app.include_router(webhooks.router)
app.include_router(blockchain.router)