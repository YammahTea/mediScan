from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jwt import PyJWTError
from datetime import datetime, timezone
import jwt

# Modules
from Back.db.database import get_db
from Back.db.models import User
from Back.services.auth import is_token_blacklisted, SECRET_KEY, ALGORITHM
from Back.services.redis_client import get_redis

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
MAX_REQUESTS = 10

async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db),
        redis = Depends(get_redis)
):
  credentials_exception = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
  )
  
  # 1- Check if token is blacklisted
  if await is_token_blacklisted(token, redis):
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



async def check_rate_limit(
        user: User,
        db: AsyncSession
):
  """
  Checks if the user has reached their maximum request limits for the day
  True -> can upload
  False -> can NOT upload
  
  1- Checks for a new day
  2- Check is not unlimited and reached max count
  3- if none, increase request counter and update last request
  """
  now = datetime.now(timezone.utc)

  if user.last_request is None or user.last_request.date() < now.date():
    user.request_count = 0
    
  if not user.is_unlimited and user.request_count >= MAX_REQUESTS:
    raise HTTPException(
      status_code=status.HTTP_429_TOO_MANY_REQUESTS,
      detail="Daily limit reached, Please come back tomorrow."
    )
  
  user.request_count += 1
  user.last_request = now
  
  await db.commit()
  await db.refresh(user)
  
  return True