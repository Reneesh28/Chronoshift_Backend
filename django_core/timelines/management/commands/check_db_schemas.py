import json
from django.core.management.base import BaseCommand
from utils.mongo import db

class Command(BaseCommand):
    help = "Checks, initializes, and configures MongoDB collections with strict JSON Schema validations and optimized query indexes."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\n[START] Starting ChronoShift MongoDB Schema Verification & Configuration...\n"))

        # Define Schema Validators for each Collection
        validators = {
            "timelines": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["user_id", "title", "description"],
                    "properties": {
                        "user_id": {
                            "bsonType": "int",
                            "description": "must be an integer representing user id and is required"
                        },
                        "title": {
                            "bsonType": "string",
                            "maxLength": 255,
                            "description": "must be a string and is required"
                        },
                        "description": {
                            "bsonType": "string",
                            "description": "must be a string and is required"
                        },
                        "root_branch_id": {
                            "bsonType": ["string", "null"],
                            "description": "must be a string representing parent branch ObjectId or null"
                        }
                    }
                }
            },
            "branches": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["timeline_id", "branch_name", "decision_trigger", "divergence_score", "depth_level", "status"],
                    "properties": {
                        "timeline_id": {
                            "bsonType": "string",
                            "description": "must be a string representing timeline ObjectId and is required"
                        },
                        "parent_branch_id": {
                            "bsonType": ["string", "null"],
                            "description": "must be a string representing parent branch ObjectId or null"
                        },
                        "branch_name": {
                            "bsonType": "string",
                            "maxLength": 255,
                            "description": "must be a string and is required"
                        },
                        "decision_trigger": {
                            "bsonType": "string",
                            "description": "must be a string and is required"
                        },
                        "divergence_score": {
                            "bsonType": "double",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "must be a double between 0.0 and 1.0 and is required"
                        },
                        "depth_level": {
                            "bsonType": "int",
                            "minimum": 1,
                            "description": "must be a positive integer and is required"
                        },
                        "status": {
                            "bsonType": "string",
                            "description": "must be a string and is required"
                        }
                    }
                }
            },
            "events": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["timeline_id", "branch_id", "event_type", "event_value", "created_by"],
                    "properties": {
                        "timeline_id": {
                            "bsonType": "string",
                            "description": "must be a string representing timeline ObjectId and is required"
                        },
                        "branch_id": {
                            "bsonType": "string",
                            "description": "must be a string representing branch ObjectId and is required"
                        },
                        "event_type": {
                            "enum": ["decision", "simulation", "replay", "divergence"],
                            "description": "must be one of: decision, simulation, replay, divergence and is required"
                        },
                        "event_value": {
                            "bsonType": "string",
                            "description": "must be a string and is required"
                        },
                        "created_by": {
                            "bsonType": "int",
                            "description": "must be an integer and is required"
                        }
                    }
                }
            },
            "simulations": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["timeline_id", "source_branch_id", "generated_branch_ids", "simulation_status", "divergence_results"],
                    "properties": {
                        "timeline_id": {
                            "bsonType": "string",
                            "description": "must be a string representing timeline ObjectId and is required"
                        },
                        "source_branch_id": {
                            "bsonType": "string",
                            "description": "must be a string representing source branch ObjectId and is required"
                        },
                        "generated_branch_ids": {
                            "bsonType": "array",
                            "items": {
                                "bsonType": "string"
                            },
                            "description": "must be an array of strings representing branch ObjectIds and is required"
                        },
                        "simulation_status": {
                            "enum": ["queued", "processing", "completed", "failed"],
                            "description": "must be one of: queued, processing, completed, failed and is required"
                        },
                        "divergence_results": {
                            "bsonType": "object",
                            "description": "must be a mapping object and is required"
                        }
                    }
                }
            },
            "ai_summaries": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["timeline_id", "branch_id", "simulation_id", "risk_score", "confidence_score", "summary"],
                    "properties": {
                        "timeline_id": {
                            "bsonType": "string",
                            "description": "must be a string and is required"
                        },
                        "branch_id": {
                            "bsonType": "string",
                            "description": "must be a string and is required"
                        },
                        "simulation_id": {
                            "bsonType": "string",
                            "description": "must be a string and is required"
                        },
                        "risk_score": {
                            "bsonType": "double",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "must be a double between 0.0 and 1.0 and is required"
                        },
                        "confidence_score": {
                            "bsonType": "double",
                            "minimum": 0.0,
                            "maximum": 1.0,
                            "description": "must be a double between 0.0 and 1.0 and is required"
                        },
                        "summary": {
                            "bsonType": "string",
                            "description": "must be a string and is required"
                        }
                    }
                }
            },
            "replays": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["timeline_id", "branch_id", "event_sequence", "current_step", "status"],
                    "properties": {
                        "timeline_id": {
                            "bsonType": "string",
                            "description": "must be a string representing timeline ObjectId and is required"
                        },
                        "branch_id": {
                            "bsonType": "string",
                            "description": "must be a string representing branch ObjectId and is required"
                        },
                        "event_sequence": {
                            "bsonType": "array",
                            "items": {
                                "bsonType": "string"
                            },
                            "description": "must be an array of strings representing event IDs and is required"
                        },
                        "current_step": {
                            "bsonType": "int",
                            "minimum": 0,
                            "description": "must be an integer >= 0 and is required"
                        },
                        "status": {
                            "enum": ["playing", "paused", "completed"],
                            "description": "must be one of: playing, paused, completed and is required"
                        }
                    }
                }
            },
            "users": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["username", "email", "password_hash"],
                    "properties": {
                        "username": {
                            "bsonType": "string",
                            "maxLength": 150,
                            "description": "must be a string of at most 150 characters and is required"
                        },
                        "email": {
                            "bsonType": "string",
                            "description": "must be a string representing an email and is required"
                        },
                        "password_hash": {
                            "bsonType": "string",
                            "maxLength": 255,
                            "description": "must be a string of at most 255 characters and is required"
                        }
                    }
                }
            }
        }

        # Define Recommended Query Indexes for each Collection
        indexes = {
            "timelines": [
                [("user_id", 1)],
                [("created_at", 1)]
            ],
            "branches": [
                [("timeline_id", 1)],
                [("parent_branch_id", 1)],
                [("divergence_score", 1)]
            ],
            "events": [
                [("timeline_id", 1)],
                [("branch_id", 1)],
                [("timestamp", 1)]
            ],
            "simulations": [
                [("timeline_id", 1)],
                [("simulation_status", 1)]
            ],
            "ai_summaries": [
                [("branch_id", 1)],
                [("risk_score", 1)]
            ],
            "replays": [
                [("timeline_id", 1)],
                [("started_at", 1)]
            ],
            "users": [
                [("username", 1)],
                [("email", 1)]
            ]
        }

        # Get existing collections
        existing_collections = db.list_collection_names()

        # Initialize and update collections
        for collection_name, validator in validators.items():
            self.stdout.write(f"[*] Processing collection: {self.style.WARNING(collection_name)}")

            if collection_name in existing_collections:
                # Update schema validation rules for existing collections
                try:
                    db.command("collMod", collection_name, validator=validator, validationLevel="strict")
                    self.stdout.write(self.style.SUCCESS(f"   |-- Applied strict JSON Schema validator."))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   |-- Error modifying validator: {e}"))
            else:
                # Create collection with strict validation
                try:
                    db.create_collection(collection_name, validator=validator, validationLevel="strict")
                    self.stdout.write(self.style.SUCCESS(f"   |-- Created collection with strict JSON Schema validator."))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"   |-- Error creating collection: {e}"))

            # Create Indexes
            if collection_name in indexes:
                collection = db[collection_name]
                for idx_keys in indexes[collection_name]:
                    index_name = "_".join([f"{k}_{v}" for k, v in idx_keys])
                    try:
                        collection.create_index(idx_keys, name=index_name)
                        self.stdout.write(self.style.SUCCESS(f"   |-- Verified index: {index_name}"))
                    except Exception as e:
                        self.stdout.write(self.style.ERROR(f"   |-- Error creating index {index_name}: {e}"))

        self.stdout.write(self.style.SUCCESS("\n[SUCCESS] ChronoShift MongoDB collections are fully verified, validated, and optimized!\n"))
