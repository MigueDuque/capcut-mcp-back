import uuid

from enum import Enum
from typing import Dict, List, Any


class Keyframe:
    """A single keyframe (control point), currently supports linear interpolation only"""

    kf_id: str
    """Globally unique keyframe id, auto-generated"""
    time_offset: int
    """Time offset relative to the segment start, in microseconds"""
    values: List[float]
    """Keyframe value(s) — typically a single-element list"""

    def __init__(self, time_offset: int, value: float):
        """Initialize a keyframe with a given time offset and value"""
        self.kf_id = uuid.uuid4().hex

        self.time_offset = time_offset
        self.values = [value]

    def export_json(self) -> Dict[str, Any]:
        return {
            # Defaults
            "curveType": "Line",
            "graphID": "",
            "left_control": {"x": 0.0, "y": 0.0},
            "right_control": {"x": 0.0, "y": 0.0},
            # Custom fields
            "id": self.kf_id,
            "time_offset": self.time_offset,
            "values": self.values
        }


class Keyframe_property(Enum):
    """The property type controlled by a keyframe"""

    position_x = "KFTypePositionX"
    """Positive = move right; value = CapCut display value / draft width (half-canvas-width units)"""
    position_y = "KFTypePositionY"
    """Positive = move up; value = CapCut display value / draft height (half-canvas-height units)"""
    rotation = "KFTypeRotation"
    """Clockwise rotation in **degrees**"""

    scale_x = "KFTypeScaleX"
    """X-axis scale (1.0 = no scale); mutually exclusive with uniform_scale"""
    scale_y = "KFTypeScaleY"
    """Y-axis scale (1.0 = no scale); mutually exclusive with uniform_scale"""
    uniform_scale = "UNIFORM_SCALE"
    """Uniform XY scale (1.0 = no scale); mutually exclusive with scale_x and scale_y"""

    alpha = "KFTypeAlpha"
    """Opacity (1.0 = fully opaque); only valid on Video_segment"""
    saturation = "KFTypeSaturation"
    """Saturation offset (0.0 = original, range -1.0 to 1.0); only valid on Video_segment"""
    contrast = "KFTypeContrast"
    """Contrast offset (0.0 = original, range -1.0 to 1.0); only valid on Video_segment"""
    brightness = "KFTypeBrightness"
    """Brightness offset (0.0 = original, range -1.0 to 1.0); only valid on Video_segment"""

    volume = "KFTypeVolume"
    """Volume (1.0 = original); valid on Audio_segment and Video_segment"""


class Keyframe_list:
    """A list of keyframes controlling a single property"""

    list_id: str
    """Globally unique list id, auto-generated"""
    keyframe_property: Keyframe_property
    """The property this list controls"""
    keyframes: List[Keyframe]
    """The keyframes in this list"""

    def __init__(self, keyframe_property: Keyframe_property):
        """Initialize a keyframe list for the given property"""
        self.list_id = uuid.uuid4().hex

        self.keyframe_property = keyframe_property
        self.keyframes = []

    def add_keyframe(self, time_offset: int, value: float):
        """Add a keyframe at the given time offset with the given value"""
        keyframe = Keyframe(time_offset, value)
        self.keyframes.append(keyframe)
        self.keyframes.sort(key=lambda x: x.time_offset)

    def export_json(self) -> Dict[str, Any]:
        return {
            "id": self.list_id,
            "keyframe_list": [kf.export_json() for kf in self.keyframes],
            "material_id": "",
            "property_type": self.keyframe_property.value
        }
