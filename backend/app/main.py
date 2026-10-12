from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import REPO_ROOT, get_settings
from app.routers import accounts, analytics, categories, me, transactions, uploads
from app.version import app_commit, app_version

settings = get_settings()

app = FastAPI(title="Personal Finance API", version=app_version())
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["*"],
    allow_headers=["*"],
)

api = APIRouter(prefix="/api")


@api.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


@api.get("/version", tags=["health"])
def version():
    """The version and git commit of the code this server is running."""
    return {"version": app_version(), "commit": app_commit()}


for module in (me, accounts, uploads, transactions, categories, analytics):
    api.include_router(module.router)
app.include_router(api)


# Serve the built web app (frontend/dist) when it exists, so the whole app runs
# from one address. In development, Vite serves the frontend instead.
FRONTEND_DIST = (REPO_ROOT / "frontend" / "dist").resolve()

if FRONTEND_DIST.is_dir():

    @app.get("/{path:path}", include_in_schema=False)
    def frontend(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")
        file = (FRONTEND_DIST / path).resolve()
        if path and file.is_file() and file.is_relative_to(FRONTEND_DIST):
            return FileResponse(file)
        # Client-side routes (/transactions, /import, ...) all load the app shell.
        return FileResponse(FRONTEND_DIST / "index.html")
