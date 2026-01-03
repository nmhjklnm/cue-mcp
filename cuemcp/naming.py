"""Conversation name generator."""
import secrets


C = "bcdfghjklmnpqrstvwxz"
V = "aeiou"
CODA = ["", "n", "r", "l", "s", "m", "nd", "st", "rk", "ld"]


def syllable() -> str:
    return secrets.choice(C) + secrets.choice(V) + secrets.choice(CODA)


def pure_name(min_len: int = 8, max_len: int = 12) -> str:
    for _ in range(100):
        n_syl = secrets.choice([3, 4, 5])
        s = "".join(syllable() for _ in range(n_syl))
        s = s[:max_len]
        if min_len <= len(s) <= max_len and s.isalpha():
            return s
    raise RuntimeError("Name generation failed; adjust syllable/length parameters")


def generate_name() -> str:
    """Generate a human-friendly conversation name.

    Format: pronounceable lowercase letters only
    Examples: tavilron, nemosand
    """
    return pure_name().lower()
