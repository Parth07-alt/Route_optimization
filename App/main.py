from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from App.routes import demand, routing, full_pipeline
from App.routes.visualization import router as visualization_router  # 🆕
from App.database.db import init_db
from App.routes.whatsapp import router as whatsapp_router  # 🆕from fastapi.staticfiles imp
from fastapi.middleware.cors import CORSMiddleware




  # 🆕

# Add this line before app routes
init_db()

app = FastAPI(title="Smart Water Distribution System")

# Add after app = FastAPI(...)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static folder so maps are accessible via browser
app.mount("/static", StaticFiles(directory="App/static"), name="static")  # 🆕

# Existing routes
app.include_router(demand.router)
app.include_router(routing.router)
app.include_router(full_pipeline.router)

# New visualization route
app.include_router(visualization_router)  # 🆕

# Add with other routers
app.include_router(whatsapp_router)

# Add this line with other mounts
app.mount("/driver", StaticFiles(directory="driver_app", html=True), name="driver")
