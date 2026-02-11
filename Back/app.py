from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# For admin panel
from sqladmin import Admin, ModelView
from Back.db.database import engine
from Back.db.models import User

# Routers
from Back.routers import login, upload, tools, profile

# Modules
from Back.core.pipeline import load_models
from Back.db.database import create_db_and_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
  
  # 1- Load all models (yolo + ocr)
  hunter, surgeon, reader = await load_models()
  
  app.state.hunter_model = hunter
  app.state.surgeon_model = surgeon
  app.state.reader = reader
  
  # 2- create db
  await create_db_and_tables()

  yield

app = FastAPI(lifespan=lifespan)

origins = [
  "http://localhost:5173", # for local testing (yes i will add the frontend url when i host it)
  "http://127.0.0.1:5173", # cuz the browser deals with localhost but the backend sets the cookie in this domain...
  "https://mediscan-dun.vercel.app/" # frontend url :)
]

app.add_middleware(
  CORSMiddleware,
  allow_origins=origins,
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
  expose_headers=["Content-Disposition"]
)

# connecting routers
app.include_router(login.router)
app.include_router(upload.router)
app.include_router(profile.router)
app.include_router(tools.router)

#  ADMIN PANEL SETUP
class UserAdmin(ModelView, model=User):
  column_list = [User.id, User.username, User.email, User.is_unlimited, User.is_active, User.request_count, User.last_request, User.is_verified]
  
  can_create = True
  can_edit = True
  can_delete = True
  
  icon = "fa-solid fa-user"

# This adds the /admin route
authentication_backend = None
admin = Admin(app, engine)
admin.add_view(UserAdmin)