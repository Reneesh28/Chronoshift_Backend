from pydantic import BaseModel, Field
from typing import List, Dict

# REQUEST SCHEMAS

class SimulationRunRequest(BaseModel):
    timeline_id: str = Field(..., description="The ObjectId string of the root timeline")
    branch_id: str = Field(..., description="The ObjectId string of the starting parent branch")
    decision: str = Field(..., description="The decision text to base the simulation on")

# RESPONSE SCHEMAS

class SimulationRunResponse(BaseModel):
    simulation_id: str = Field(..., description="The ObjectId string of the created simulation record")
    status: str = Field("simulation_started", description="Status code of the started simulation")

class SimulationStatusResponse(BaseModel):
    simulation_id: str = Field(..., description="The ObjectId string of the requested simulation")
    status: str = Field(..., description="Lifecycle status of simulation (queued, processing, completed, failed)")
    progress: int = Field(..., ge=0, le=100, description="Completion percentage (0 to 100)")

class SimulationResultResponse(BaseModel):
    simulation_id: str = Field(..., description="The ObjectId string of the requested simulation")
    generated_branches: List[str] = Field(..., description="List of generated branch ObjectId strings")
    divergence_scores: Dict[str, float] = Field(..., description="Divergence scores mapped by branch ObjectId")

# ERROR SCHEMAS

class ErrorResponse(BaseModel):
    error: bool = Field(True, description="Indicates if an error occurred")
    message: str = Field(..., description="Human-readable explanation of the error")
    code: str = Field(..., description="ChronoShift standard error code string")
