from fastapi import APIRouter
from repository.content import client,table

router = APIRouter()

@router.get("/contents")
async def get_contents():
    
    return {"response": "200", "message": f"connection succeeded. ","content":table.table_name}
