import os
import sys
import django
from datetime import datetime

# 1. SETUP DJANGO ENVIRONMENT
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
django.setup()

from django.contrib.auth.models import User
from utils.mongo import (
    users_collection,
    timelines_collection,
    branches_collection,
    events_collection,
    simulations_collection,
    ai_summaries_collection,
    replays_collection,
    db
)

def store_sample_data():
    print("==========================================================")
    # Avoid unicode characters in heading to prevent Windows terminal console crashes
    print("[START] Storing Sample Data for All Django Core Apps")
    print("==========================================================")

    # 1. Test Connection
    try:
        db.command("ping")
        print("[OK] Connected to MongoDB Atlas successfully.\n")
    except Exception as e:
        print(f"[ERROR] Could not connect to MongoDB: {e}")
        return

    # Clean existing sample records to keep database clean
    sample_tag = "sample_dev_"
    username = f"{sample_tag}user"
    email = "dev_user@chronoshift.io"
    password = "DevSecurePassword123"

    print("[*] Cleaning up old sample records if any exist...")
    User.objects.filter(username=username).delete()
    users_collection.delete_many({"username": username})
    
    # We will delete other collections' items later based on timeline_id if created
    print("[OK] DB cleanup complete.\n")

    # APP 1: auth_app (User Sync)
    print("--- [APP 1: auth_app] Syncing User Auth ---")
    # A. Save in SQLite
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password
    )
    print(f"|-- [SUCCESS] Saved User in SQLite (ID: {user.id})")

    # B. Sync to MongoDB Atlas
    users_collection.insert_one({
        "username": user.username,
        "email": user.email,
        "password_hash": user.password
    })
    print(f"|-- [SUCCESS] Synchronized User to MongoDB Atlas users collection.")
    print(f"    * Username: {user.username}")
    print(f"    * Email: {user.email}\n")

    # APP 2: timelines (Timeline Creation)
    print("--- [APP 2: timelines] Creating Timelines ---")
    timeline_payload = {
        "user_id": user.id,
        "title": "Quantum Fleet Optimization",
        "description": "Dev branch evaluating logistics routing algorithms under deep space anomalies."
    }
    
    timeline_result = timelines_collection.insert_one(timeline_payload)
    timeline_id_str = str(timeline_result.inserted_id)
    print(f"|-- [SUCCESS] Saved Timeline in MongoDB Atlas timelines collection.")
    print(f"    * Timeline ID: {timeline_id_str}")
    print(f"    * Title: {timeline_payload['title']}\n")
    # APP 3: branches (Branches, Events, Simulations, AI Summaries)
    print("--- [APP 3: branches] Creating Branching Logic & Simulation Placeholders ---")
    
    # A. Root Branch
    root_branch_data = {
        "timeline_id": timeline_id_str,
        "parent_branch_id": None,
        "branch_name": "Standard Route 101",
        "decision_trigger": "Initial simulation launch with defaults",
        "divergence_score": 0.0,
        "depth_level": 1,
        "status": "active",
        "created_at": datetime.utcnow()
    }
    root_branch_result = branches_collection.insert_one(root_branch_data)
    root_branch_id_str = str(root_branch_result.inserted_id)
    
    # Update timeline root branch linkage
    timelines_collection.update_one(
        {"_id": timeline_result.inserted_id},
        {"$set": {"root_branch_id": root_branch_id_str}}
    )
    
    print(f"|-- [SUCCESS] Created Root Branch (ID: {root_branch_id_str})")
    print(f"|-- [SUCCESS] Linked Timeline root_branch_id to '{root_branch_id_str}'")

    # B. Derived Branch (Alternate Timeline)
    derived_branch_data = {
        "timeline_id": timeline_id_str,
        "parent_branch_id": root_branch_id_str,
        "branch_name": "Warp Bubble Bypass Route",
        "decision_trigger": "Activate Warp Engines at Sector 4 anomalies",
        "divergence_score": 0.74,
        "depth_level": 2,
        "status": "active",
        "created_at": datetime.utcnow()
    }
    derived_branch_result = branches_collection.insert_one(derived_branch_data)
    derived_branch_id_str = str(derived_branch_result.inserted_id)
    print(f"|-- [SUCCESS] Created Derived Branch (ID: {derived_branch_id_str})")

    # C. Event Injection (Decision Event)
    event_data = {
        "timeline_id": timeline_id_str,
        "branch_id": derived_branch_id_str,
        "event_type": "decision",
        "event_value": "Overload plasma conduits to increase velocity by 20%",
        "created_by": user.id,
        "timestamp": datetime.utcnow()
    }
    event_result = events_collection.insert_one(event_data)
    event_id_str = str(event_result.inserted_id)
    print(f"|-- [SUCCESS] Injected Decision Event (ID: {event_id_str})")

    # D. Simulation Setup
    simulation_data = {
        "timeline_id": timeline_id_str,
        "source_branch_id": derived_branch_id_str,
        "generated_branch_ids": [derived_branch_id_str],
        "simulation_status": "queued",
        "divergence_results": {
            derived_branch_id_str: 0.74
        },
        "started_at": datetime.utcnow(),
        "completed_at": None
    }
    sim_result = simulations_collection.insert_one(simulation_data)
    sim_id_str = str(sim_result.inserted_id)
    print(f"|-- [SUCCESS] Enqueued Simulation Placeholder (ID: {sim_id_str})")

    # E. AI Summary Insight
    ai_summary_data = {
        "timeline_id": timeline_id_str,
        "branch_id": derived_branch_id_str,
        "simulation_id": sim_id_str,
        "risk_score": 0.82,
        "confidence_score": 0.91,
        "summary": "Activating Warp Drive inside Sector 4 yields a high probability of structural fatigue. Plasma velocity increases by 20% but increases warp core collapse probability from 2% to 15%."
    }
    ai_result = ai_summaries_collection.insert_one(ai_summary_data)
    ai_id_str = str(ai_result.inserted_id)
    print(f"|-- [SUCCESS] Saved AI Summary Narrative (ID: {ai_id_str})\n")

    # APP 4: replay (Replay Sequences)
    print("--- [APP 4: replay] Creating Playback Replay Sessions ---")
    replay_data = {
        "timeline_id": timeline_id_str,
        "branch_id": derived_branch_id_str,
        "event_sequence": [event_id_str],
        "current_step": 0,
        "status": "playing",
        "started_at": datetime.utcnow()
    }
    replay_result = replays_collection.insert_one(replay_data)
    replay_id_str = str(replay_result.inserted_id)
    print(f"|-- [SUCCESS] Initialized Replay Playback Session (ID: {replay_id_str})\n")
    # REPORT SUMMARY
    print("==========================================================")
    print("[SUMMARY] Developer Sample Seed Operations Completed Successfully")
    print("==========================================================")
    print(f"Registered User Name:  {username}")
    print(f"Registered User Email: {email}")
    print(f"Timeline ID:           {timeline_id_str}")
    print(f"Root Branch ID:        {root_branch_id_str}")
    print(f"Derived Branch ID:     {derived_branch_id_str}")
    print(f"Event ID:              {event_id_str}")
    print(f"Simulation ID:         {sim_id_str}")
    print(f"AI Summary ID:         {ai_id_str}")
    print(f"Replay Session ID:     {replay_id_str}")
    print("==========================================================")
    print("[!] You can now explore these structures directly in MongoDB Compass/Atlas.")
    print("[!] Run this script again at any time to regenerate/reset developer records.")
    print("==========================================================\n")

if __name__ == "__main__":
    store_sample_data()
