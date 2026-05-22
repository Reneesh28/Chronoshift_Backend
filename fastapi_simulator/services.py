import json
import asyncio
import random
from datetime import datetime
from bson import ObjectId
import httpx
from config import (
    simulations_collection,
    branches_collection,
    timelines_collection
)

# ==========================================================
# BRANCH ARCHETYPE DEFINITIONS
# ==========================================================

BRANCH_ARCHETYPES = [
    {
        "key": "stable_growth",
        "label": "Controlled Expansion",
        "prefix": "Stable Growth",
        "divergence_range": (0.30, 0.50),
    },
    {
        "key": "high_risk_growth",
        "label": "Hypergrowth Scenario",
        "prefix": "High Risk",
        "divergence_range": (0.51, 0.75),
    },
    {
        "key": "systemic_collapse",
        "label": "Operational Collapse",
        "prefix": "Systemic Collapse",
        "divergence_range": (0.76, 0.95),
    },
]


def _build_branch_name(archetype: dict, decision: str) -> str:
    """
    Generates a human-readable branch name that combines
    the archetype label with a truncated decision context.
    """
    decision_short = decision.strip()[:40]
    return f"{archetype['prefix']}: {decision_short}"


async def emit_websocket_event(timeline_id: str, payload: dict):
    """
    Issues a non-blocking asynchronous HTTP POST request to Django's WebSocket
    broadcast bridge to relay events to the React client in real-time.
    """
    url = "http://localhost:8000/api/timelines/broadcast/"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "timeline_id": timeline_id,
                    "payload": payload
                },
                timeout=2.0
            )
            if response.status_code != 200:
                print(f"[WS EMITTER WARNING] Django broadcast returned status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[WS EMITTER ERROR] Failed to emit WebSocket event over bridge: {e}")


async def trigger_ai_summary(timeline_id: str, branch_id: str, simulation_id: str):
    """
    Fires an asynchronous POST to the Flask AI Engine to pre-generate
    a full timeline report for a specific branch. This runs in background
    so the user sees reports immediately when they click a node.
    """
    url = "http://localhost:8003/ai/generate-summary"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "timeline_id": timeline_id,
                    "branch_id": branch_id,
                    "simulation_id": simulation_id
                },
                timeout=15.0
            )
            if response.status_code == 200:
                print(f"[AI TRIGGER] Summary pre-generated for branch {branch_id}")
            else:
                print(f"[AI TRIGGER WARNING] Flask AI returned {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[AI TRIGGER ERROR] Could not reach Flask AI Engine for branch {branch_id}: {e}")


async def run_simulation_task(simulation_id: str, timeline_id: str, branch_id: str, decision: str):
    """
    Simulates timeline futures asynchronously:
    1. Updates simulation status to 'processing' (0%).
    2. Increments progress progressively from 0 to 100.
    3. Fetches parent branch hierarchy details.
    4. Generates 3 alternative scenario branches with archetype-aware divergence scores.
    5. Persists new branch records in MongoDB Atlas.
    6. Emits structured JSON logs representing WebSocket event streams.
    7. Auto-triggers Flask AI Engine to pre-generate reports for each branch.
    """
    print(f"\n[SIMULATION START] Starting simulation {simulation_id} for timeline {timeline_id} derived from branch {branch_id}")
    
    try:
        # Step 1: Transition status to processing
        simulations_collection.update_one(
            {"_id": ObjectId(simulation_id)},
            {
                "$set": {
                    "simulation_status": "processing",
                    "progress": 0,
                    "started_at": datetime.utcnow()
                }
            }
        )
        
        # Emit initial processing event
        await emit_websocket_event(timeline_id, {
            "event": "simulation_updated",
            "simulation_id": simulation_id,
            "progress": 0,
            "status": "processing"
        })
        
        # Step 2: Simulate dynamic progressive increments (20%, 40%, 60%, 80%)
        for prog in [20, 40, 60, 80]:
            await asyncio.sleep(0.5)  # 0.5s pause to mimic computation
            
            simulations_collection.update_one(
                {"_id": ObjectId(simulation_id)},
                {"$set": {"progress": prog}}
            )
            
            await emit_websocket_event(timeline_id, {
                "event": "simulation_updated",
                "simulation_id": simulation_id,
                "progress": prog,
                "status": "processing"
            })
            
        # Step 3: Fetch parent branch details to determine depth level
        parent_depth = 1
        try:
            parent_branch = branches_collection.find_one({"_id": ObjectId(branch_id)})
            if parent_branch:
                parent_depth = parent_branch.get("depth_level", 1)
        except Exception as e:
            print(f"[WARNING] Could not resolve parent branch {branch_id} hierarchy depth: {e}")
            
        # Step 4: Generate 3 archetype-driven branches
        await asyncio.sleep(0.5)  # Pause before finalizing
        
        generated_branch_ids = []
        divergence_map = {}
        timestamp_str = datetime.utcnow().isoformat() + "Z"

        for archetype in BRANCH_ARCHETYPES:
            low, high = archetype["divergence_range"]
            div_score = round(random.uniform(low, high), 2)
            
            branch_data = {
                "timeline_id": timeline_id,
                "parent_branch_id": branch_id,
                "branch_name": _build_branch_name(archetype, decision),
                "branch_type": archetype["key"],
                "decision_trigger": decision,
                "divergence_score": div_score,
                "depth_level": parent_depth + 1,
                "status": "active",
                "created_at": datetime.utcnow()
            }
            result = branches_collection.insert_one(branch_data)
            br_id = str(result.inserted_id)
            
            generated_branch_ids.append(br_id)
            divergence_map[br_id] = div_score
            
            # Emit branch creation event
            await emit_websocket_event(timeline_id, {
                "event": "branch_created",
                "timeline_id": timeline_id,
                "branch_id": br_id,
                "parent_branch_id": branch_id,
                "branch_type": archetype["key"],
                "divergence_score": div_score,
                "timestamp": timestamp_str
            })
            
            # Emit divergence event
            await emit_websocket_event(timeline_id, {
                "event": "divergence_changed",
                "branch_id": br_id,
                "divergence_score": div_score
            })

        # Step 5: Finalize Simulation Record in DB
        simulations_collection.update_one(
            {"_id": ObjectId(simulation_id)},
            {
                "$set": {
                    "simulation_status": "completed",
                    "progress": 100,
                    "generated_branch_ids": generated_branch_ids,
                    "divergence_results": divergence_map,
                    "completed_at": datetime.utcnow()
                }
            }
        )
        
        # Emit simulation completed events
        await emit_websocket_event(timeline_id, {
            "event": "simulation_updated",
            "simulation_id": simulation_id,
            "progress": 100,
            "status": "completed"
        })
        await emit_websocket_event(timeline_id, {
            "event": "simulation_completed",
            "simulation_id": simulation_id,
            "generated_branches": generated_branch_ids
        })
        
        print(f"[SIMULATION COMPLETED] Simulation {simulation_id} resolved successfully with {len(generated_branch_ids)} branches.")

        # Step 6: Auto-trigger Flask AI Engine for each generated branch
        print(f"[AI PRE-GENERATION] Triggering narrative reports for {len(generated_branch_ids)} branches...")
        ai_tasks = [
            trigger_ai_summary(timeline_id, br_id, simulation_id)
            for br_id in generated_branch_ids
        ]
        await asyncio.gather(*ai_tasks, return_exceptions=True)
        print(f"[AI PRE-GENERATION] All narrative reports dispatched.")
        
    except Exception as err:
        print(f"[SIMULATION ERROR] Simulation task {simulation_id} failed: {err}")
        try:
            simulations_collection.update_one(
                {"_id": ObjectId(simulation_id)},
                {
                    "$set": {
                        "simulation_status": "failed",
                        "completed_at": datetime.utcnow()
                    }
                }
            )
        except Exception as db_err:
            print(f"[DATABASE ERROR] Failed to flag simulation failure: {db_err}")
