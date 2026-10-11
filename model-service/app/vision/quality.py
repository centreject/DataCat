"""Image quality signals that do not need a model."""

from PIL import Image, ImageStat

# LOW_VISIBILITY: the frame has (almost) no texture — a lens covered by a finger, tape or a cap.
# Only texture separates that from a dark scene: eval photos darkened to 30% reach mean brightness 2
# yet keep a standard deviation of 6 or more, while a covered lens shows (almost) none whatever the
# light (R3 review, measured 2026-10-04). Brightness alone flagged dim hallways with people in them.
# Spring still decides "camera blocked" with ToF (someone close + nothing visible → 안전 확인 필요).
UNIFORM_STDDEV = 5


def low_visibility(image: Image.Image) -> bool:
    stat = ImageStat.Stat(image.convert("L").resize((64, 48)))
    return stat.stddev[0] < UNIFORM_STDDEV
