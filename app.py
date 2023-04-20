from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from db import setup_db, shutdown_db
from routers import simulations, users

@asynccontextmanager
async def lifespan(app: FastAPI):
  await setup_db()
  yield
  await shutdown_db()

app = FastAPI(lifespan=lifespan)

origins = [
  "http://localhost",
  "http://localhost:4200",
]

app.add_middleware(
  CORSMiddleware,
  allow_origins=origins,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)

app.include_router(users.router)
app.include_router(simulations.router)





