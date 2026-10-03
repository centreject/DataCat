"""Image quality signals that do not need a model."""

from PIL import Image, ImageStat

# Below these the frame shows (almost) nothing: a covered lens, tape, or an unlit hallway.
# The image alone cannot tell "blocked" from "dark", so the service only reports LOW_VISIBILITY;
# Spring decides with ToF (someone close + nothing visible → plan's 안전 확인 필요).
DARK_MEAN = 20
UNIFORM_STDDEV = 8


def low_visibility(image: Image.Image) -> bool:
    stat = ImageStat.Stat(image.convert("L").resize((64, 48)))
    return stat.mean[0] < DARK_MEAN or stat.stddev[0] < UNIFORM_STDDEV
