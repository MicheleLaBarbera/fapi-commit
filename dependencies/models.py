from typing import Optional, List
from bson import ObjectId
from pydantic import BaseModel, Field

class PyObjectId(ObjectId):
	@classmethod
	def __get_validators__(cls):
		yield cls.validate

	@classmethod
	def validate(cls, v):
		if not ObjectId.is_valid(v):
			raise ValueError("Invalid ObjectID")
		return ObjectId(v)

	@classmethod
	def __modify_schema__(cls, field_schema):
		field_schema.update(type="string")


class SimulationMap(BaseModel):
	id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
	simulation_id: PyObjectId = Field(default_factory=PyObjectId)
	color_entropy: int 
	color_entropy_percent: int
	color_effort: int 
	nodes_count: int 
	edges_count: int
	entropy: float 
	entropy_percent: float 
	effort: float 
	created_at: int
	adjacency_matrix: List[List[int]]

	class Config:
		allow_population_by_field_name = True
		arbitrary_types_allowed = True
		json_encoders = {ObjectId: str}	

class Simulation(BaseModel):
	id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
	name: str
	maps_count: int
	node_min: int
	node_max: int
	is_public: bool
	owner_id: PyObjectId = Field(default_factory=PyObjectId)
	created_at: Optional[int]
	maps: Optional[List[SimulationMap]]

	class Config:
		allow_population_by_field_name = True
		arbitrary_types_allowed = True
		json_encoders = {ObjectId: str}
		schema_extra = {
			"example": {
				"name": "redhawk",
				"maps_count": "1000",
				"node_min": "10",
				"node_max": "25",
			}
		}

class Token(BaseModel):
	access_token: str
	token_type: str

class User(BaseModel):
	username: str
	email: str
	firstname: str
	lastname: str
	is_disabled: bool

class UserAuth(BaseModel):
	username: str
	password: str
	remember_me: int

class TokenData(BaseModel):
  username: str | None = None
