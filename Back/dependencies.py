from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jwt import PyJWTError
import jwt

# Modules
from Back.db.database import get_db
from Back.db.models import User
from Back.services.auth import is_token_blacklisted, SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db)
):
  credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
  )
  
  # 1- Check if token is blacklisted
  if await is_token_blacklisted(token, db):
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is invalid (Logged out)")
  
  try:
    # 2- Decode token
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    username: str = payload.get("sub")
    
    if username is None:
      raise credentials_exception
    
  except PyJWTError:
    raise credentials_exception
  
  # 3- Get User from DB
  result = await db.execute(select(User).where(User.username == username))
  user = result.scalars().first()
  
  if user is None:
    raise credentials_exception
  
  # 4- check if the user is active
  if not user.is_active:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user")
  
  return user