import os
from datetime import date

from pymongo import MongoClient

DB_NAME = "jd_intake_db"
COLLECTION_NAME = "jobs"

_client = None


def _get_collection():
    """Return the `jobs` collection, connecting to MongoDB (via MONGO_URI) on first use."""
    global _client
    if _client is None:
        mongo_uri = os.getenv("MONGO_URI")
        if not mongo_uri:
            raise RuntimeError(
                "MONGO_URI environment variable is not set. "
                "Add your MongoDB Atlas connection string to .env (see .env.example)."
            )
        _client = MongoClient(mongo_uri)
    return _client[DB_NAME][COLLECTION_NAME]


def find_duplicate_job(title: str, company: str):
    """Return the existing job doc with the same title+company (case/whitespace-insensitive), or None.

    Compares against precomputed lowercase fields rather than a regex match — a raw keyword
    dropped into MongoDB's $regex can crash on special characters (seen firsthand in the
    Day 1 job search tool), and it's slower than an indexable equality check anyway.
    """
    collection = _get_collection()
    return collection.find_one({
        "title_lower": title.strip().lower(),
        "company_lower": company.strip().lower(),
    })


def publish_job_in_db(parsed: dict, description: str, quality_score: int) -> str:
    """Insert a published job posting. Returns the new document's id as a string."""
    collection = _get_collection()
    doc = {
        **parsed,
        "title_lower": parsed["title"].strip().lower(),
        "company_lower": parsed["company"].strip().lower(),
        "description": description,
        "quality_score": quality_score,
        "date_posted": date.today().isoformat(),
    }
    result = collection.insert_one(doc)
    return str(result.inserted_id)
