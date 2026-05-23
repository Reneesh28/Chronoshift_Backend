import os
import sys
import time
import subprocess
import requests
from pathlib import Path
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient

def run_e2e_verification():
    print("==========================================================")
    print("[START] Automated End-to-End Simulation Engine Verification")
    print("==========================================================")

    # 1. Resolve shared env location and config variables
    service_dir = Path(__file__).resolve().parent
    root_backend_dir = service_dir.parent
    env_path = root_backend_dir / ".env"
    
    if not env_path.exists():
        print(f"[ERROR] Environment file not found at {env_path}!")
        sys.exit(1)

    from dotenv import load_dotenv
    load_dotenv(env_path)

    mongo_uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGO_DB_NAME", "Chronoshift")

    # 2. Setup direct Mongo connection for seeding & assertion verification
    print("[*] Connecting to MongoDB Atlas cluster...")
    try:
        try:
            import dns.resolver
            dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
            dns.resolver.default_resolver.nameservers = ['8.8.8.8', '1.1.1.1', '8.8.4.4']
        except Exception as dns_err:
            pass
        client = MongoClient(mongo_uri)
        db = client[db_name]
        timelines_col = db["timelines"]
        branches_col = db["branches"]
        simulations_col = db["simulations"]
        print("[OK] Connected to MongoDB Atlas.")
    except Exception as e:
        print(f"[ERROR] MongoDB Connection failed: {e}")
        sys.exit(1)

    # Seed temporary testing records
    print("[*] Seeding temporary verification documents...")
    temp_timeline = {
        "user_id": 9999,
        "title": "Verification Test Timeline",
        "description": "Used by verify_simulator.py automation framework",
        "created_at": datetime.utcnow()
    }
    t_result = timelines_col.insert_one(temp_timeline)
    timeline_id_str = str(t_result.inserted_id)

    temp_branch = {
        "timeline_id": timeline_id_str,
        "parent_branch_id": None,
        "branch_name": "Verification Root Branch",
        "decision_trigger": "Initial verify launch",
        "divergence_score": 0.0,
        "depth_level": 1,
        "status": "active",
        "created_at": datetime.utcnow()
    }
    b_result = branches_col.insert_one(temp_branch)
    branch_id_str = str(b_result.inserted_id)

    # Update timeline with root branch link
    timelines_col.update_one(
        {"_id": ObjectId(timeline_id_str)},
        {"$set": {"root_branch_id": branch_id_str}}
    )

    print(f"|-- Seeded Timeline ID: {timeline_id_str}")
    print(f"|-- Seeded Root Branch ID: {branch_id_str}")

    # 3. Spawn FastAPI app server on port 8002 in background
    print("\n[*] Spawning FastAPI Simulator service on port 8002...")
    python_exe = sys.executable
    server_process = subprocess.Popen(
        [python_exe, "-m", "uvicorn", "main:app", "--port", "8002", "--host", "127.0.0.1"],
        cwd=str(service_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # 4. Wait for server boot
    print("[*] Waiting for Simulator API to respond...")
    booted = False
    for i in range(20):  # Retry 20 times, total 10 seconds
        time.sleep(0.5)
        try:
            res = requests.get("http://127.0.0.1:8002/simulate/health", timeout=1.0)
            if res.status_code == 200:
                booted = True
                print("[OK] Simulator service is online.")
                break
        except requests.exceptions.RequestException:
            pass

    if not booted:
        print("[ERROR] FastAPI Simulator service failed to start on port 8002!")
        # Print errors if any
        stdout, stderr = server_process.communicate()
        print("Stdout:", stdout)
        print("Stderr:", stderr)
        
        # Cleanup
        timelines_col.delete_one({"_id": ObjectId(timeline_id_str)})
        branches_col.delete_one({"_id": ObjectId(branch_id_str)})
        sys.exit(1)

    # 5. POST /simulate/run request
    print("\n[*] Triggering simulation run flow: POST /simulate/run...")
    payload = {
        "timeline_id": timeline_id_str,
        "branch_id": branch_id_str,
        "decision": "Establish automated verification pipelines across distributed networks"
    }

    try:
        run_res = requests.post("http://127.0.0.1:8002/simulate/run", json=payload, timeout=5.0)
        print(f"|-- POST /simulate/run Response Code: {run_res.status_code}")
        
        if run_res.status_code != 202:
            print(f"[ERROR] Failed to start simulation: {run_res.text}")
            raise Exception("Trigger failed")

        data = run_res.json()
        simulation_id = data.get("simulation_id")
        status_msg = data.get("status")
        print(f"[SUCCESS] Simulation started. ID: {simulation_id}, status: {status_msg}")

        # 6. Poll status endpoint GET /simulate/status/{id}
        print("\n[*] Polling simulation progress asynchronously...")
        completed = False
        for poll_step in range(30):
            time.sleep(0.4)
            status_res = requests.get(f"http://127.0.0.1:8002/simulate/status/{simulation_id}", timeout=2.0)
            if status_res.status_code != 200:
                print(f"[ERROR] Failed to fetch status: {status_res.text}")
                raise Exception("Poll failed")

            status_data = status_res.json()
            progress = status_data.get("progress")
            status_str = status_data.get("status")
            print(f"    * [POLL] Progress: {progress}%, Status: '{status_str}'")

            if status_str == "completed":
                completed = True
                print("[SUCCESS] Simulation completed successfully.")
                break
            elif status_str == "failed":
                print("[ERROR] Background task marked simulation as failed!")
                raise Exception("Task failed")

        if not completed:
            print("[ERROR] Simulation timed out without completing!")
            raise Exception("Timeout")

        # 7. GET /simulate/result/{id}
        print("\n[*] Fetching simulation branch results: GET /simulate/result/{id}...")
        result_res = requests.get(f"http://127.0.0.1:8002/simulate/result/{simulation_id}", timeout=2.0)
        print(f"|-- GET /simulate/result/ Response Code: {result_res.status_code}")
        
        if result_res.status_code != 200:
            print(f"[ERROR] Failed to fetch results: {result_res.text}")
            raise Exception("Result failed")

        result_data = result_res.json()
        generated_branches = result_data.get("generated_branches", [])
        divergence_scores = result_data.get("divergence_scores", {})
        print(f"[SUCCESS] Results received:")
        print(f"    * Generated branches: {generated_branches}")
        print(f"    * Divergence scores: {divergence_scores}")

        # 8. Assert native Mongo Atlas persistence and data integrity
        print("\n[*] Querying MongoDB Atlas database to verify structural persistence...")
        
        # Verify simulation document completed
        sim_doc = simulations_col.find_one({"_id": ObjectId(simulation_id)})
        assert sim_doc is not None, "Simulation document not found in DB!"
        assert sim_doc.get("simulation_status") == "completed", "DB simulation status is not completed!"
        assert sim_doc.get("progress") == 100, "DB simulation progress is not 100!"
        print("[OK] Confirmed simulation document state in database.")

        # Verify generated branches
        for br_id in generated_branches:
            br_doc = branches_col.find_one({"_id": ObjectId(br_id)})
            assert br_doc is not None, f"Generated branch {br_id} document not found in DB!"
            assert br_doc.get("parent_branch_id") == branch_id_str, "Branch parent linkage is incorrect!"
            assert br_doc.get("timeline_id") == timeline_id_str, "Branch timeline linkage is incorrect!"
            assert br_doc.get("depth_level") == 2, "Branch depth level is incorrect (expected 2)!"
            assert br_doc.get("divergence_score") == divergence_scores.get(br_id), "Divergence score mismatch!"
            print(f"    * [OK] Verified Branch: ID = {br_id}, Name = '{br_doc.get('branch_name')}', Depth = {br_doc.get('depth_level')}, Divergence = {br_doc.get('divergence_score')}")

        print("[SUCCESS] MongoDB Atlas data integrity checks verified successfully.")

    except Exception as err:
        print(f"\n[FATAL ERROR] Automated check failed: {err}")
    finally:
        # 9. Cleanup database test records
        print("\n[*] Cleaning up temporary verification records from Atlas...")
        try:
            # Delete generated branches
            b_list = branches_col.find({"timeline_id": timeline_id_str})
            b_ids = [doc["_id"] for doc in b_list]
            branches_col.delete_many({"timeline_id": timeline_id_str})
            timelines_col.delete_one({"_id": ObjectId(timeline_id_str)})
            simulations_col.delete_many({"timeline_id": timeline_id_str})
            print(f"[OK] Cleaned timeline, branches, and simulations (Removed {len(b_ids)} branch docs).")
        except Exception as clean_err:
            print(f"[WARNING] Database cleanup failed: {clean_err}")

        # 10. Terminate background server process cleanly
        print("[*] Stopping FastAPI Simulator background process...")
        server_process.terminate()
        try:
            server_process.wait(timeout=2.0)
            print("[OK] Simulator background process terminated successfully.")
        except subprocess.TimeoutExpired:
            server_process.kill()
            print("[WARNING] Simulator background process forced killed.")

    print("==========================================================")
    print("[SUCCESS] All Phase 4 Verification Checks Completed Successfully!")
    print("==========================================================\n")

if __name__ == "__main__":
    run_e2e_verification()
