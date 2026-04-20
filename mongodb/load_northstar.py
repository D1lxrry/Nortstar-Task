# Load the 9 NorthStar CSVs into a fresh MongoDB database.
# Drops each collection first so reruns produce a clean load.

import csv
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient

# CSVs used to live under the Cybersecurity module folder while I was
# still moving things around. Once I committed the dataset to the repo
# I switched to the in-repo path. Repo root is one level up from here.
DATASET_DIR = Path(__file__).resolve().parent.parent / "northstar_dataset"
DB_NAME = "northstar"

CSV_FILES = [
    "customers.csv", "orders.csv", "deliveries.csv",
    "drivers.csv", "vehicles.csv", "hubs.csv",
    "incidents.csv", "complaints.csv", "app_events.csv",
]

# The CSVs use a mix of timestamp shapes. strptime is greedy so order
# matters: most specific format first.
DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
]


def coerce(value):
    # Detect ints, floats, dates, bools. Anything else stays a string.
    # Int has to come before float so "5" does not become 5.0.
    if value is None:
        return None
    s = value.strip()
    if s == "":
        return None
    if s.lstrip("-").isdigit():
        try:
            return int(s)
        except ValueError:
            pass
    try:
        return float(s)
    except ValueError:
        pass
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    if s.lower() in ("true", "false"):
        return s.lower() == "true"
    return s


def load_csv(path):
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [{k: coerce(v) for k, v in row.items()} for row in reader]


def main():
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path)

    uri = os.getenv("MONGODB_URI", "").strip()
    if not uri:
        sys.exit(f"MONGODB_URI is empty. Set it in {env_path}.")
    if not DATASET_DIR.exists():
        sys.exit(f"Dataset folder not found: {DATASET_DIR}")

    print(f"connecting to atlas, db={DB_NAME}")
    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    db = client[DB_NAME]

    total = 0
    for name in CSV_FILES:
        path = DATASET_DIR / name
        if not path.exists():
            print(f"  MISSING: {path}")
            continue
        collection = name[:-4]
        db[collection].drop()
        docs = load_csv(path)
        if docs:
            db[collection].insert_many(docs)
        total += len(docs)
        print(f"  {collection:<12} {len(docs):>5} docs")

    print(f"\ntotal: {total} documents across {len(CSV_FILES)} collections")


if __name__ == "__main__":
    main()
