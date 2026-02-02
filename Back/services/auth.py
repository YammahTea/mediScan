from passlib.context import CryptContext
import jwt

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import os
from dotenv import load_dotenv

# Modules
from Back.db.models import BlacklistedToken

load_dotenv()

# hash config
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# secret config
SECRET_KEY = os.getenv("AUTH_SECRET_KEY")
ALGORITHM = os.getenv("AUTH_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES"))

def hash_password(password: str) -> str:
  return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
  return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict):
  to_encode = data.copy()
  
  # expire time
  expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
  to_encode.update({"exp": expire})
  
  encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
  return encoded_jwt


async def is_token_blacklisted(token: str, db: AsyncSession) -> bool:
  """
  Returns true if the token is found in the sql blacklist
  """
  query = select(BlacklistedToken).where(BlacklistedToken.token == token)
  result = await db.execute(query)
  
  return result.scalars().first() is not None

async def add_token_to_blacklist(token: str, expiration: float, db: AsyncSession):
  """
  Adds the token to the sql blacklist with its expiration time
  """
  
  # convert timestamp to a datetime obj
  # i use utc in the model's logic
  expires_at_dt = datetime.fromtimestamp(expiration, timezone.utc).replace(tzinfo=None)
  
  new_entry = BlacklistedToken(token=token, expires_at=expires_at_dt)
  
  db.add(new_entry)
  await db.commit()