from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import  selectinload
from sqlalchemy import select
import jwt

# Modules
from Back.db.database import get_db
from Back.db.models import User, RefreshToken
from Back.services.auth import verify_password, hash_token, create_access_token, create_refresh_token, add_token_to_blacklist, AUTH_REFRESH_TOKEN_EXPIRE_DAYS, SECRET_KEY, ALGORITHM
from Back.dependencies import get_current_user, oauth2_scheme
from Back.services.redis_client import get_redis

router = APIRouter(
  tags=["Authentication"]
)

@router.post("/login")
async def login(
        response: Response,
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db),
):
  """
  Finds user in db and check if it is a valid user with the correct password
  and then checks if the account is active and then creates an access token
  """
  
  # 1- Find user in db (by email or username)
  
  if "@" in form_data.username: # simple check because i am the one who will make the user account :)
    query = select(User).where(User.email == form_data.username)
    result = await db.execute(query)
    user = result.scalars().first()
    
  else:
    query = select(User).where(User.username == form_data.username)
    result = await db.execute(query)
    user = result.scalars().first()


# 2- check if user doesn't exist or if the password doesn't match
  if not user or not verify_password(form_data.password, user.hashed_password):
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Incorrect username or password",
      headers={"WWW-Authenticate": "Bearer"}
    )
  
  # 3- check if the user is active
  if not user.is_active:
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="The account is deactivated")
  
  # 4- create the access token + refresh token
  access_token = create_access_token(
    data={"sub": user.username}
  )
  
  refresh_token = await create_refresh_token(user.id, db)
  
  response.set_cookie(
    key="refresh_token",
    value=refresh_token,
    httponly=True,
    secure=True,
    samesite="none", # changed from lax, because i kept having issues between vercel and modal
    max_age=AUTH_REFRESH_TOKEN_EXPIRE_DAYS * 86400,
    path="/",
  )
  
  return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
        response: Response,
        user: User = Depends(get_current_user), # to avoid errors if the user is not actually logged in
        token: str = Depends(oauth2_scheme),
        db: AsyncSession = Depends(get_db),
        redis = Depends(get_redis)
):
  
  try:
    # 1- Decode just to find out when this token was supposed to expire
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    expiration = payload.get("exp")
    await add_token_to_blacklist(token, expiration, redis)
    
    
    # 2- Blacklist the token
    await add_token_to_blacklist(token, expiration, redis)

  except jwt.PyJWTError:
    pass
  
    # 3- delete the cookie
  response.delete_cookie(
    key="refresh_token",
    path="/",
    secure=True,
    httponly=True,
    samesite="lax"
  )
  
  return {"message": "Successfully logged out"}


@router.post("/refresh")
async def refresh_token(
        request: Request,
        response: Response,
        db: AsyncSession = Depends(get_db)
):
  
  # 1- grab the cookie
  refresh_token_raw = request.cookies.get("refresh_token")
  if not refresh_token_raw:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is missing")
  
  # 2- hash the refresh token
  hashed_token = hash_token(refresh_token_raw)
  
  # 3- Check if the hashed token exists in the db and is associated with its user
  # selectinload is faster than the normal join (look it up bruh)
  query = (
    select(RefreshToken)
    .where(RefreshToken.hashed_token == hashed_token)
    .options(selectinload(RefreshToken.user))
  )
  
  result = await db.execute(query)
  stored_token: RefreshToken = result.scalars().first()
  
  # 4- validate the result
  if not stored_token:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
  
  if stored_token.revoked:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token is revoked")
  
  # 5- Get the user
  user = stored_token.user
  if not user or not user.is_active:
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
  
  # 6- create new access token
  new_access_token = create_access_token(data={"sub": user.username})
  
  # 6.5- remove the old refresh token (Rotation)
  stored_token.revoked = True
  new_refresh_token = await create_refresh_token(user.id, db)
  
  # 7- set the cookie
  response.set_cookie(
    key="refresh_token",
    value=new_refresh_token,
    httponly=True,
    secure=True, # make it false if testing localy
    samesite="lax",
    max_age=AUTH_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60, # days to seconds
    path="/"
  )
  
  return {"access_token": new_access_token, "token_type": "bearer"}
