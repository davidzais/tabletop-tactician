
import os
from functools import cache
from pathlib import Path
from uuid import uuid4

import structlog
import uvicorn
from clerk_backend_api import Clerk
from clerk_backend_api.security.types import AuthenticateRequestOptions
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.security import HTTPBearer
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from tabletop_tactician.agent.adviser import build_full_report
from tabletop_tactician.api.middleware import RequestIdMiddleware, SecurityHeadersMiddleware
from tabletop_tactician.config import get_settings
from tabletop_tactician.logging_config import configure_logging
from tabletop_tactician.reference_data.roster import Army, load_roster

configure_logging(
    log_level=os.getenv("LOG_LEVEL", "INFO"),
    json_logs=os.getenv("JSON_LOGS", "false").lower() == "true",
)


logger = structlog.get_logger()

bearer_scheme = HTTPBearer(auto_error=False)   
limiter = Limiter(key_func=get_remote_address)


_cors_origins = [
    o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:8000").split(",")
]

app = FastAPI(title="Tabletop Tactician API", description="A tabletop wargame battle report generator with LLM analysis")
app.state.limiter = limiter
app.add_middleware(middleware_class=SecurityHeadersMiddleware)
app.add_middleware(middleware_class=RequestIdMiddleware)
app.add_middleware(
    middleware_class=CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["POST"],
    allow_headers=["Content-Type", "Authorization"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
)


#set up the path to static files to serve the simple UI
STATIC_DIR = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

JOBS: dict[str, dict[str, str | None]] = {}

def _get_rate_limit() -> str:
    settings = get_settings()
    return settings.rate_limit

def verify_clerk_user(request: Request,  _credentials=Depends(bearer_scheme)) -> str:
    state = get_clerk().authenticate_request(request, options=AuthenticateRequestOptions(authorized_parties=_cors_origins))
    payload = state.payload
    if not state.is_signed_in or payload is None:
        raise HTTPException(401, "Not authenticated")
    return payload["sub"]   # the Clerk user id

@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    logger.warning("rate_limit_exceeded", client=get_remote_address(request))
    return JSONResponse(
        status_code=429, content={"detail": "Too many requests. Please slow down."}
    )

@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")

@app.post("/report", status_code=status.HTTP_202_ACCEPTED, dependencies=[Depends(verify_clerk_user)])
@limiter.limit(limit_value=_get_rate_limit)
def generate_report(request: Request, my_army: UploadFile, enemy_army: UploadFile, background_tasks: BackgroundTasks, dry_run: bool = False):

    saved_files = {}
    current_processing_army = None
    
    try:
        current_processing_army = "my_army"
        content_bytes = my_army.file.read()
        my_army_content = content_bytes.decode("utf-8")
        saved_files["my_army"] = my_army_content

        current_processing_army = "enemy_army"
        content_bytes = enemy_army.file.read()
        enemy_army_content = content_bytes.decode("utf-8")
        saved_files["enemy_army"] = enemy_army_content

        attacker: Army = load_roster(saved_files["my_army"])
        defender: Army = load_roster(saved_files["enemy_army"])

        #creat a unique job id and set its status to pending in the JOBS dictionary
        job_id = str(uuid4())
        JOBS[job_id] = {"status": "pending", "report": None}

        #run this in the background so that the API can return a response immediately
        background_tasks.add_task(process_report, job_id, attacker, defender, dry_run)
        return {"job_id": job_id}   
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not parse file {current_processing_army}: {str(e)}"
        )
    finally:
        # Always close the FastAPI UploadFile stream
        my_army.file.close()
        enemy_army.file.close()

    

@app.get("/report/{job_id}", dependencies=[Depends(verify_clerk_user)])
def get_report(job_id: str):
    job = JOBS.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="unknown job id")
    return job   # {"status": "pending"}  or  {"status": "done", "report": "..."}
   
@app.get("/config")  
def get_config() -> dict[str, str]:
    settings = get_settings()
    return {
        "clerk_publishable_key": settings.clerk_publishable_key
    }

def process_report(job_id: str, my_army: Army, enemy_army: Army, dry_run: bool = False) -> None:
    try:
        report = build_full_report(my_army=my_army, enemy_army=enemy_army, dry_run=dry_run)
        JOBS[job_id] = {"status": "done", "report": report}
    except ValueError as e:
        JOBS[job_id] = {"status": "failed", "error": str(e)}



# @cache makes this lazy: the Clerk client is built on first call, not at import.
# If instead we had `clerk = Clerk(bearer_auth=os.environ["CLERK_SECRET_KEY"])` at
# module top-level, just importing this module would construct it — and crash without
# a .env. Lazy loading means tests can import the module with no secrets present.
@cache
def get_clerk() -> Clerk:
   settings = get_settings()
   return Clerk(bearer_auth=settings.clerk_secret_key.get_secret_value())

def main() -> None:
    uvicorn.run("tabletop_tactician.api.main:app", host="127.0.0.1", port=8000, reload=True, log_level="info")



if __name__ == "__main__":
    main()
