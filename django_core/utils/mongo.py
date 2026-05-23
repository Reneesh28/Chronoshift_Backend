from pymongo import MongoClient
from dotenv import load_dotenv
import os

# --------------------------------------------------
# LOAD ENV VARIABLES
# --------------------------------------------------

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGO_DB_NAME = os.getenv("MONGO_DB_NAME")

# --------------------------------------------------
# CREATE CLIENT
# --------------------------------------------------

# Override DNS resolver for MongoDB Atlas SRV connection in restricted environments
try:
    import dns.resolver
    dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
    dns.resolver.default_resolver.nameservers = ['8.8.8.8', '1.1.1.1', '8.8.4.4']
except Exception as dns_err:
    print(f"[CONFIG WARNING] Failed to override default DNS resolver: {dns_err}")

client = MongoClient(MONGODB_URI)

# --------------------------------------------------
# DATABASE
# --------------------------------------------------

db = client[MONGO_DB_NAME]

# --------------------------------------------------
# TEST CONNECTION
# --------------------------------------------------

try:
    client.admin.command("ping")

    print("\n[OK] MongoDB Atlas Connection Successful\n")

except Exception as e:

    print("\n[ERROR] MongoDB Connection Failed\n")
    print(e)

# --------------------------------------------------
# COLLECTIONS
# --------------------------------------------------

timelines_collection = db["timelines"]
branches_collection = db["branches"]
events_collection = db["events"]
simulations_collection = db["simulations"]
ai_summaries_collection = db["ai_summaries"]
replays_collection = db["replays"]
users_collection = db["users"]