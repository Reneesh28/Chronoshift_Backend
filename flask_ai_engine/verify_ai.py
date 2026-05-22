import os
import sys
import time
import subprocess
import requests
from pathlib import Path
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient

def run_ai_e2e_verification():
    print("==========================================================")
    print("[START] Automated End-to-End Flask AI Engine Verification")
    print("==========================================================")

    # 1. Resolve shared env location and config variables
    service_dir = Path(__file__).resolve().parent
    root_backend_dir = service_dir.parent
    env_path = root_backend_dir / ".env"
    
    if not env_path.exists():
        print(f"[ERROR] Shared environment file not found at {env_path}!")
        sys.exit(1)

    from dotenv import load_dotenv
    load_dotenv(env_path)

    mongo_uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGO_DB_NAME", "Chronoshift")

    # 2. Setup direct Mongo connection for seeding & assertion verification
    print("[*] Connecting to MongoDB Atlas cluster...")
    try:
        client = MongoClient(mongo_uri)
        db = client[db_name]
        timelines_col = db["timelines"]
        branches_col = db["branches"]
        simulations_col = db["simulations"]
        summaries_col = db["ai_summaries"]
        print("[OK] Connected to MongoDB Atlas.")
    except Exception as e:
        print(f"[ERROR] MongoDB Connection failed: {e}")
        sys.exit(1)

    # Seed temporary testing records
    print("[*] Seeding temporary verification documents...")
    temp_timeline = {
        "user_id": 8888,
        "title": "Automated AI Verification Timeline",
        "description": "Validating LangChain & Hugging Face pipeline integration",
        "created_at": datetime.utcnow()
    }
    t_result = timelines_col.insert_one(temp_timeline)
    timeline_id_str = str(t_result.inserted_id)

    temp_branch = {
        "timeline_id": timeline_id_str,
        "parent_branch_id": None,
        "branch_name": "AI Verification Baseline Branch",
        "decision_trigger": "Launch overseas marketing operations and expand headcount",
        "divergence_score": 0.65,
        "depth_level": 2,
        "status": "active",
        "created_at": datetime.utcnow()
    }
    b_result = branches_col.insert_one(temp_branch)
    branch_id_str = str(b_result.inserted_id)

    temp_simulation = {
        "timeline_id": timeline_id_str,
        "source_branch_id": branch_id_str,
        "generated_branch_ids": [branch_id_str],
        "simulation_status": "completed",
        "progress": 100,
        "divergence_results": {branch_id_str: 0.65},
        "started_at": datetime.utcnow(),
        "completed_at": datetime.utcnow()
    }
    s_result = simulations_col.insert_one(temp_simulation)
    simulation_id_str = str(s_result.inserted_id)

    print(f"|-- Seeded Timeline ID: {timeline_id_str}")
    print(f"|-- Seeded Branch ID: {branch_id_str}")
    print(f"|-- Seeded Simulation ID: {simulation_id_str}")

    # 3. Spawn Flask AI Engine app server on port 8003 in background
    print("\n[*] Spawning Flask AI service on port 8003...")
    python_exe = sys.executable
    server_process = subprocess.Popen(
        [python_exe, "main.py"],
        cwd=str(service_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    # 4. Wait for server boot
    print("[*] Waiting for Flask AI service to respond...")
    booted = False
    for i in range(20):  # Retry 20 times, total 10 seconds
        time.sleep(0.5)
        try:
            res = requests.get("http://127.0.0.1:8003/ai/health", timeout=1.0)
            if res.status_code == 200:
                booted = True
                print("[OK] Flask AI Engine service is online.")
                break
        except requests.exceptions.RequestException:
            pass

    if not booted:
        print("[ERROR] Flask AI Engine service failed to start on port 8003!")
        # Cleanup seeded records
        timelines_col.delete_one({"_id": ObjectId(timeline_id_str)})
        branches_col.delete_one({"_id": ObjectId(branch_id_str)})
        simulations_col.delete_one({"_id": ObjectId(simulation_id_str)})
        server_process.terminate()
        sys.exit(1)

    try:
        # 5. POST /ai/generate-summary request
        print("\n[*] Triggering summary generation flow: POST /ai/generate-summary...")
        payload = {
            "timeline_id": timeline_id_str,
            "branch_id": branch_id_str,
            "simulation_id": simulation_id_str
        }

        run_res = requests.post("http://127.0.0.1:8003/ai/generate-summary", json=payload, timeout=10.0)
        print(f"|-- POST /ai/generate-summary Response Code: {run_res.status_code}")
        
        if run_res.status_code != 200:
            print(f"[ERROR] Summary generation endpoint failed: {run_res.text}")
            raise Exception("API Summary Generation failed")

        data = run_res.json()
        summary_id = data.get("summary_id")
        risk_score = data.get("risk_score")
        summary_text = data.get("summary")
        print(f"[SUCCESS] Summary generated cleanly.")
        print(f"    * Summary ID: {summary_id}")
        print(f"    * Calculated Heuristic Risk: {risk_score}")
        print(f"    * Text output: '{summary_text}'")

        # 6. Assert JSON response contract properties
        assert summary_id is not None, "Summary ID is missing in response!"
        assert risk_score is not None, "Risk score is missing in response!"
        assert summary_text is not None and len(summary_text) > 10, "Summary output is empty or too short!"
        print("[OK] Verified API JSON contract fields match.")

        # 7. Assert native MongoDB Atlas persistence and data integrity
        print("\n[*] Querying MongoDB Atlas database to verify structural persistence...")
        sum_doc = summaries_col.find_one({"_id": ObjectId(summary_id)})
        
        assert sum_doc is not None, "Summary document not found in database!"
        assert sum_doc.get("timeline_id") == timeline_id_str, "Summary timeline linkage mismatch!"
        assert sum_doc.get("branch_id") == branch_id_str, "Summary branch linkage mismatch!"
        assert sum_doc.get("simulation_id") == simulation_id_str, "Summary simulation linkage mismatch!"
        assert sum_doc.get("risk_score") == risk_score, "Summary risk score mismatch in DB!"
        assert sum_doc.get("confidence_score") is not None, "Summary confidence score is missing in DB!"
        assert sum_doc.get("summary") == summary_text, "Summary narrative text mismatch in DB!"
        print("[OK] Confirmed AI summary document state in MongoDB Atlas matches exactly.")

        # 8. GET /ai/summary/{id}
        print("\n[*] Fetching summary narrative: GET /ai/summary/{id}...")
        get_res = requests.get(f"http://127.0.0.1:8003/ai/summary/{summary_id}", timeout=2.0)
        print(f"|-- GET /ai/summary/ Response Code: {get_res.status_code}")
        
        if get_res.status_code != 200:
            print(f"[ERROR] Failed to fetch summary: {get_res.text}")
            raise Exception("API GET Summary failed")

        get_data = get_res.json()
        assert get_data.get("summary_id") == summary_id, "Fetched summary ID mismatch!"
        assert get_data.get("branch_id") == branch_id_str, "Fetched branch ID mismatch!"
        assert get_data.get("risk_score") == risk_score, "Fetched risk score mismatch!"
        assert get_data.get("summary") == summary_text, "Fetched narrative summary mismatch!"
        print("[OK] Verified GET /ai/summary endpoint matches payload exactly.")

    except Exception as err:
        print(f"\n[FATAL ERROR] Automated AI validation check failed: {err}")
    finally:
        # 9. Cleanup database test records
        print("\n[*] Cleaning up temporary verification records from Atlas...")
        try:
            timelines_col.delete_one({"_id": ObjectId(timeline_id_str)})
            branches_col.delete_one({"_id": ObjectId(branch_id_str)})
            simulations_col.delete_one({"_id": ObjectId(simulation_id_str)})
            summaries_col.delete_many({"timeline_id": timeline_id_str})
            print("[OK] Cleaned timelines, branches, simulations, and summaries documents successfully.")
        except Exception as clean_err:
            print(f"[WARNING] Database cleanup failed: {clean_err}")

        # 10. Terminate background server process cleanly
        print("[*] Stopping Flask AI Engine background process...")
        server_process.terminate()
        try:
            server_process.wait(timeout=2.0)
            print("[OK] Flask background process terminated successfully.")
        except subprocess.TimeoutExpired:
            server_process.kill()
            print("[WARNING] Flask background process forced killed.")

    print("[SUCCESS] All Phase 5 AI Engine Verification Checks Completed!")

if __name__ == "__main__":
    run_ai_e2e_verification()
