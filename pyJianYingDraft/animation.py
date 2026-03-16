"""Video and text animation classes"""

import uuid

from typing import Union, Optional
from typing import Literal, Dict, List, Any

from .time_util import Timerange

from .metadata.animation_meta import Animation_meta
from .metadata import Intro_type, Outro_type, Group_animation_type
from .metadata import CapCut_Intro_type, CapCut_Outro_type, CapCut_Group_animation_type
from .metadata import Text_intro, Text_outro, Text_loop_anim
from .metadata import CapCut_Text_intro, CapCut_Text_loop_anim, CapCut_Text_outro


class Animation:
    """A single video or text animation effect"""

    name: str
    """Animation name — defaults to the effect's own name"""
    effect_id: str
    """Animation effect id provided by CapCut/JianYing"""
    animation_type: str
    """Animation type string; defined in subclasses"""
    resource_id: str
    """Resource id provided by CapCut/JianYing"""

    start: int
    """Offset from the segment start, in microseconds"""
    duration: int
    """Animation duration in microseconds"""

    is_video_animation: bool
    """True for video animations, False for text animations; defined in subclasses"""

    def __init__(self, animation_meta: Animation_meta, start: int, duration: int):
        self.name = animation_meta.title
        self.effect_id = animation_meta.effect_id
        self.resource_id = animation_meta.resource_id

        self.start = start
        self.duration = duration

    def export_json(self) -> Dict[str, Any]:
        return {
            "anim_adjust_params": None,
            "platform": "all",
            "panel": "video" if self.is_video_animation else "",
            "material_type": "video" if self.is_video_animation else "sticker",

            "name": self.name,
            "id": self.effect_id,
            "type": self.animation_type,
            "resource_id": self.resource_id,

            "start": self.start,
            "duration": self.duration,
            # path and request_id are intentionally omitted
        }


class Video_animation(Animation):
    """A video animation effect"""

    animation_type: Literal["in", "out", "group"]

    def __init__(self, animation_type: Union[Intro_type, Outro_type, Group_animation_type, CapCut_Intro_type, CapCut_Outro_type, CapCut_Group_animation_type],
                 start: int, duration: int):
        super().__init__(animation_type.value, start, duration)

        if ((isinstance(animation_type, Intro_type) or isinstance(animation_type, CapCut_Intro_type))):
            self.animation_type = "in"
        elif isinstance(animation_type, Outro_type) or isinstance(animation_type, CapCut_Outro_type):
            self.animation_type = "out"
        elif isinstance(animation_type, Group_animation_type) or isinstance(animation_type, CapCut_Group_animation_type):
            self.animation_type = "group"

        self.is_video_animation = True


class Text_animation(Animation):
    """A text animation effect"""

    animation_type: Literal["in", "out", "loop"]

    def __init__(self, animation_type: Union[Text_intro, Text_outro, Text_loop_anim, CapCut_Text_intro, CapCut_Text_outro, CapCut_Text_loop_anim],
                 start: int, duration: int):
        super().__init__(animation_type.value, start, duration)

        if (isinstance(animation_type, Text_intro) or isinstance(animation_type, CapCut_Text_intro)):
            self.animation_type = "in"
        elif (isinstance(animation_type, Text_outro) or isinstance(animation_type, CapCut_Text_outro)):
            self.animation_type = "out"
        elif (isinstance(animation_type, Text_loop_anim) or isinstance(animation_type, CapCut_Text_loop_anim)):
            self.animation_type = "loop"

        self.is_video_animation = False


class Segment_animations:
    """A collection of animations attached to a segment.

    For video segments: intro, outro, or group animations.
    For text segments: intro, outro, or loop animations.
    """

    animation_id: str
    """Globally unique id for this animation collection, auto-generated"""

    animations: List[Animation]
    """List of animations in this collection"""

    def __init__(self):
        self.animation_id = uuid.uuid4().hex
        self.animations = []

    def get_animation_trange(self, animation_type: Literal["in", "out", "group", "loop"]) -> Optional[Timerange]:
        """Return the time range of the animation with the given type, or None if not found"""
        for animation in self.animations:
            if animation.animation_type == animation_type:
                return Timerange(animation.start, animation.duration)
        return None

    def add_animation(self, animation: Union[Video_animation, Text_animation]) -> None:
        # Only one animation of each type is allowed (e.g. no two intro animations)
        if animation.animation_type in [ani.animation_type for ani in self.animations]:
            raise ValueError(f"An animation of type '{animation.animation_type}' already exists on this segment")

        if isinstance(animation, Video_animation):
            # Group animations cannot coexist with intro/outro animations
            if any(ani.animation_type == "group" for ani in self.animations):
                raise ValueError("A group animation already exists on this segment; no other animations can be added")
            if animation.animation_type == "group" and len(self.animations) > 0:
                raise ValueError("Cannot add a group animation when other animations already exist on this segment")
        elif isinstance(animation, Text_animation):
            if any(ani.animation_type == "loop" for ani in self.animations):
                raise ValueError(
                    "A loop animation already exists on this segment. "
                    "To combine loop and intro/outro animations, add intro/outro first."
                )

        self.animations.append(animation)

    def export_json(self) -> Dict[str, Any]:
        return {
            "id": self.animation_id,
            "type": "sticker_animation",
            "multi_language_current": "none",
            "animations": [animation.export_json() for animation in self.animations]
        }
