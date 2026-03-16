"""Base segment class and commonly shared attribute classes"""

import uuid
from typing import Optional, Dict, List, Any, Union

from .animation import Segment_animations
from .time_util import Timerange, tim
from .keyframe import Keyframe_list, Keyframe_property


class Base_segment:
    """Base class for all track segments"""

    segment_id: str
    """Globally unique segment id, auto-generated"""
    material_id: str
    """Id of the material used by this segment"""
    target_timerange: Timerange
    """Time range of this segment on the track"""

    common_keyframes: List[Keyframe_list]
    """Keyframe lists for each animated property"""

    def __init__(self, material_id: str, target_timerange: Timerange):
        self.segment_id = uuid.uuid4().hex
        self.material_id = material_id
        self.target_timerange = target_timerange

        self.common_keyframes = []

    @property
    def start(self) -> int:
        """Segment start time in microseconds"""
        return self.target_timerange.start
    @start.setter
    def start(self, value: int):
        self.target_timerange.start = value

    @property
    def duration(self) -> int:
        """Segment duration in microseconds"""
        return self.target_timerange.duration
    @duration.setter
    def duration(self, value: int):
        self.target_timerange.duration = value

    @property
    def end(self) -> int:
        """Segment end time in microseconds"""
        return self.target_timerange.end

    def overlaps(self, other: "Base_segment") -> bool:
        """Return True if this segment overlaps with another"""
        return self.target_timerange.overlaps(other.target_timerange)

    def export_json(self) -> Dict[str, Any]:
        """Return attributes common to all segment types"""
        return {
            "enable_adjust": True,
            "enable_color_correct_adjust": False,
            "enable_color_curves": True,
            "enable_color_match_adjust": False,
            "enable_color_wheels": True,
            "enable_lut": True,
            "enable_smart_color_adjust": False,
            "last_nonzero_volume": 1.0,
            "reverse": False,
            "track_attribute": 0,
            "track_render_index": 0,
            "visible": True,
            # Custom fields
            "id": self.segment_id,
            "material_id": self.material_id,
            "target_timerange": self.target_timerange.export_json(),

            "common_keyframes": [kf_list.export_json() for kf_list in self.common_keyframes],
            "keyframe_refs": [],  # purpose unclear
        }


class Speed:
    """Playback speed object; currently only constant speed is supported"""

    global_id: str
    """Globally unique id, auto-generated"""
    speed: float
    """Playback speed"""

    def __init__(self, speed: float):
        self.global_id = uuid.uuid4().hex
        self.speed = speed

    def export_json(self) -> Dict[str, Any]:
        return {
            "curve_speed": None,
            "id": self.global_id,
            "mode": 0,
            "speed": self.speed,
            "type": "speed"
        }


class Clip_settings:
    """Image transform settings for a segment"""

    alpha: float
    """Opacity, 0–1"""
    flip_horizontal: bool
    """Whether to flip horizontally"""
    flip_vertical: bool
    """Whether to flip vertically"""
    rotation: float
    """Clockwise rotation in **degrees**; may be negative"""
    scale_x: float
    """Horizontal scale factor"""
    scale_y: float
    """Vertical scale factor"""
    transform_x: float
    """Horizontal offset in half-canvas-width units"""
    transform_y: float
    """Vertical offset in half-canvas-height units"""

    def __init__(self, *, alpha: float = 1.0,
                 flip_horizontal: bool = False, flip_vertical: bool = False,
                 rotation: float = 0.0,
                 scale_x: float = 1.0, scale_y: float = 1.0,
                 transform_x: float = 0.0, transform_y: float = 0.0):
        """Initialize image transform settings; defaults produce no transformation.

        Args:
            alpha (float, optional): Opacity, 0–1. Defaults to 1.0.
            flip_horizontal (bool, optional): Flip horizontally. Defaults to False.
            flip_vertical (bool, optional): Flip vertically. Defaults to False.
            rotation (float, optional): Clockwise rotation in **degrees**. Defaults to 0.0.
            scale_x (float, optional): Horizontal scale. Defaults to 1.0.
            scale_y (float, optional): Vertical scale. Defaults to 1.0.
            transform_x (float, optional): Horizontal offset in half-canvas-width units. Defaults to 0.0.
            transform_y (float, optional): Vertical offset in half-canvas-height units. Defaults to 0.0.
                Note: CapCut-imported subtitles typically use -0.8.
        """
        self.alpha = alpha
        self.flip_horizontal, self.flip_vertical = flip_horizontal, flip_vertical
        self.rotation = rotation
        self.scale_x, self.scale_y = scale_x, scale_y
        self.transform_x, self.transform_y = transform_x, transform_y

    def export_json(self) -> Dict[str, Any]:
        clip_settings_json = {
            "alpha": self.alpha,
            "flip": {"horizontal": self.flip_horizontal, "vertical": self.flip_vertical},
            "rotation": self.rotation,
            "scale": {"x": self.scale_x, "y": self.scale_y},
            "transform": {"x": self.transform_x, "y": self.transform_y}
        }
        return clip_settings_json


class Media_segment(Base_segment):
    """Base class for media segments (video and audio)"""

    source_timerange: Optional[Timerange]
    """Time range clipped from the source material; None for stickers"""
    speed: Speed
    """Playback speed settings"""
    volume: float
    """Volume level"""

    extra_material_refs: List[str]
    """Additional material ids linked to this segment (animations, effects, etc.)"""

    def __init__(self, material_id: str, source_timerange: Optional[Timerange], target_timerange: Timerange, speed: float, volume: float):
        super().__init__(material_id, target_timerange)

        self.source_timerange = source_timerange
        self.speed = Speed(speed)
        self.volume = volume

        self.extra_material_refs = [self.speed.global_id]

    def export_json(self) -> Dict[str, Any]:
        """Return attributes common to audio and video segments"""
        ret = super().export_json()
        ret.update({
            "source_timerange": self.source_timerange.export_json() if self.source_timerange else None,
            "speed": self.speed.speed,
            "volume": self.volume,
            "extra_material_refs": self.extra_material_refs,
        })
        return ret


class Visual_segment(Media_segment):
    """Base class for visible segments (video, sticker, text)"""

    clip_settings: Clip_settings
    """Image transform settings; may be overridden by keyframes"""

    uniform_scale: bool
    """Whether XY scale is locked together"""

    animations_instance: Optional[Segment_animations]
    """Animation collection; may be None.

    Automatically added to the materials list when the segment is placed on a track.
    """

    def __init__(self, material_id: str, source_timerange: Optional[Timerange], target_timerange: Timerange,
                 speed: float, volume: float, *, clip_settings: Optional[Clip_settings]):
        """Initialize a visual segment.

        Args:
            material_id (`str`): Material id
            source_timerange (`Timerange`, optional): Clipped range from the source material
            target_timerange (`Timerange`): Target time range on the track
            speed (`float`): Playback speed
            volume (`float`): Volume level
            clip_settings (`Clip_settings`, optional): Image transform settings; defaults to no transformation
        """
        super().__init__(material_id, source_timerange, target_timerange, speed, volume)

        self.clip_settings = clip_settings if clip_settings is not None else Clip_settings()
        self.uniform_scale = True
        self.animations_instance = None

    def add_keyframe(self, _property: Keyframe_property, time_offset: Union[int, str], value: float) -> "Visual_segment":
        """Create a keyframe for the given property and add it to the keyframe list.

        Args:
            _property (`Keyframe_property`): The property to animate
            time_offset (`int` or `str`): Keyframe time offset in microseconds; strings are parsed with `tim()`.
            value (`float`): Property value at `time_offset`

        Raises:
            `ValueError`: Attempted to set both `uniform_scale` and one of `scale_x` / `scale_y`
        """
        if (_property == Keyframe_property.scale_x or _property == Keyframe_property.scale_y) and self.uniform_scale:
            self.uniform_scale = False
        elif _property == Keyframe_property.uniform_scale:
            if not self.uniform_scale:
                raise ValueError("Cannot set uniform_scale when scale_x or scale_y has already been set")
            _property = Keyframe_property.scale_x

        if isinstance(time_offset, str): time_offset = tim(time_offset)

        for kf_list in self.common_keyframes:
            if kf_list.keyframe_property == _property:
                kf_list.add_keyframe(time_offset, value)
                return self
        kf_list = Keyframe_list(_property)
        kf_list.add_keyframe(time_offset, value)
        self.common_keyframes.append(kf_list)
        return self

    def export_json(self) -> Dict[str, Any]:
        """Export JSON data common to all visual segments"""
        json_dict = super().export_json()
        json_dict.update({
            "clip": self.clip_settings.export_json(),
            "uniform_scale": {"on": self.uniform_scale, "value": 1.0},
        })
        return json_dict
