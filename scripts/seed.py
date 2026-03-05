#!/usr/bin/env python3
"""Seed script: creates a demo org and generates realistic event data."""

import json
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.db.engine import DuckDBManager
from app.db.schema import initialize_schema
from app.utils.api_key import generate_api_key, hash_api_key, key_prefix

DB_PATH = str(Path(__file__).parent.parent / "data" / "analytics.duckdb")

# Event definitions with realistic distributions
EVENT_TYPES = {
    "page_view": {
        "weight": 50,
        "properties": lambda: {
            "page": random.choice(["/home", "/pricing", "/features", "/blog", "/about", "/docs", "/signup", "/login"]),
            "referrer": random.choice(["google", "twitter", "direct", "github", "hackernews", ""]),
            "browser": random.choice(["Chrome", "Firefox", "Safari", "Edge"]),
        },
    },
    "signup": {
        "weight": 8,
        "properties": lambda: {
            "plan": random.choice(["free", "free", "free", "pro", "enterprise"]),
            "source": random.choice(["organic", "referral", "ad", "blog"]),
        },
    },
    "login": {
        "weight": 20,
        "properties": lambda: {
            "method": random.choice(["email", "google", "github"]),
        },
    },
    "button_click": {
        "weight": 30,
        "properties": lambda: {
            "button_id": random.choice(["cta_hero", "nav_signup", "pricing_pro", "pricing_enterprise", "docs_link"]),
            "page": random.choice(["/home", "/pricing", "/features"]),
        },
    },
    "purchase": {
        "weight": 3,
        "properties": lambda: {
            "amount": round(random.choice([9.99, 29.99, 49.99, 99.99, 199.99]), 2),
            "plan": random.choice(["pro", "enterprise"]),
            "currency": "USD",
        },
    },
    "feature_used": {
        "weight": 15,
        "properties": lambda: {
            "feature": random.choice(["dashboard", "export", "api", "webhook", "integration", "report"]),
        },
    },
    "error": {
        "weight": 5,
        "properties": lambda: {
            "error_code": random.choice(["400", "401", "403", "404", "500"]),
            "page": random.choice(["/api/events", "/api/query", "/dashboard"]),
        },
    },
}

# Build weighted event list
WEIGHTED_EVENTS = []
for name, config in EVENT_TYPES.items():
    WEIGHTED_EVENTS.extend([name] * config["weight"])

# User pool
NUM_USERS = 200
USERS = [f"user-{i:04d}" for i in range(NUM_USERS)]


def generate_events(num_events: int, days_back: int = 30) -> list[tuple]:
    """Generate realistic event data spread over the past N days."""
    rows = []
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(days=days_back)

    for _ in range(num_events):
        event_name = random.choice(WEIGHTED_EVENTS)
        distinct_id = random.choice(USERS)

        # Distribute events with more activity on weekdays and business hours
        day_offset = random.random() * days_back
        ts = start_time + timedelta(days=day_offset)
        # Add time-of-day bias (more events 9am-6pm)
        hour = random.gauss(13, 4)
        hour = max(0, min(23, int(hour)))
        ts = ts.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59))

        props = EVENT_TYPES[event_name]["properties"]()

        event_id = str(uuid.uuid4())
        rows.append((
            event_id, None, event_name, distinct_id, ts,
            json.dumps(props), now,
        ))

    return rows


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Seed event analytics database with demo data.")
    parser.add_argument("--name", default="Demo Organization", help="Organization name (default: 'Demo Organization')")
    parser.add_argument("--slug", default="demo", help="Organization slug (default: 'demo')")
    parser.add_argument("--events", type=int, default=15000, help="Number of events to generate (default: 15000)")
    parser.add_argument("--days", type=int, default=30, help="Days of history to generate (default: 30)")
    args = parser.parse_args()

    print("Seeding event analytics database...")
    print(f"Database: {DB_PATH}")

    db = DuckDBManager(DB_PATH)
    initialize_schema(db)

    # Check if org already exists
    existing = db.execute_read("SELECT id FROM organizations WHERE slug = ?", (args.slug,))
    if existing:
        print(f"Org '{args.slug}' already exists, skipping org creation.")
        org_id = existing[0]["id"]
    else:
        # Create org
        org_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        db.execute_write_sync(
            "INSERT INTO organizations (id, name, slug, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            [(org_id, args.name, args.slug, now, now)],
        )

        # Create API key
        raw_key = generate_api_key()
        key_id = str(uuid.uuid4())
        db.execute_write_sync(
            "INSERT INTO api_keys (id, org_id, key_prefix, key_hash, label, is_active, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(key_id, org_id, key_prefix(raw_key), hash_api_key(raw_key), "default", True, now)],
        )
        print(f"\nOrganization: {args.name} (slug: {args.slug})")
        print(f"API Key: {raw_key}")
        print("(Save this key - it won't be shown again!)\n")

    # Generate events
    num_events = args.events
    print(f"Generating {num_events} events over the last {args.days} days...")
    events = generate_events(num_events, days_back=args.days)

    # Set org_id on all events
    events = [(e[0], org_id, *e[2:]) for e in events]

    # Batch insert
    batch_size = 1000
    for i in range(0, len(events), batch_size):
        batch = events[i : i + batch_size]
        db.execute_write_sync(
            "INSERT INTO events (id, org_id, event_name, distinct_id, timestamp, properties, ingested_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            batch,
        )
        print(f"  Inserted {min(i + batch_size, len(events))}/{num_events} events")

    # Print summary
    counts = db.execute_read(
        "SELECT event_name, COUNT(*) as count FROM events WHERE org_id = ? GROUP BY event_name ORDER BY count DESC",
        (org_id,),
    )
    print("\nEvent distribution:")
    for row in counts:
        print(f"  {row['event_name']}: {row['count']}")

    total = db.execute_read("SELECT COUNT(*) as total FROM events WHERE org_id = ?", (org_id,))
    users = db.execute_read("SELECT COUNT(DISTINCT distinct_id) as users FROM events WHERE org_id = ?", (org_id,))
    print(f"\nTotal events: {total[0]['total']}")
    print(f"Unique users: {users[0]['users']}")
    print("\nSeed complete!")

    db.close()


if __name__ == "__main__":
    main()
