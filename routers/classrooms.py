import math
from typing import Annotated
from bson import ObjectId, json_util
from fastapi import APIRouter, Body, Depends, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import json
import time
import uuid 

from db import get_db
from dependencies.models import Classroom, ClassroomHomework, ClassroomHomeworkMap, User
from dependencies.utils import ConceptMap
from internals.user import get_current_user
import datetime
  
router = APIRouter(
  prefix="/classrooms",
  tags=["classrooms"],
  responses={404: {"description": "Not found"}},
)

@router.get("/invite/{invite_token}", response_description="Make a student join a classroom")
async def student_join_classrooms(invite_token: str, current_user: Annotated[User, Depends(get_current_user)]):
  _db = await get_db()

  if current_user['role'] != 0:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a student")

  classroom = await _db["classrooms"].find_one({"invite_token": invite_token})

  if classroom == None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom invite link not found")
  
  search_classroom_student = await _db["classrooms_students"].find_one({ 'classroom_id': classroom['_id'], 'student_id': current_user['_id'] })

  if search_classroom_student:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You have already joined this classroom")
        
  new_classroom_student = await _db["classrooms_students"].insert_one({ 'classroom_id': ObjectId(classroom['_id']), 'student_id': ObjectId(current_user['_id']) })
  created_classroom_student = await _db["classrooms_students"].find_one({"_id": new_classroom_student.inserted_id})

  return JSONResponse(status_code=status.HTTP_201_CREATED, content=json.loads(json_util.dumps(created_classroom_student)))

@router.get("/", response_description="Get all the classrooms")
async def show_classrooms(current_user: Annotated[User, Depends(get_current_user)]):
  _db = await get_db()
        
  if current_user['role'] == 1:
  
    classrooms = await _db["classrooms"].find({"teacher_id": current_user['_id']}).to_list(None)

    ct = datetime.datetime.now()
    dt = ct.timestamp()
    
    if classrooms:
      for classroom in classrooms:
        teacher = await _db["users"].find_one({"_id": classroom['teacher_id']})
        classroom["teacher"] = teacher
    
        classroom_students_count = await _db["classrooms_students"].count_documents({"classroom_id": classroom['_id']})
        classroom["students_count"] = classroom_students_count

        classroom_homeworks_count = await _db["classrooms_homeworks"].count_documents({"classroom_id": classroom['_id'], "expire_datetime": {"$gte": int(dt)}})
        classroom["homeworks_count"] = classroom_homeworks_count
          
    return JSONResponse(status_code=status.HTTP_200_OK, content=json.loads(json_util.dumps(classrooms)))
  
  if current_user['role'] == 0:
    classrooms_student = await _db["classrooms_students"].find({"student_id": current_user['_id']}).to_list(None)

    classrooms = []

    ct = datetime.datetime.now()
    dt = ct.timestamp()

    if classrooms_student:
      for classroom_student in classrooms_student:
        classroom = await _db["classrooms"].find_one({"_id": classroom_student['classroom_id']})
        teacher = await _db["users"].find_one({"_id": ObjectId(classroom['teacher_id'])})
        classroom["teacher"] = teacher
        print(classroom)

        classroom_students_count = await _db["classrooms_students"].count_documents({"classroom_id": classroom['_id']})
        classroom["students_count"] = classroom_students_count

        classroom_homeworks_count = await _db["classrooms_homeworks"].count_documents({"classroom_id": classroom['_id'], "expire_datetime": {"$gte": int(dt)}})
        classroom["homeworks_count"] = classroom_homeworks_count

        classrooms.append(classroom)

    return JSONResponse(status_code=status.HTTP_200_OK, content=json.loads(json_util.dumps(classrooms)))

@router.get("/{id}", response_description="Show classroom")
async def show_classroom(id: str, current_user: Annotated[User, Depends(get_current_user)]):
  _db = await get_db()

  classroom = await _db["classrooms"].find_one({"_id": ObjectId(id)})

  if classroom == None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")
  
  if current_user['role'] == 1 and classroom['teacher_id'] != current_user['_id']:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to see this classroom")
  elif current_user['role'] == 0:
    student_classroom = await _db["classrooms_students"].find_one({'classroom_id': classroom['_id'], 'student_id': current_user['_id'] })
    if student_classroom == None:
      raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to see this classroom")
  
  teacher = await _db["users"].find_one({'_id': classroom['teacher_id']})

  if teacher != None:
    classroom['teacher'] = {
      'firstname': teacher['firstname'],
      'lastname': teacher['lastname'],
      'email': teacher['email']
    }

  return JSONResponse(status_code=status.HTTP_200_OK, content=json.loads(json_util.dumps(classroom)))


@router.get("/{id}/students", response_description="Show classroom students")
async def show_classroom_students(id: str, current_user: Annotated[User, Depends(get_current_user)]):
  _db = await get_db()

  classroom = await _db["classrooms"].find_one({"_id": ObjectId(id)})

  if classroom == None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")
  
  if current_user['role'] == 1 and classroom['teacher_id'] != current_user['_id']:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to see this classroom")
  
  classroom_students = await _db["classrooms_students"].find({ 'classroom_id': classroom['_id'] }).to_list(None)

  students = []

  is_valid_student = True if current_user['role'] == 1 else False

  for classroom_student in classroom_students:
    student = await _db["users"].find_one({'_id': classroom_student['student_id'] })

    if student:
      if is_valid_student == False and student['_id'] == current_user['_id']:
        is_valid_student = True

      students.append({
        'firstname': student['firstname'],
        'lastname': student['lastname'],
        'email': student['email']
      })

  if is_valid_student == False:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to see this classroom")
  
  return JSONResponse(status_code=status.HTTP_200_OK, content=json.loads(json_util.dumps(students)))

@router.get("/{id}/homeworks", response_description="Show classroom homeworks")
async def show_classroom_homeworks(id: str, current_user: Annotated[User, Depends(get_current_user)]):
  _db = await get_db()

  classroom = await _db["classrooms"].find_one({"_id": ObjectId(id)})

  if classroom == None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")
  
  if current_user['role'] == 1 and classroom['teacher_id'] != current_user['_id']:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to see this classroom")
  elif current_user['role'] == 0:
    student_classroom = await _db["classrooms_students"].find_one({'classroom_id': classroom['_id'], 'student_id': current_user['_id'] })
    if student_classroom == None:
      raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to see this classroom")
  
  homeworks = await _db["classrooms_homeworks"].find({'classroom_id': classroom['_id'] }).to_list(None)

  for homework in homeworks:
    homework_maps = await _db["classrooms_homeworks_maps"].find({'homework_id': homework['_id'] }).to_list(None)
    homework['maps'] = homework_maps

  return JSONResponse(status_code=status.HTTP_200_OK, content=json.loads(json_util.dumps(homeworks)))

@router.post("/", response_description="Add a new classroom")
async def create_classroom(current_user: Annotated[User, Depends(get_current_user)], classroom: Classroom = Body(...)):
  _db = await get_db()

  if current_user['role'] != 1:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a teacher")
  
  classroom = jsonable_encoder(classroom)
  del classroom['_id']

  same_classroom = await _db["classrooms"].find_one({"teacher_id": current_user['_id'], "name": classroom['name']})
  if same_classroom:
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Specified classroom name already exists")

  classroom['teacher_id'] = current_user['_id']
  classroom['invite_token'] = str(uuid.uuid4())
  classroom['created_at'] = int(time.time())

  new_classroom = await _db["classrooms"].insert_one(classroom)
  created_classroom = await _db["classrooms"].find_one({"_id": new_classroom.inserted_id})

  return JSONResponse(status_code=status.HTTP_201_CREATED, content=json.loads(json_util.dumps(created_classroom)))


@router.post("/{id}/homeworks", response_description="Add a new classroom homework")
async def create_classroom_homework(id: str, current_user: Annotated[User, Depends(get_current_user)], classroom_homework: ClassroomHomework = Body(...)):
  _db = await get_db()

  if current_user['role'] != 1:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not a teacher")
  
  classroom = await _db["classrooms"].find_one({"_id": ObjectId(id)})

  if classroom == None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")
  
  if classroom['teacher_id'] != current_user['_id']:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not the teacher of this classroom")

  classroom_homework = jsonable_encoder(classroom_homework)
  del classroom_homework['_id']

  classroom_homework['classroom_id'] = ObjectId(id)

  new_classroom_homework = await _db["classrooms_homeworks"].insert_one(classroom_homework)
  created_classroom_homework = await _db["classrooms_homeworks"].find_one({"_id": new_classroom_homework.inserted_id})

  return JSONResponse(status_code=status.HTTP_201_CREATED, content=json.loads(json_util.dumps(created_classroom_homework)))


@router.get("/{classroom_id}/homeworks/{homework_id}", response_description="Show classroom homeworks")
async def show_classroom_homeworks(classroom_id: str, homework_id: str, current_user: Annotated[User, Depends(get_current_user)]):
  _db = await get_db()

  classroom = await _db["classrooms"].find_one({"_id": ObjectId(classroom_id)})

  if classroom == None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")
  
  if current_user['role'] == 1 and classroom['teacher_id'] != current_user['_id']:
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to see this classroom")
  elif current_user['role'] == 0:
    student_classroom = await _db["classrooms_students"].find_one({'classroom_id': classroom['_id'], 'student_id': current_user['_id'] })
    if student_classroom == None:
      raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to see this classroom")
  
  homework = await _db["classrooms_homeworks"].find_one({'_id': ObjectId(homework_id)})
  
  if homework == None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found")
  
  if current_user['role'] == 0:
    homework_map = await _db["classrooms_homeworks_maps"].find_one({'homework_id': ObjectId(homework_id), 'student_id': current_user['_id'] })
    homework['student_map'] = homework_map

  if current_user['role'] == 1:
    homework_maps = await _db["classrooms_homeworks_maps"].find({'homework_id': homework['_id'] }).to_list(None)

    homework['maps'] = []

    for homework_map in homework_maps:
      author = await _db["users"].find_one({'_id': ObjectId(homework_map['student_id'])})
      homework_map['author_name'] = author['firstname'] + " " + author['lastname'] if author else ""
      homework_map['is_teacher_map'] = True if author['role'] == 1 else False

      homework['maps'].append(homework_map)

  return JSONResponse(status_code=status.HTTP_200_OK, content=json.loads(json_util.dumps(homework)))

@router.post("/{classroom_id}/homeworks/{homework_id}", response_description="Create classroom homework")
async def create_classroom_homework_map(classroom_id: str, homework_id: str, current_user: Annotated[User, Depends(get_current_user)], classroom_homework_map: ClassroomHomeworkMap = Body(...)):
  _db = await get_db()

  classroom = await _db["classrooms"].find_one({"_id": ObjectId(classroom_id)})

  if classroom == None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Classroom not found")
  
  if current_user['role'] == 0:
    student_classroom = await _db["classrooms_students"].find_one({'classroom_id': classroom['_id'], 'student_id': current_user['_id'] })
    if student_classroom == None:
      raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are not allowed to submit the homework in this classroom")
  
  homework = await _db["classrooms_homeworks"].find_one({'_id': ObjectId(homework_id) })
  
  if homework == None:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Homework not found")
  
  classroom_homework_map = jsonable_encoder(classroom_homework_map)
  del classroom_homework_map['_id']
  classroom_homework_map['homework_id'] = ObjectId(classroom_homework_map['homework_id'])
  classroom_homework_map['student_id'] = current_user['_id']
  classroom_homework_map['created_at'] = int(time.time())

  classroom_homework_map['entropy'] = 0
  entropy_max = [0, 0, 0, 1,2.584962501,4.584962501,6.906890596,9.491853096,12.29920802,15.29920802,18.46913302,21.79106111,25.25049273,28.83545523,32.53589495,36.34324987,40.25014047,44.25014047,48.33760331,52.50752831,56.75545583,61.07738392,65.46970134,69.92913296,74.45269492,79.03765742,83.68151361,88.38195333,93.13684083,97.94419575,102.8021767]
  for x in classroom_homework_map['adjacency_matrix']:
    links_count = 0 
    for y in x: # Check for every node how many links it has
      if y == 1:
        links_count = links_count + 1
    
    node_entropy = 0
    if links_count > 0:
      probability = 1 / links_count 
      for _ in range(links_count):
        node_entropy = node_entropy + abs((probability * math.log(probability, 2))) # Entropy formula

    classroom_homework_map['entropy'] = classroom_homework_map['entropy'] + node_entropy

  if classroom_homework_map['nodes_count'] >= 0 and classroom_homework_map['nodes_count'] <= 30:
    classroom_homework_map['entropy_percent'] = (classroom_homework_map['entropy'] / entropy_max[classroom_homework_map['nodes_count']]) * 100

    classroom_homework_map['effort'] = (classroom_homework_map['entropy_percent'] / 100) * classroom_homework_map['nodes_count'] * classroom_homework_map['edges_count']

  new_classroom_homework_map = await _db["classrooms_homeworks_maps"].insert_one(classroom_homework_map)
  created_classroom_homework_map = await _db["classrooms_homeworks_maps"].find_one({"_id": new_classroom_homework_map.inserted_id})
  
  return JSONResponse(status_code=status.HTTP_201_CREATED, content=json.loads(json_util.dumps(created_classroom_homework_map)))

