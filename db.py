import os
import motor.motor_asyncio
from dotenv import load_dotenv

load_dotenv()
			
_MONGODB_URL = os.getenv('MONGODB_URL')

_db = None 

async def setup_db():
  global _db
  client = motor.motor_asyncio.AsyncIOMotorClient(_MONGODB_URL)
  _db = client.entropy
  return _db

async def get_db():
  global _db
  if _db is not None:
      return _db
  
  db = await setup_db()
  return db

async def shutdown_db():
  global _db
  _db = None