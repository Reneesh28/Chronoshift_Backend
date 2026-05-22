import sys
from pathlib import Path

# Resolve fastapi_simulator path and inject into sys.path to enable smooth microservice module resolution
SERVICE_DIR = str(Path(__file__).resolve().parent)
if SERVICE_DIR not in sys.path:
    sys.path.insert(0, SERVICE_DIR)

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from routes import router

# ==========================================================
# FASTAPI APP INSTANTIATION
# ==========================================================

app = FastAPI(
    title="ChronoShift Realtime Simulation Engine",
    description="Asynchronous distributed engine responsible for parallel futures branching and divergence calculations.",
    version="1.0.0"
)

# ==========================================================
# CORS MIDDLWARE CONFIGURATION
# ==========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permits all origins for simplified MVP local dev integrations
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================================
# GLOBAL CUSTOM EXCEPTION HANDLERS
# ==========================================================

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    Intercepts Pydantic validation errors and reformats them to align with 
    the standard ChronoShift JSON error specification.
    """
    errors_summary = []
    for error in exc.errors():
        field_path = " -> ".join(str(p) for p in error.get("loc", []))
        message = error.get("msg", "Validation error")
        errors_summary.append(f"[{field_path}]: {message}")
        
    readable_errors = "; ".join(errors_summary)
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": True,
            "message": f"Validation failed: {readable_errors}",
            "code": "INVALID_REQUEST"
        }
    )

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    Intercepts standard HTTPExceptions and serializes them in ChronoShift structure.
    """
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.detail,
            "code": "SIMULATION_ERROR"
        }
    )

@app.exception_handler(Exception)
async def global_generic_exception_handler(request: Request, exc: Exception):
    """
    Catches any unhandled generic server errors to prevent HTML traceback prints,
    returning structured JSON reports.
    """
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": f"An unexpected server error occurred: {str(exc)}",
            "code": "SIMULATION_ERROR"
        }
    )

# ==========================================================
# MOUNT BLUEPRINTS & ROOT ROUTES
# ==========================================================

app.include_router(router)

@app.get("/")
def root():
    """
    Returns application metadata and status.
    """
    return {
        "app": "ChronoShift Simulation Engine",
        "version": "1.0.0",
        "status": "online"
    }
