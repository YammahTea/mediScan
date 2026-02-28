from fastapi import FastAPI, APIRouter, Header, status, HTTPException, Depends

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from dotenv import load_dotenv
import os

# Modules
from Back.db.database import get_db

router = APIRouter(
  tags=["DevOps"]
)

load_dotenv()

# bot bouncer
@router.get("/keep-alive")
async def keep_alive(
        x_keep_alive_token: str = Header(None),
        db: AsyncSession = Depends(get_db)
):
  
  expected_token = os.getenv("KEEP_ALIVE_TOKEN")
  
  # checks if it is a random bot
  if not expected_token or x_keep_alive_token != expected_token:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                        detail="Forbidden")
  
  # if it isn't, it pokes the db to keep a connection opened
  
  try:
    await db.execute(text("SELECT 1"))
    return {"status": "success", "message": "Supabase is awake"}
  
  except Exception as e:
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database ping failed")