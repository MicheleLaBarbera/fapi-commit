from typing import Annotated
from bson import ObjectId
from fastapi import APIRouter, Body, Depends, status, HTTPException
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
import json
import numpy as np
import time

from db import get_db
from dependencies.models import Simulation, User
from dependencies.utils import ConceptMap
from internals.user import get_current_user
from datetime import date
import datetime

router = APIRouter(
	prefix="/simulations",
	tags=["simulations"],
	responses={404: {"description": "Not found"}},
)

@router.get("/", response_description="List all simulations")
async def read_simulations():
	_db = await get_db()


	dt = int(time.mktime(datetime.datetime.strptime(str(date(date.today().year, 1, 1)), "%Y-%m-%d").timetuple()))

	simulations_count = await _db["simulations"].count_documents({"created_at": {"$gte": dt}})
	simulations_maps_count = await _db["simulations_maps"].count_documents({"created_at": {"$gte": dt}})
	return {"simulations_count": simulations_count, "simulations_maps_count": simulations_maps_count}

@router.get("/{name}", response_description="Get a single simulation", response_model=Simulation)
async def show_simulation(name: str, current_user: Annotated[User, Depends(get_current_user)]):
	_db = await get_db()

	simulation = await _db["simulations"].find_one({"name": name})

	if not simulation:
		raise HTTPException(
			status_code=status.HTTP_404_NOT_FOUND,
			detail="Simulation not found",
		)
	
	if simulation['is_public'] == False and simulation['owner_id'] != current_user['_id']:
		raise HTTPException(
      status_code=status.HTTP_401_UNAUTHORIZED,
      detail="You are not authorized to view this simulation",
    )

	simulation_maps = await _db["simulations_maps"].find({"simulation_id": ObjectId(simulation['_id'])}).to_list(None)

	simulation['maps'] = simulation_maps

	return simulation

@router.post("/", response_description="Add a new simulation")
async def create_simulation(current_user: Annotated[User, Depends(get_current_user)], simulation: Simulation = Body(...)):
	_db = await get_db()

	simulation = jsonable_encoder(simulation)
	simulation['owner_id'] = current_user['_id']
	simulation['created_at'] = int(time.time())
	del simulation['maps']
	
	new_simulation = await _db["simulations"].insert_one(simulation)
	created_simulation = await _db["simulations"].find_one({"_id": new_simulation.inserted_id})

	max_entropy = 0
	max_entropy_percent = 0
	max_effort = 0

	maps = []
	adjacency_matrix_list = []
	data = []

	# Generate 'n' concept maps
	for _ in range(created_simulation['maps_count']):
		map = ConceptMap() # Create ConceptMap object
		map.generate(created_simulation['node_min'], created_simulation['node_max']) # Generate a random directed acyclic graph (DAG) with given parameters
		
		maps.append(map) # Append the generated map in a maps list
		adjacency_matrix_list.append(map.get_adjacency_matrix()) # Append the adjacency matrix of the generated map in a adjacency matrix list

		if map.get_entropy() > max_entropy:
			max_entropy = map.get_entropy()

		if map.get_entropy_percent() > max_entropy_percent:
			max_entropy_percent = map.get_entropy_percent()

		if map.get_effort() > max_effort:
			max_effort = map.get_effort()

	first_part_entropy = (max_entropy / 3)
	second_part_entropy = first_part_entropy * 2

	first_part_entropy_percent = (max_entropy_percent / 3)
	second_part_entropy_percent = first_part_entropy_percent * 2

	first_part_effort = (max_effort / 3)
	second_part_effort = first_part_effort * 2

	i = 0
	for map in maps:
		color_entropy = 0
		if map.get_entropy() > (first_part_entropy) and map.get_entropy() < second_part_entropy:
			color_entropy = 1
		elif map.get_entropy() > second_part_entropy:
			color_entropy = 2

		color_entropy_percent = 0
		if map.get_entropy_percent() > (first_part_entropy_percent) and map.get_entropy_percent() < second_part_entropy_percent:
			color_entropy_percent = 1
		elif map.get_entropy_percent() > second_part_entropy_percent:
			color_entropy_percent = 2

		color_effort = 0
		if map.get_effort() > (first_part_effort) and map.get_effort() < second_part_effort:
			color_effort = 1
		elif map.get_effort() > second_part_effort:
			color_effort = 2

		data.append({
			'simulation_id': ObjectId(new_simulation.inserted_id), 
			'color_entropy': color_entropy,
			'color_entropy_percent': color_entropy_percent,
			'color_effort': color_effort,
			'nodes_count': map.get_nodes_count(),
			'entropy': round(map.get_entropy(), 2),
			'entropy_percent': round(map.get_entropy_percent(), 2),
			'effort': round(map.get_effort(), 2),
			'edges_count': map.get_edges_count(),
			'created_at': simulation['created_at'],
			'adjacency_matrix': np.char.mod('%s', adjacency_matrix_list[i]).tolist()
		})
		i = i + 1

	await _db["simulations_maps"].insert_many(data)

	return JSONResponse(status_code=status.HTTP_201_CREATED, content=json.loads(json.dumps({"_id": simulation['_id']})))
