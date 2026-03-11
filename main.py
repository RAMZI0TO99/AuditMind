from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from database import engine
import models

# Import our new modular routers
from routers import auth, documents, payments, rules

# Create database tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Compliance Guard API")

app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount the routers
app.include_router(auth.router)
app.include_router(documents.router)
app.include_router(payments.router)
app.include_router(rules.router)

# Serve the frontend
@app.get("/")
async def serve_frontend():
    return FileResponse("index.html")