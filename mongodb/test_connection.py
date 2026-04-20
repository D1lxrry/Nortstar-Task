# Smoke test: ping Atlas and list the databases.
# I leave this in the repo because it is the first script I run after
# any change to .env or the cluster.

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    sys.exit(
        "python-dotenv is not installed. Run this first:\n"
        "    python3 -m pip install python-dotenv\n"
    )

try:
    from pymongo import MongoClient
    from pymongo.errors import ConfigurationError, OperationFailure, ServerSelectionTimeoutError
except ImportError:
    sys.exit(
        "pymongo is not installed. Run this first:\n"
        '    python3 -m pip install "pymongo[srv]"\n'
    )


def main() -> int:
    env_path = Path(__file__).resolve().parent / ".env"
    load_dotenv(env_path)

    uri = os.getenv("MONGODB_URI", "").strip()
    if not uri:
        print("MONGODB_URI is empty.")
        print(f"Open {env_path} and paste your Atlas connection string between the quotes.")
        return 1

    print("Connecting to MongoDB Atlas...")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=10000)
        client.admin.command("ping")
    except ConfigurationError as exc:
        print(f"Configuration error: {exc}")
        print("Usually this means the connection string is malformed. Recopy it from Atlas.")
        return 2
    except OperationFailure as exc:
        print(f"Authentication failed: {exc}")
        print("Check the username and password inside .env are correct.")
        return 3
    except ServerSelectionTimeoutError as exc:
        print(f"Could not reach the cluster: {exc}")
        print("Check your internet connection and that your IP is on the Atlas Network Access list.")
        return 4

    print("Connection OK. Ping successful.")
    print()
    print("Databases on this cluster:")
    for name in sorted(client.list_database_names()):
        print(f"  - {name}")

    # Extra demo: peek at 1 document from the sample_airbnb database, if it exists.
    if "sample_airbnb" in client.list_database_names():
        print()
        print("Peek at 1 listing from sample_airbnb.listingsAndReviews:")
        doc = client["sample_airbnb"]["listingsAndReviews"].find_one(
            {}, {"name": 1, "property_type": 1, "address.country": 1, "price": 1}
        )
        print(doc)

    return 0


if __name__ == "__main__":
    sys.exit(main())
