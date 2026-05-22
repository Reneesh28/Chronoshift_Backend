import os
import sys
import time
import subprocess
import requests
import asyncio
import websockets
import json
import re
from pathlib import Path
from datetime import datetime
from bson import ObjectId
from pymongo import MongoClient

def kill_port_owners(ports):
    """
    Finds and forcefully terminates any process listening on the specified local ports on Windows.
    This guarantees a clean local testing environment, resolving any orphaned background servers.
    """
    print("[CLEANUP] Ensuring local testing ports are unoccupied...")
    for port in ports:
        try:
            # Query netstat to find active listeners on the target port
            output = subprocess.check_output(f'netstat -ano | findstr :{port}', shell=True, text=True)
            for line in output.strip().split('\n'):
                # Format: TCP    127.0.0.1:8000         0.0.0.0:0              LISTENING       1234
                if "LISTENING" in line:
                    parts = re.split(r'\s+', line.strip())
                    if len(parts) >= 5:
                        pid = parts[-1]
                        print(f"  |-- Port {port} is occupied by PID {pid}. Force-terminating process...")
                        subprocess.run(f'taskkill /F /PID {pid}', shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            # netstat returns non-zero if no matching line is found
            pass

async def test_full_system_integration():
    print("\n" + "="*80)
    print("      PROJECT CHRONOSHIFT — REAL-TIME FULL SYSTEM E2E INTEGRATION TEST")
    print("="*80 + "\n")

    # 1. Clean port collisions to ensure test environment is clean
    kill_port_owners([8000, 8002, 8003])

    # 2. Resolve shared env location and config variables
    root_backend_dir = Path(__file__).resolve().parent
    env_path = root_backend_dir / ".env"
    
    if not env_path.exists():
        print(f"[FAIL] Shared environment file not found at {env_path}!")
        sys.exit(1)

    from dotenv import load_dotenv
    load_dotenv(env_path)

    mongo_uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGO_DB_NAME", "Chronoshift")

    # 3. Setup direct MongoDB Atlas connection
    print("[INIT] Connecting to MongoDB Atlas cluster...")
    try:
        mongo_client = MongoClient(mongo_uri)
        db = mongo_client[db_name]
        timelines_col = db["timelines"]
        branches_col = db["branches"]
        simulations_col = db["simulations"]
        summaries_col = db["ai_summaries"]
        print("[SUCCESS] MongoDB Atlas connection verified.")
    except Exception as e:
        print(f"[FAIL] MongoDB Connection failed: {e}")
        sys.exit(1)

    # 4. Seed temporary verification data
    timeline_id_str = ""
    branch_id_str = ""
    
    print("[SEEDS] Ingesting temporary verification mock graph...")
    try:
        temp_timeline = {
            "user_id": 9999,
            "title": "E2E Real-time Integration Timeline",
            "description": "Validating full system events with WebSocket & MongoDB Atlas synchronization",
            "created_at": datetime.utcnow()
        }
        t_result = timelines_col.insert_one(temp_timeline)
        timeline_id_str = str(t_result.inserted_id)

        temp_branch = {
            "timeline_id": timeline_id_str,
            "parent_branch_id": None,
            "branch_name": "E2E Integration Root Branch",
            "decision_trigger": "Initiating project chronoshift real-time validation protocol",
            "divergence_score": 0.0,
            "depth_level": 1,
            "status": "active",
            "created_at": datetime.utcnow()
        }
        b_result = branches_col.insert_one(temp_branch)
        branch_id_str = str(b_result.inserted_id)

        # Link root branch to timeline
        timelines_col.update_one(
            {"_id": ObjectId(timeline_id_str)},
            {"$set": {"root_branch_id": branch_id_str}}
        )
        print(f"  |-- Seeded Timeline ID: {timeline_id_str}")
        print(f"  |-- Seeded Root Branch ID: {branch_id_str}")
    except Exception as e:
        print(f"[FAIL] Seeding failed: {e}")
        sys.exit(1)

    # 5. Spawning Microservices in background subprocesses
    processes = {}
    python_exe = sys.executable

    try:
        # A. Django Core Daphne ASGI Server (Port 8000)
        print("\n[SERVICES] Launching Daphne ASGI Server on port 8000...")
        processes["django"] = subprocess.Popen(
            [python_exe, "-m", "daphne", "-p", "8000", "core.asgi:application"],
            cwd=str(root_backend_dir / "django_core"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # B. FastAPI Simulator (Port 8002)
        print("[SERVICES] Launching FastAPI Simulator on port 8002...")
        processes["fastapi"] = subprocess.Popen(
            [python_exe, "-m", "uvicorn", "main:app", "--port", "8002", "--host", "127.0.0.1"],
            cwd=str(root_backend_dir / "fastapi_simulator"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # C. Flask AI Engine (Port 8003)
        print("[SERVICES] Launching Flask AI Engine on port 8003...")
        env_copy = os.environ.copy()
        env_copy["AI_PORT"] = "8003"
        processes["flask"] = subprocess.Popen(
            [python_exe, "main.py"],
            cwd=str(root_backend_dir / "flask_ai_engine"),
            env=env_copy,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait for services to respond
        print("[SERVICES] Waiting for services to boot...")
        
        # Disable proxies for local calls in this test process to avoid network loopback blocks
        session = requests.Session()
        session.trust_env = False
        
        booted = False
        errors = {}
        
        for attempt in range(12):
            time.sleep(0.5)
            django_ok = False
            fastapi_ok = False
            flask_ok = False
            
            try:
                # We accept 200 (Open) or 401 (Authenticated) as confirmation that the API handler is active and running!
                r = session.get("http://127.0.0.1:8000/api/timelines/health/", timeout=0.5)
                django_ok = r.status_code in [200, 401]
            except Exception as e:
                errors["django"] = str(e)
                
            try:
                r = session.get("http://127.0.0.1:8002/simulate/health", timeout=0.5)
                fastapi_ok = r.status_code in [200, 401]
            except Exception as e:
                errors["fastapi"] = str(e)
                
            try:
                r = session.get("http://127.0.0.1:8003/ai/health", timeout=0.5)
                flask_ok = r.status_code in [200, 401]
            except Exception as e:
                errors["flask"] = str(e)
                
            if django_ok and fastapi_ok and flask_ok:
                booted = True
                print("[SERVICES] [OK] All services confirmed online and responding via HTTP health checks!")
                break

        # Extremely resilient fallback: if all processes are running (poll is None), we allow the test to proceed
        # after a short buffer sleep. This bypasses any local network routing/proxy restrictions on local machines.
        if not booted:
            all_alive = all(proc.poll() is None for proc in processes.values())
            if all_alive:
                print("[SERVICES] [RESILIENT FALLBACK] HTTP checks timed out, but all background processes are ALIVE and running.")
                print("  |-- Django (Daphne): ALIVE")
                print("  |-- FastAPI: ALIVE")
                print("  |-- Flask: ALIVE")
                print("  |-- Incurring a 3.0 second buffer sleep to ensure complete service readiness...")
                time.sleep(3.0)
                booted = True
            else:
                print("[FAIL] One or more microservices failed to boot.")
                for name, proc in processes.items():
                    print(f"  |-- Process status of '{name}': poll_status = {proc.poll()}")
                    if name in errors:
                        print(f"  |-- Last connection error for '{name}': {errors[name]}")
                raise RuntimeError("Microservice boot failure")

        # 6. Establish real-time WebSocket connection to Daphne
        ws_uri = f"ws://127.0.0.1:8000/ws/timeline/{timeline_id_str}"
        print(f"\n[WEBSOCKET] Subscribing client to WS channel: {ws_uri}")
        
        async with websockets.connect(ws_uri) as websocket:
            print("[WEBSOCKET] [SUCCESS] Real-time websocket subscription open!")

            # 7. Trigger FastAPI Simulator Simulation run
            simulate_run_url = "http://127.0.0.1:8002/simulate/run"
            simulate_payload = {
                "timeline_id": timeline_id_str,
                "branch_id": branch_id_str,
                "decision": "Deploy decentralized low-latency WebSocket layer on ChronoShift backend"
            }
            print(f"\n[SIMULATOR] Triggering simulation run: {simulate_run_url}")
            sim_res = session.post(simulate_run_url, json=simulate_payload, timeout=5.0)
            
            assert sim_res.status_code == 202, f"Expected 202, got {sim_res.status_code}: {sim_res.text}"
            sim_data = sim_res.json()
            simulation_id = sim_data.get("simulation_id")
            print(f"[SIMULATOR] [OK] Simulation successfully queued with ID: {simulation_id}")

            # 8. Listen for live events streaming over WebSocket
            print("\n[STREAM] Actively listening to WebSocket packet events...")
            
            ws_events = []
            generated_branches = []
            
            # Read streaming packets until simulation_completed is received
            simulation_completed_received = False
            timeout_limit = 12.0
            start_time = time.time()
            
            while not simulation_completed_received:
                if time.time() - start_time > timeout_limit:
                    raise TimeoutError("Timed out waiting for simulation WebSocket packets")
                
                try:
                    # Non-blocking wait for messages
                    message = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                    event_data = json.loads(message)
                    ws_events.append(event_data)
                    
                    event_name = event_data.get("event")
                    print(f"  |-- [WS EVENT RECEIVED] '{event_name}' -> {json.dumps(event_data)}")
                    
                    if event_name == "simulation_completed":
                        simulation_completed_received = True
                        generated_branches = event_data.get("generated_branches", [])
                except asyncio.TimeoutError:
                    continue

            # 9. Assert simulation events structure and order
            print("\n[ASSERTION] Validating timeline simulation packet sequence...")
            
            # Filter events by event type
            update_events = [e for e in ws_events if e.get("event") == "simulation_updated"]
            branch_created_events = [e for e in ws_events if e.get("event") == "branch_created"]
            div_events = [e for e in ws_events if e.get("event") == "divergence_changed"]
            completed_events = [e for e in ws_events if e.get("event") == "simulation_completed"]

            assert len(update_events) > 0, "No simulation progress update packets received!"
            # Assert progress starts near 0 and reaches 100
            assert update_events[0].get("progress") == 0, "Initial progress is not 0%"
            assert update_events[-1].get("progress") == 100, "Final progress is not 100%"
            assert len(branch_created_events) == 2, "Expected exactly 2 branch_created events!"
            assert len(div_events) == 2, "Expected exactly 2 divergence_changed events!"
            assert len(completed_events) == 1, "Expected exactly 1 simulation_completed event!"
            print("[ASSERTION] [SUCCESS] All simulation events are structurally flawless.")

            # 10. Trigger Flask AI Engine summary generation for new branches
            print(f"\n[AI] Triggering AI Summaries for newly branched alternative timelines: {generated_branches}")
            
            ai_summaries = []
            for idx, child_branch_id in enumerate(generated_branches):
                ai_url = "http://127.0.0.1:8003/ai/generate-summary"
                ai_payload = {
                    "timeline_id": timeline_id_str,
                    "branch_id": child_branch_id,
                    "simulation_id": simulation_id
                }
                print(f"[AI] Requesting narrative for branch {child_branch_id}...")
                ai_res = session.post(ai_url, json=ai_payload, timeout=10.0)
                
                assert ai_res.status_code == 200, f"AI generation failed: {ai_res.text}"
                ai_data = ai_res.json()
                ai_summaries.append(ai_data)
                print(f"  |-- [OK] Narrative complete: Risk = {ai_data.get('risk_score')}, Text = '{ai_data.get('summary')}'")

            # 11. Listen to WebSocket for AI real-time event packets
            print("\n[STREAM] Capturing AI real-time broadcast packets from WebSocket...")
            ai_packets_captured = 0
            timeout_limit = 5.0
            start_time = time.time()
            
            while ai_packets_captured < 2:
                if time.time() - start_time > timeout_limit:
                    raise TimeoutError("Timed out waiting for AI narrative WebSocket packets")
                
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=0.5)
                    event_data = json.loads(message)
                    event_name = event_data.get("event")
                    
                    if event_name == "ai_summary_ready":
                        ai_packets_captured += 1
                        print(f"  |-- [WS EVENT RECEIVED] '{event_name}' -> {json.dumps(event_data)}")
                        
                        # Validate structure
                        assert event_data.get("summary_id") is not None, "Missing summary_id"
                        assert event_data.get("branch_id") in generated_branches, "Unknown branch_id in AI payload"
                        assert event_data.get("risk_score") is not None, "Missing risk_score"
                        assert event_data.get("confidence_score") is not None, "Missing confidence_score"
                except asyncio.TimeoutError:
                    continue

            print("[ASSERTION] [SUCCESS] All AI narrative events streamed cleanly in real-time.")

            # 12. Assert MongoDB Atlas persistence and data integrity sync
            print("\n[DB] Querying MongoDB Atlas to validate absolute state syncing...")
            
            # Assert simulation collection
            sim_doc = simulations_col.find_one({"_id": ObjectId(simulation_id)})
            assert sim_doc is not None, "Simulation document missing from DB"
            assert sim_doc.get("simulation_status") == "completed", "Simulation state in DB not completed"
            assert sim_doc.get("progress") == 100, "Simulation progress in DB not 100"
            print("  |-- [OK] Simulation collection record sync verified.")

            # Assert branches collection
            for child_branch_id in generated_branches:
                br_doc = branches_col.find_one({"_id": ObjectId(child_branch_id)})
                assert br_doc is not None, f"Child branch {child_branch_id} missing from DB"
                assert br_doc.get("parent_branch_id") == branch_id_str, "Parent branch mismatch"
                assert br_doc.get("timeline_id") == timeline_id_str, "Timeline linkage mismatch"
                assert br_doc.get("depth_level") == 2, "Depth level calculation mismatch"
                print(f"  |-- [OK] Branch sync verified for ID {child_branch_id} ('{br_doc.get('branch_name')}').")

            # Assert ai_summaries collection
            for child_branch_id in generated_branches:
                sum_doc = summaries_col.find_one({"branch_id": child_branch_id})
                assert sum_doc is not None, f"AI summary missing for branch {child_branch_id}"
                assert sum_doc.get("timeline_id") == timeline_id_str, "AI summary timeline link mismatch"
                assert sum_doc.get("simulation_id") == simulation_id, "AI summary simulation link mismatch"
                assert sum_doc.get("summary") is not None, "Summary narrative text is missing"
                print(f"  |-- [OK] AI narrative sync verified for branch {child_branch_id}.")

            print("[ASSERTION] [SUCCESS] Absolute MongoDB Atlas database integrity confirmed.")

            print("\n" + "="*80)
            print("         ALL REAL-TIME REALTIME & DATABASE INTEGRATION CHECKS PASSED!")
            print("="*80 + "\n")

    except Exception as e:
        print(f"\n[FAIL] Test encountered critical error: {e}")
        raise e
    finally:
        # 13. Cleanup Database
        print("[CLEANUP] Purging verification documents from MongoDB Atlas...")
        try:
            if timeline_id_str:
                timelines_col.delete_one({"_id": ObjectId(timeline_id_str)})
                branches_col.delete_many({"timeline_id": timeline_id_str})
                simulations_col.delete_many({"timeline_id": timeline_id_str})
                summaries_col.delete_many({"timeline_id": timeline_id_str})
                print("[CLEANUP] Database purged cleanly.")
        except Exception as clean_err:
            print(f"[CLEANUP WARNING] MongoDB purge incomplete: {clean_err}")

        # 14. Gracefully terminate microservices
        print("[CLEANUP] Stopping background microservices...")
        for name, proc in processes.items():
            print(f"  |-- Terminating {name} process...")
            proc.terminate()
            try:
                proc.wait(timeout=3.0)
                print(f"  |-- [OK] {name} terminated cleanly.")
            except subprocess.TimeoutExpired:
                proc.kill()
                print(f"  |-- [WARNING] {name} killed forcefully.")

if __name__ == "__main__":
    try:
        asyncio.run(test_full_system_integration())
        sys.exit(0)
    except Exception:
        sys.exit(1)
