import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

def run_diagnostics():
    print("==========================================================")
    print("[DIAGNOSTICS] FastAPI Environment & Mongo Integration")
    print("==========================================================")

    # 1. Resolve shared env location (parent directory of service)
    service_dir = Path(__file__).resolve().parent
    root_backend_dir = service_dir.parent
    env_path = root_backend_dir / ".env"
    
    print(f"|-- Service root directory: {service_dir}")
    print(f"|-- Backend root directory: {root_backend_dir}")
    print(f"|-- Shared environment path: {env_path}")

    if not env_path.exists():
        print(f"[ERROR] Environment file not found at {env_path}!")
        sys.exit(1)

    load_dotenv(env_path)
    print("[OK] Shared environment variables loaded.")

    # 2. Extract settings
    mongo_uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGO_DB_NAME")

    print(f"|-- Loaded DB Name: {db_name}")
    if not mongo_uri:
        print("[ERROR] MONGODB_URI is missing in the env file!")
        sys.exit(1)

    # Clean display URI for logs
    display_uri = mongo_uri.split("@")[-1] if "@" in mongo_uri else mongo_uri
    print(f"|-- Loaded MongoDB Destination URI: ...@{display_uri}")

    # 3. Test MongoDB Connectivity
    try:
        try:
            import dns.resolver
            dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
            dns.resolver.default_resolver.nameservers = ['8.8.8.8', '1.1.1.1', '8.8.4.4']
        except Exception as dns_err:
            pass
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        # Force a call to test connection
        client.admin.command("ping")
        db = client[db_name]
        
        print("\n[SUCCESS] MongoDB Atlas Connection Verified successfully.")
        print(f"|-- Active Collections detected:")
        for col in db.list_collection_names():
            print(f"    * {col}")
            
    except Exception as e:
        print(f"\n[ERROR] MongoDB Atlas Connection failed from FastAPI environment: {e}")
        sys.exit(1)

    print("==========================================================\n")

if __name__ == "__main__":
    run_diagnostics()
