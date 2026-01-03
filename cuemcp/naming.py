"""Conversation name generator."""
import random


ADJECTIVES = [
    "brave", "swift", "clever", "calm", "wild",
    "curious", "bright", "gentle", "bold", "keen",
    "noble", "quiet", "sharp", "warm", "wise",
]

ANIMALS = [
    "fox", "owl", "wolf", "hawk", "panda",
    "tiger", "deer", "bear", "eagle", "lion",
    "crane", "otter", "raven", "lynx", "heron",
]


def generate_name() -> str:
    """Generate a human-friendly conversation name.

    Format: {adjective}-{animal}-{number}
    Examples: brave-fox-17, swift-owl-42
    """
    adj = random.choice(ADJECTIVES)
    animal = random.choice(ANIMALS)
    num = random.randint(10, 99)
    return f"{adj}-{animal}-{num}"
