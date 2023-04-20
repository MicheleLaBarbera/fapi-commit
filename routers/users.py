from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from dependencies.models import Token, User, UserAuth
from internals.auth import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token
from internals.user import authenticate_user, get_current_active_user

router = APIRouter(
	prefix="/users",
	tags=["users"],
	responses={404: {"description": "Not found"}},
)

@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: UserAuth):
  user = await authenticate_user(form_data.username, form_data.password)
  if not user:
    raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="Incorrect username or password",
      headers={"WWW-Authenticate": "Bearer"},
    )
  
  access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
  access_token = create_access_token(data={"sub": user['username']}, expires_delta=access_token_expires)
  return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=User)
async def read_users_me(current_user: Annotated[User, Depends(get_current_active_user)]):
  return current_user