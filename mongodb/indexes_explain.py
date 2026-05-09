# Profile 4 query archetypes with and without their proposed index.
# Captures executionStats from explain(). docsExamined is the metric I
# rely on; wall-clock is meaningless at this scale because the working
# set fits in cache.

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient


env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(env_path)
uri = os.getenv("MONGODB_URI", "").strip()
if not uri:
    sys.exit(f"MONGODB_URI is empty. Open {env_path} and paste your string.")

client = MongoClient(uri, serverSelectionTimeoutMS=10000)
db = client["northstar"]
oa = db.orders_aggregate


# ---------------------------------------------------------------------------
# Queries under test. Each entry pairs a representative filter with the
# index the literature would suggest for it.
# ---------------------------------------------------------------------------
QUERIES = [
    {
        "id": "Q_A",
        "name": "Single field equality on service_type",
        "filter": {"service_type": "Business"},
        "indexes": [[("service_type", ASCENDING)]],
        "rationale": "Equality match on a low cardinality field. Tests whether a "
                     "single field index reduces docsExamined to nReturned.",
    },
    {
        "id": "Q_B",
        "name": "Compound match on service_type and delivery.delivery_status",
        "filter": {"service_type": "Business", "delivery.delivery_status": "Failed"},
        "indexes": [[("service_type", ASCENDING), ("delivery.delivery_status", ASCENDING)]],
        "rationale": "Compound predicate that benefits from a compound index "
                     "with the most selective field first.",
    },
    {
        "id": "Q_C",
        "name": "Point lookup on order_id (high cardinality)",
        "filter": {"order_id": "O00023"},
        "indexes": [[("order_id", ASCENDING)]],
        "rationale": "Equality on a unique identifier. Predicts the most "
                     "extreme reduction since exactly 1 document matches.",
    },
    {
        "id": "Q_D",
        "name": "Equality on pickup_zone (mid cardinality)",
        "filter": {"pickup_zone": "Central"},
        "indexes": [[("pickup_zone", ASCENDING)]],
        "rationale": "Mid cardinality equality, a common reporting filter "
                     "after the zone canonicalisation step.",
    },
]


def drop_non_default_indexes() -> None:
    """Reset the index state to only the mandatory _id_ index."""
    for ix in oa.list_indexes():
        if ix["name"] != "_id_":
            oa.drop_index(ix["name"])


def stage_chain(plan: dict) -> str:
    """Walk a winning plan and return its stage chain joined by arrows."""
    stages = []
    cur = plan
    while cur:
        st = cur.get("stage")
        if st:
            stages.append(st)
        cur = cur.get("inputStage")
    return " -> ".join(stages)


def capture(filter_: dict) -> dict:
    """Return the executionStats subset we want, plus the stage chain."""
    exp = oa.find(filter_).explain()
    qp = exp.get("queryPlanner", {})
    es = exp.get("executionStats", {})
    return {
        "stage_chain": stage_chain(qp.get("winningPlan", {})),
        "n_returned": es.get("nReturned", 0),
        "docs_examined": es.get("totalDocsExamined", 0),
        "keys_examined": es.get("totalKeysExamined", 0),
        "exec_ms": es.get("executionTimeMillis", 0),
    }


def fmt_row(label: str, s: dict) -> str:
    return (
        f"  {label:<7} | stage_chain={s['stage_chain']:<35} | "
        f"nReturned={s['n_returned']:<4} | "
        f"docsExamined={s['docs_examined']:<6} | "
        f"keysExamined={s['keys_examined']:<6} | "
        f"execMs={s['exec_ms']}"
    )


def reduction(before: int, after: int) -> str:
    if not after:
        return "n/a (after = 0)"
    return f"{before / max(after, 1):.1f}x"


def run_one(q: dict) -> None:
    title = f"{q['id']}. {q['name']}"
    print()
    print(title)
    print("-" * len(title))
    print(f"  Rationale: {q['rationale']}")
    print(f"  Filter:    {q['filter']}")
    print(f"  Index set: {q['indexes']}")
    print()

    # Baseline.
    drop_non_default_indexes()
    before = capture(q["filter"])
    print(fmt_row("BEFORE", before))

    # Indexed run.
    for spec in q["indexes"]:
        oa.create_index(spec)
    after = capture(q["filter"])
    print(fmt_row("AFTER ", after))

    # Reduction summary.
    print()
    print(f"  docsExamined:    {before['docs_examined']:>6} -> {after['docs_examined']:<6} "
          f"reduction {reduction(before['docs_examined'], after['docs_examined'])}")
    print(f"  keysExamined:    {before['keys_examined']:>6} -> {after['keys_examined']:<6}")
    print(f"  execTimeMillis:  {before['exec_ms']:>6} -> {after['exec_ms']:<6} "
          f"speedup   {reduction(before['exec_ms'], after['exec_ms'])}")


def main() -> int:
    print("=" * 78)
    print("Query optimisation experiments on northstar.orders_aggregate")
    print("=" * 78)
    print(f"Document count: {oa.estimated_document_count()}")
    print(f"Server:         {client.server_info().get('version', 'unknown')}")

    for q in QUERIES:
        run_one(q)

    print()
    print("=" * 78)
    print("Final indexes installed on orders_aggregate")
    print("=" * 78)
    for ix in oa.list_indexes():
        keys = dict(ix["key"])
        print(f"  - {ix['name']:<35} keys={keys}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
