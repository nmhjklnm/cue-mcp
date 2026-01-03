"""会话名生成模块"""
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
    """生成人性化的会话名
    
    格式: {形容词}-{动物}-{数字}
    示例: brave-fox-17, swift-owl-42
    """
    adj = random.choice(ADJECTIVES)
    animal = random.choice(ANIMALS)
    num = random.randint(10, 99)
    return f"{adj}-{animal}-{num}"
