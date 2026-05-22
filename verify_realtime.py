import subprocess
import time
import requests
import asyncio
import websockets
import json
import sys

async def test_websocket_broadcast():
    print("\n==================================================")
    print("STARTING REAL-TIME WEBSOCKET INTEGRATION TEST")
    print("==================================================")

    # 1. Launch Daphne ASGI Server
    print("[TEST] Launching Daphne ASGI server on port 8000...")
    daphne_process = subprocess.Popen(
        ["venv/Scripts/python", "-m", "daphne", "-p", "8000", "core.asgi:application"],
        cwd="django_core",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for Daphne to boot up
    time.sleep(3)
    
    if daphne_process.poll() is not None:
        print("[FAIL] Daphne server failed to start. Logs:")
        stdout, stderr = daphne_process.communicate()
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
        sys.exit(1)
        
    print("[TEST] Daphne server successfully running in background.")

    uri = "ws://127.0.0.1:8000/ws/timeline/test_timeline_id"
    broadcast_url = "http://127.0.0.1:8000/api/timelines/broadcast/"
    test_payload = {
        "event": "simulation_updated",
        "simulation_id": "sim_test_100",
        "progress": 42,
        "status": "processing"
    }

    try:
        # 2. Connect to the WebSocket
        print(f"[TEST] Attempting WebSocket handshake at: {uri}")
        async with websockets.connect(uri) as websocket:
            print("[SUCCESS] WebSocket handshake successful and channel established!")
            
            # 3. Fire internal REST API bridge broadcast request
            print(f"[TEST] Emitting broadcast payload via REST bridge: {broadcast_url}")
            response = requests.post(
                broadcast_url,
                json={
                    "timeline_id": "test_timeline_id",
                    "payload": test_payload
                },
                headers={"Content-Type": "application/json"}
            )
            
            assert response.status_code == 200, f"Broadcast endpoint returned status {response.status_code}: {response.text}"
            print("[SUCCESS] HTTP Broadcast Bridge accepted the request.")

            # 4. Wait for WebSocket message delivery
            print("[TEST] Waiting for event to stream over the WebSocket...")
            try:
                # 5-second timeout to prevent infinite hang
                message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                received_data = json.loads(message)
                print(f"[SUCCESS] Received message over WebSocket: {json.dumps(received_data, indent=2)}")
                
                # Assert payloads match exactly
                assert received_data.get("event") == test_payload["event"], "Payload 'event' mismatch"
                assert received_data.get("progress") == test_payload["progress"], "Payload 'progress' mismatch"
                assert received_data.get("simulation_id") == test_payload["simulation_id"], "Payload 'simulation_id' mismatch"
                print("\n[SUCCESS] ALL WEBSOCKET BROADCAST ASSERTIONS PASSED PERFECTLY!")
                
            except asyncio.TimeoutError:
                print("[FAIL] Timeout: Event broadcast was not received by the WebSocket client.")
                raise TimeoutError("WebSocket broadcast timeout")
                
    except Exception as e:
        print(f"\n[FAIL] Test encountered an error: {e}")
        raise e
    finally:
        # 5. Clean up Daphne process
        print("[TEST] Terminating Daphne background process...")
        daphne_process.terminate()
        try:
            daphne_process.wait(timeout=3)
            print("[TEST] Daphne server shut down cleanly.")
        except subprocess.TimeoutExpired:
            daphne_process.kill()
            print("[WARNING] Daphne process was forcefully killed.")
            
if __name__ == "__main__":
    try:
        asyncio.run(test_websocket_broadcast())
        print("\n==================================================")
        print("REAL-TIME WEBSOCKET INTEGRATION TEST PASSED!")
        print("==================================================")
    except Exception:
        sys.exit(1)
