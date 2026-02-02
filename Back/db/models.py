import uuid
from sqlalchemy import Uuid, String, Boolean, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime, timezone


class Base(DeclarativeBase):
  pass

class User(Base):

  __tablename__ = 'users'

  # User ID
  id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
  
  # Username
  username: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
  
  # User email
  email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
  
  # For future use
  is_verified: Mapped[bool] = mapped_column(Boolean, unique= False, default=False)
  
  # User password
  hashed_password: Mapped[str] = mapped_column(String, nullable=False)
  
  # Used to activate/deactivate accounts
  is_active: Mapped[bool] = mapped_column(Boolean, unique=False, default=True)
  
  
class BlacklistedToken(Base):
  __tablename__ = 'token_blacklist'
  
  id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
  
  token: Mapped[str] = mapped_column(String, index=True, unique=True)
  
  expires_at: Mapped[datetime] = mapped_column(DateTime, default= lambda : datetime.now(timezone.utc).replace(tzinfo=None))