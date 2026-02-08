from fastapi import HTTPException, status, Depends
import uuid


# Modules
from Back.services.redis_client import get_redis
from Back.dependencies import get_current_user
from Back.db.models import User

async def check_user_cooldown(
        user: User = Depends(get_current_user),
        redis = Depends(get_redis)
):
  """
  To prevent spamming for 10 seconds after a request
  """
  
  key = f"cooldown:user:{user.id}"
  
  is_allowed = await redis.set(key, "locked", ex=10, nx=True) # u can have anything instead of "locked", maybe meow?
  # nx means to set the key only if it doesn't exist
  
  if not is_allowed: # it means key is None which means it exists alr
    ttl = await redis.ttl(key) # time for cooldown
    
    raise HTTPException(
      status_code=status.HTTP_429_TOO_MANY_REQUESTS,
      detail=f"Calm down, please wait {ttl} second(s)"
    )
  
  return True
  