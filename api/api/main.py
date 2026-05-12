from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# React assets
app.mount(
    "/assets",
    StaticFiles(directory="web/dist/assets"),
    name="assets"
)

# Root route
@app.get("/")
async def root():
    return FileResponse("web/dist/index.html")

# React routes
@app.get("/{full_path:path}")
async def serve_react_app(full_path: str):
    return FileResponse("web/dist/index.html")