import os
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient

# 1. Resolve shared env location (parent directory of flask_ai_engine)
SERVICE_DIR = Path(__file__).resolve().parent
ROOT_BACKEND_DIR = SERVICE_DIR.parent
ENV_PATH = ROOT_BACKEND_DIR / ".env"

# Load from .env file if available (local dev), otherwise rely on
# environment variables already injected by Docker Compose env_file.
if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    # In Docker, env vars are injected directly — no file needed
    pass

# Read environment variables
MONGODB_URI = os.getenv("MONGODB_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "Chronoshift")
HF_TOKEN = os.getenv("HF_TOKEN")
MODEL_NAME = os.getenv("MODEL_NAME", "microsoft/phi-2")
AI_REMOTE_ENABLED = os.getenv("AI_REMOTE_ENABLED", "False") == "True"
DJANGO_URL = os.getenv("DJANGO_URL")

if not DJANGO_URL:
    raise ValueError("DJANGO_URL environment variable is missing. Configure it in your .env or the system context.")

if not MONGODB_URI:
    raise ValueError("MONGODB_URI variable is missing in the env file")

if not HF_TOKEN:
    print("[CONFIG WARNING] HF_TOKEN is not set. Flask AI Engine will use fallback summaries only.")
elif not AI_REMOTE_ENABLED:
    print("[CONFIG] Remote Hugging Face inference disabled. Flask AI Engine will use fallback summaries.")

# Override DNS resolver for MongoDB Atlas SRV connection in restricted environments
try:
    import dns.resolver
    dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
    dns.resolver.default_resolver.nameservers = ['8.8.8.8', '1.1.1.1', '8.8.4.4']
except Exception as dns_err:
    print(f"[CONFIG WARNING] Failed to override default DNS resolver: {dns_err}")

# 2. Establish MongoDB Client
client = MongoClient(MONGODB_URI)
db = client[MONGO_DB_NAME]

# 3. Mapped PyMongo Collections
users_collection = db["users"]
timelines_collection = db["timelines"]
branches_collection = db["branches"]
events_collection = db["events"]
simulations_collection = db["simulations"]
ai_summaries_collection = db["ai_summaries"]
replays_collection = db["replays"]

print(f"[CONFIG] Flask AI Engine config successfully loaded.")
print(f"[CONFIG] Target Model: '{MODEL_NAME}'")
print(f"[CONFIG] MongoDB database connected: '{MONGO_DB_NAME}'")
