import hashlib
import secrets


def generate_api_key() -> str:
    """Generate an API key like ea_live_<32 hex chars>."""
    return f"ea_live_{secrets.token_hex(32)}"


def hash_api_key(key: str) -> str:
    """SHA-256 hash of the full API key."""
    return hashlib.sha256(key.encode()).hexdigest()


def key_prefix(key: str) -> str:
    """First 15 chars for display purposes."""
    return key[:15] + "..."
