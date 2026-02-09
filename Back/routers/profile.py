from fastapi import APIRouter, Depends, HTTPException, status
from datetime import timedelta, datetime, timezone, time

# Modules
from Back.dependencies import MAX_REQUESTS
from Back.db.models import User
from Back.dependencies import get_current_user

router = APIRouter(
  tags=["Profile"]
)

@router.get("/profile/me")
async def get_my_profile(
        user: User = Depends(get_current_user),
):
  
  # 1- Calculate reset time (next midnight UTC)
  now = datetime.now(timezone.utc)
  tomorrow = now.date() + timedelta(days=1)
  
  next_reset = datetime.combine(tomorrow, time.min).replace(tzinfo=timezone.utc)
  
  # 2- Check current usage
  # If it's a new day but they haven't made a request yet, the DB still shows old count
  # reset it to 0 for the UI
  
  current_count = user.request_count
  if user.last_request and user.last_request.date() < now.date():
    current_count = 0
    
  user_info = {
    "username": user.username,
    "email": user.email,
    "is_unlimited": user.is_unlimited,
    "request_count": current_count,
    "max_requests": MAX_REQUESTS,
    "next_reset": next_reset,
    "last_request": user.last_request
  }
  
  return user_info