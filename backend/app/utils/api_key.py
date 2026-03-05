"""
API key generation and hashing utilities.

Keys follow the format: ea_live_<64 hex chars>
The prefix "ea_live_" makes keys identifiable (like Stripe's sk_live_ prefix).
This helps users know what a key is for if they find it in their env files.

secrets.token_hex(32) generates 32 random bytes = 64 hex characters.
This gives 256 bits of entropy - effectively unguessable by brute force.
"""

import hashlib
import secrets


def generate_api_key() -> str:
    """Generate an API key like ea_live_<64 hex chars>."""
    return f"ea_live_{secrets.token_hex(32)}"


def hash_api_key(key: str) -> str:
    """
    SHA-256 hash of the full API key. This is what we store in the DB.
    When a request comes in, we hash the provided key and compare hashes.
    One-way: you can't reverse the hash to get the original key.
    """
    return hashlib.sha256(key.encode()).hexdigest()


def key_prefix(key: str) -> str:
    """First 15 chars for display purposes (e.g., "ea_live_2d380...")."""
    return key[:15] + "..."
