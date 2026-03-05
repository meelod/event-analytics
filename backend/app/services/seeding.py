"""
Demo data seeding service.

Generates realistic randomized events for a given org, matching the same
logic as scripts/seed.py but callable from the backend API.

This lets users seed demo data from the Settings page UI instead of
needing to run a CLI script. The event types, weights, and property
generators are identical to the seed script.
"""

import json
import random
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone

from app.db.engine import DuckDBManager

# ---------------------------------------------------------------------------
# Event type definitions with weighted distributions.
#
# Each event type has:
# - weight: relative frequency (page_view at 50 is ~38% of all events)
# - properties: a lambda that returns randomized properties for that event
#
# These are identical to scripts/seed.py to ensure consistency.
# ---------------------------------------------------------------------------
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

# Build a weighted list: each event name repeated by its weight.
# random.choice() on this list naturally produces the right distribution.
WEIGHTED_EVENTS: list[str] = []
for name, config in EVENT_TYPES.items():
    WEIGHTED_EVENTS.extend([name] * config["weight"])

# Pool of synthetic user IDs
NUM_USERS = 200
USERS = [f"user-{i:04d}" for i in range(NUM_USERS)]


def generate_events(org_id: str, num_events: int, days_back: int = 30) -> list[tuple]:
    """
    Generate realistic event rows ready for batch INSERT.

    Each row is a tuple matching the events table columns:
    (id, org_id, event_name, distinct_id, timestamp, properties_json, ingested_at)

    Timestamps are distributed across the past `days_back` days with a
    Gaussian bias toward business hours (peak at 1pm, std dev 4 hours).
    """
    rows = []
    now = datetime.now(timezone.utc)
    start_time = now - timedelta(days=days_back)

    for _ in range(num_events):
        event_name = random.choice(WEIGHTED_EVENTS)
        distinct_id = random.choice(USERS)

        # Spread events uniformly across the date range
        day_offset = random.random() * days_back
        ts = start_time + timedelta(days=day_offset)

        # Bias time-of-day toward business hours (Gaussian centered at 1pm)
        hour = random.gauss(13, 4)
        hour = max(0, min(23, int(hour)))
        ts = ts.replace(hour=hour, minute=random.randint(0, 59), second=random.randint(0, 59))

        props = EVENT_TYPES[event_name]["properties"]()
        event_id = str(uuid.uuid4())

        rows.append((
            event_id, org_id, event_name, distinct_id, ts,
            json.dumps(props), now,
        ))

    return rows


async def seed_demo_events(
    db: DuckDBManager,
    org_id: str,
    count: int = 1000,
    days_back: int = 30,
) -> dict:
    """
    Generate and insert demo events for an org.

    Returns a summary dict with:
    - inserted: number of events inserted
    - distribution: {event_name: count} breakdown
    """
    # Generate the event rows
    events = generate_events(org_id, count, days_back)

    # Count the distribution before inserting (for the response)
    event_names = [row[2] for row in events]  # index 2 = event_name
    distribution = dict(Counter(event_names))

    # Batch insert in chunks of 1000 (same pattern as seed.py)
    batch_size = 1000
    for i in range(0, len(events), batch_size):
        batch = events[i : i + batch_size]
        await db.execute_write(
            "INSERT INTO events (id, org_id, event_name, distinct_id, timestamp, properties, ingested_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            batch,
        )

    return {
        "inserted": len(events),
        "distribution": distribution,
    }
