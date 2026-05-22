import json
import asyncio
import random
from datetime import datetime
from bson import ObjectId
from config import (
    simulations_collection,
    branches_collection,
    timelines_collection
)

async def run_simulation_task(simulation_id: str, timeline_id: str, branch_id: str, decision: str):
    """
    Simulates timeline futures asynchronously:
    1. Updates simulation status to 'processing' (0%).
    2. Increments progress progressively from 0 to 100.
    3. Fetches parent branch hierarchy details.
    4. Generates 2 alternative scenario branches with random divergence scores [0.3, 0.9].
    5. Persists new branch records in MongoDB Atlas.
    6. Emits structured JSON logs representing WebSocket event streams.
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
        print(json.dumps({
            "event": "simulation_updated",
            "simulation_id": simulation_id,
            "progress": 0,
            "status": "processing"
        }))
        
        # Step 2: Simulate dynamic progressive increments (20%, 40%, 60%, 80%)
        for prog in [20, 40, 60, 80]:
            await asyncio.sleep(0.5)  # 0.5s pause to mimic computation
            
            simulations_collection.update_one(
                {"_id": ObjectId(simulation_id)},
                {"$set": {"progress": prog}}
            )
            
            print(json.dumps({
                "event": "simulation_updated",
                "simulation_id": simulation_id,
                "progress": prog,
                "status": "processing"
            }))
            
        # Step 3: Fetch parent branch details to determine depth level
        parent_depth = 1
        try:
            parent_branch = branches_collection.find_one({"_id": ObjectId(branch_id)})
            if parent_branch:
                parent_depth = parent_branch.get("depth_level", 1)
        except Exception as e:
            print(f"[WARNING] Could not resolve parent branch {branch_id} hierarchy depth: {e}")
            
        # Step 4: Generate heuristic divergence scores & alternative branches
        await asyncio.sleep(0.5)  # Pause before finalizing
        
        div1 = round(random.uniform(0.3, 0.9), 2)
        div2 = round(random.uniform(0.3, 0.9), 2)
        
        # Scenario Alpha
        branch1_data = {
            "timeline_id": timeline_id,
            "parent_branch_id": branch_id,
            "branch_name": f"Alternative Alpha: {decision[:40]}",
            "decision_trigger": decision,
            "divergence_score": div1,
            "depth_level": parent_depth + 1,
            "status": "active",
            "created_at": datetime.utcnow()
        }
        res1 = branches_collection.insert_one(branch1_data)
        br1_id = str(res1.inserted_id)
        
        # Scenario Beta
        branch2_data = {
            "timeline_id": timeline_id,
            "parent_branch_id": branch_id,
            "branch_name": f"Alternative Beta: {decision[:40]}",
            "decision_trigger": decision,
            "divergence_score": div2,
            "depth_level": parent_depth + 1,
            "status": "active",
            "created_at": datetime.utcnow()
        }
        res2 = branches_collection.insert_one(branch2_data)
        br2_id = str(res2.inserted_id)
        
        # Step 5: Emit WebSocket-compliant JSON outputs for branch creations
        timestamp_str = datetime.utcnow().isoformat() + "Z"
        print(json.dumps({
            "event": "branch_created",
            "timeline_id": timeline_id,
            "branch_id": br1_id,
            "parent_branch_id": branch_id,
            "divergence_score": div1,
            "timestamp": timestamp_str
        }))
        print(json.dumps({
            "event": "branch_created",
            "timeline_id": timeline_id,
            "branch_id": br2_id,
            "parent_branch_id": branch_id,
            "divergence_score": div2,
            "timestamp": timestamp_str
        }))
        
        # Emit divergence changed events
        print(json.dumps({
            "event": "divergence_changed",
            "branch_id": br1_id,
            "divergence_score": div1
        }))
        print(json.dumps({
            "event": "divergence_changed",
            "branch_id": br2_id,
            "divergence_score": div2
        }))
        
        # Step 6: Finalize Simulation Record in DB
        simulations_collection.update_one(
            {"_id": ObjectId(simulation_id)},
            {
                "$set": {
                    "simulation_status": "completed",
                    "progress": 100,
                    "generated_branch_ids": [br1_id, br2_id],
                    "divergence_results": {br1_id: div1, br2_id: div2},
                    "completed_at": datetime.utcnow()
                }
            }
        )
        
        # Emit simulation completed events
        print(json.dumps({
            "event": "simulation_updated",
            "simulation_id": simulation_id,
            "progress": 100,
            "status": "completed"
        }))
        print(json.dumps({
            "event": "simulation_completed",
            "simulation_id": simulation_id,
            "generated_branches": [br1_id, br2_id]
        }))
        
        print(f"[SIMULATION COMPLETED] Simulation {simulation_id} resolved successfully.")
        
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
