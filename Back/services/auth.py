from passlib.context import CryptContext
import jwt

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import os, uuid, secrets
import hashlib, base64

from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

# Modules
from Back.db.models import BlacklistedToken, RefreshToken

load_dotenv()

# hash config
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# secret config
SECRET_KEY = os.getenv("AUTH_SECRET_KEY")
ALGORITHM = os.getenv("AUTH_ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("AUTH_ACCESS_TOKEN_EXPIRE_MINUTES"))
AUTH_REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("AUTH_REFRESH_TOKEN_EXPIRE_DAYS"))


""" PASSWORD RELATED FUCNTION """

def hash_password(password: str) -> str:
  return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
  return pwd_context.verify(plain_password, hashed_password)



""" TOKEN RELATED FUNCTIONS """

def hash_token(token: str):
  digest = hashlib.sha256(token.encode("utf-8")).digest()
  return base64.urlsafe_b64encode(digest).decode("utf-8").rstrip("=")

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


async def create_refresh_token(user_id: uuid.UUID, db: AsyncSession):
  token = secrets.token_urlsafe(48) # random string
  expire = datetime.now(timezone.utc) + timedelta(days=AUTH_REFRESH_TOKEN_EXPIRE_DAYS)
  
  db_refresh = RefreshToken(
    user_id=user_id,
    hashed_token=hash_token(token),
    expires_at=expire,
    revoked=False
  )
  
  db.add(db_refresh)
  await db.commit()
  
  return token # plain value because it will sent in cookie only


async def get_refresh_token(hashed_token: str, db: AsyncSession):
  """
  Find a token in the db
  """
  
  query = select(RefreshToken).where(RefreshToken.hashed_token == hashed_token)
  result = await db.execute(query)
  
  token_record = result.scalars().first()
  
  return token_record

async def revoke_refresh_token(token_record: RefreshToken, db: AsyncSession):
  """
  Revoke a token
  """
  token_record.revoked = True
  await db.commit()
  