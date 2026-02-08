import uuid
from sqlalchemy import Uuid, String, Boolean, DateTime, ForeignKey, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
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
  
  # Track number of requests to limit user
  request_count: Mapped[int] = mapped_column(Integer, unique=False, default=0, nullable=False)
  
  # To check the cooldown of the user
  last_request: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
  
  # uncaps the limit
  is_unlimited: Mapped[bool] = mapped_column(Boolean, unique=False, default=False, nullable=True)
  
  
  
class RefreshToken(Base):
  __tablename__ = "refresh_token"
  
  # token id
  id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
  
  hashed_token: Mapped[str] = mapped_column(String, index=True, unique=True)
  expires_at: Mapped[datetime] = mapped_column(DateTime, default= lambda : datetime.now(timezone.utc).replace(tzinfo=None))
  
  # to ban tokens
  revoked: Mapped[bool] = mapped_column(Boolean, unique=False, default=False)
  
  # user id associated with the token
  user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
  
  user: Mapped["User"] = relationship()