from datetime import timedelta
from typing import Annotated
from fastapi import APIRouter, Body, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from bson import ObjectId, json_util
import json
from fastapi.encoders import jsonable_encoder
import time
import datetime

from dependencies.models import Token, User, UserAuth
from internals.auth import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, get_password_hash
from internals.user import authenticate_user, get_current_active_user

from db import get_db
from internals.user import get_current_user

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

@router.get("/homeworks", response_description="Show current user homeworks")
async def show_user_homeworks(current_user: Annotated[User, Depends(get_current_user)]):
  _db = await get_db()

  homeworks = []

  ct = datetime.datetime.now()
  dt = ct.timestamp()

  if current_user['role'] == 1:
    classrooms = await _db["classrooms"].find({"teacher_id": current_user['_id']}).to_list(None)

    if classrooms:
      for classroom in classrooms:
        tmp_homeworks = await _db["classrooms_homeworks"].find({'classroom_id': classroom['_id'] }).to_list(None)
        if tmp_homeworks:
          homeworks += tmp_homeworks
  elif current_user['role'] == 0:
    student_classrooms = await _db["classrooms_students"].find({'student_id': current_user['_id'] }).to_list(None)
    for student_classroom in student_classrooms:
        tmp_homeworks = await _db["classrooms_homeworks"].find({'classroom_id': student_classroom['classroom_id'], "expire_datetime": {"$gte": int(dt)} }).to_list(None)
        if tmp_homeworks:
          for tmp_homework in tmp_homeworks:
            tmp_homework['status'] = 0
            homework_map = await _db["classrooms_homeworks_maps"].find_one({'homework_id': tmp_homework['_id'], 'student_id': current_user['_id'] })
            if homework_map:
              tmp_homework['status'] = 1

            homeworks.append(tmp_homework)

  return JSONResponse(status_code=status.HTTP_200_OK, content=json.loads(json_util.dumps(homeworks)))

@router.get("/homeworks/expired", response_description="Show current user homeworks")
async def show_user_homeworks(current_user: Annotated[User, Depends(get_current_user)]):
  _db = await get_db()

  homeworks = []

  ct = datetime.datetime.now()
  dt = ct.timestamp()

  if current_user['role'] == 1:
    classrooms = await _db["classrooms"].find({"teacher_id": current_user['_id']}).to_list(None)

    if classrooms:
      for classroom in classrooms:
        tmp_homeworks = await _db["classrooms_homeworks"].find({'classroom_id': classroom['_id'] }).to_list(None)
        if tmp_homeworks:
          homeworks += tmp_homeworks

  elif current_user['role'] == 0:
    student_classrooms = await _db["classrooms_students"].find({'student_id': current_user['_id'] }).to_list(None)
    for student_classroom in student_classrooms:
        tmp_homeworks = await _db["classrooms_homeworks"].find({'classroom_id': student_classroom['classroom_id'], "expire_datetime": {"$lte": int(dt)} }).to_list(None)
        if tmp_homeworks:
          for tmp_homework in tmp_homeworks:
            tmp_homework['status'] = 0
            homework_map = await _db["classrooms_homeworks_maps"].find_one({'homework_id': tmp_homework['_id'], 'student_id': current_user['_id'] })
            if homework_map:
              tmp_homework['status'] = 1

            homeworks.append(tmp_homework)

  return JSONResponse(status_code=status.HTTP_200_OK, content=json.loads(json_util.dumps(homeworks)))

@router.post("/", response_description="Add a new user")
async def create_user(user: User = Body(...)):
  _db = await get_db()

  user = jsonable_encoder(user)

  same_user = await _db["users"].find_one({"$or": [{"username": user['username']}, {"email": user['email']}]})

  if same_user:
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Specified username or email address already exists")

  user['password'] = get_password_hash(user['password'])
  user['created_at'] = int(time.time())
  user['is_disabled'] = False

  new_user = await _db["users"].insert_one(user)
  created_user = await _db["users"].find_one({"_id": new_user.inserted_id})

  return JSONResponse(status_code=status.HTTP_201_CREATED, content=json.loads(json_util.dumps(created_user)))
