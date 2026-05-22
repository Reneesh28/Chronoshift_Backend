from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import JSONResponse
from bson import ObjectId
from bson.errors import InvalidId
from datetime import datetime

from config import (
    simulations_collection,
    timelines_collection,
    branches_collection
)
from schemas import (
    SimulationRunRequest,
    SimulationRunResponse,
    SimulationStatusResponse,
    SimulationResultResponse,
    ErrorResponse
)
from services import run_simulation_task

router = APIRouter(prefix="/simulate", tags=["Simulation"])

# HEALTH CHECK
@router.get("/health", response_model=dict)
def health_check():
    """
    Returns a lightweight service status report.
    """
    return {
        "service": "fastapi_simulator",
        "status": "running"
    }

# START SIMULATION
@router.post("/run", response_model=SimulationRunResponse, status_code=status.HTTP_202_ACCEPTED)
def run_simulation(request: SimulationRunRequest, background_tasks: BackgroundTasks):
    """
    Triggers timeline future branches simulation asynchronously.
    """
    try:
        # Validate inputs formats
        timeline_id_obj = ObjectId(request.timeline_id)
    except InvalidId:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": True,
                "message": "Invalid timeline_id format",
                "code": "INVALID_REQUEST"
            }
        )

    branch_id_obj = None
    if request.branch_id != "root":
        try:
            branch_id_obj = ObjectId(request.branch_id)
        except InvalidId:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": True,
                    "message": "Invalid branch_id format",
                    "code": "INVALID_REQUEST"
                }
            )

    # Verify that timeline and parent branch exist before launching
    timeline = timelines_collection.find_one({"_id": timeline_id_obj})
    if not timeline:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": True,
                "message": "Timeline not found",
                "code": "TIMELINE_NOT_FOUND"
            }
        )

    if branch_id_obj:
        parent_branch = branches_collection.find_one({"_id": branch_id_obj})
        if not parent_branch:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "error": True,
                    "message": "Parent branch not found",
                    "code": "BRANCH_NOT_FOUND"
                }
            )

    # Check for existing "queued" simulation placeholder for this timeline/branch
    existing_sim = simulations_collection.find_one({
        "timeline_id": request.timeline_id,
        "source_branch_id": request.branch_id,
        "simulation_status": "queued"
    })

    if existing_sim:
        simulation_id = str(existing_sim["_id"])
    else:
        # Create a new simulation record if none exists
        sim_data = {
            "timeline_id": request.timeline_id,
            "source_branch_id": request.branch_id,
            "generated_branch_ids": [],
            "simulation_status": "queued",
            "progress": 0,
            "divergence_results": {},
            "started_at": datetime.utcnow(),
            "completed_at": None
        }
        result = simulations_collection.insert_one(sim_data)
        simulation_id = str(result.inserted_id)

    # Dispatch to background task execution queue
    background_tasks.add_task(
        run_simulation_task,
        simulation_id=simulation_id,
        timeline_id=request.timeline_id,
        branch_id=request.branch_id,
        decision=request.decision
    )

    return SimulationRunResponse(
        simulation_id=simulation_id,
        status="simulation_started"
    )

# GET SIMULATION STATUS

@router.get("/status/{simulation_id}", response_model=SimulationStatusResponse)
def get_simulation_status(simulation_id: str):
    """
    Retrieves the current progress percentage and lifecycle state of a simulation.
    """
    try:
        sim_id_obj = ObjectId(simulation_id)
    except InvalidId:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": True,
                "message": "Invalid simulation_id format",
                "code": "INVALID_REQUEST"
            }
        )

    sim = simulations_collection.find_one({"_id": sim_id_obj})
    if not sim:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": True,
                "message": "Simulation not found",
                "code": "SIMULATION_ERROR"
            }
        )

    return SimulationStatusResponse(
        simulation_id=str(sim["_id"]),
        status=sim.get("simulation_status", "queued"),
        progress=sim.get("progress", 0)
    )

# GET SIMULATION RESULT

@router.get("/result/{simulation_id}", response_model=SimulationResultResponse)
def get_simulation_result(simulation_id: str):
    """
    Retrieves the alternative branch IDs and divergence score maps of a completed simulation.
    """
    try:
        sim_id_obj = ObjectId(simulation_id)
    except InvalidId:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": True,
                "message": "Invalid simulation_id format",
                "code": "INVALID_REQUEST"
            }
        )

    sim = simulations_collection.find_one({"_id": sim_id_obj})
    if not sim:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": True,
                "message": "Simulation not found",
                "code": "SIMULATION_ERROR"
            }
        )

    status_str = sim.get("simulation_status", "")
    if status_str != "completed":
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": True,
                "message": f"Simulation is not completed. Current status: '{status_str}'",
                "code": "SIMULATION_ERROR"
            }
        )

    return SimulationResultResponse(
        simulation_id=str(sim["_id"]),
        generated_branches=sim.get("generated_branch_ids", []),
        divergence_scores=sim.get("divergence_results", {})
    )
