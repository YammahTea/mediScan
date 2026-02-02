from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import jwt

# Modules
from Back.db.database import get_db
from Back.db.models import User
from Back.services.auth import verify_password, create_access_token, add_token_to_blacklist, SECRET_KEY, ALGORITHM
from Back.dependencies import get_current_user, oauth2_scheme

router = APIRouter(
  tags=["Authentication"]
)

@router.post("/login")
async def login(
        form_data: OAuth2PasswordRequestForm = Depends(),
        db: AsyncSession = Depends(get_db)
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
  
  # 4- create the token
  access_token = create_access_token(
    data={"sub": user.username}
  )
  
  return {"access_token": access_token, "token_type": "bearer"}


@router.post("/logout")
async def logout(
  user: User = Depends(get_current_user), # to avoid errors if the user is not actually logged in
  token: str = Depends(oauth2_scheme),
  db: AsyncSession = Depends(get_db)
):
  
  try:
    # 1- Decode just to find out when this token was supposed to expire
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    expiration = payload.get("exp")
    
    # 2- Blacklist the token
    await add_token_to_blacklist(token, expiration, db)

  except jwt.PyJWTError:
    pass
  
  return {"message": "Successfully logged out"}