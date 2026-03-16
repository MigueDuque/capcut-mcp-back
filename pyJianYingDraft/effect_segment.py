"""Effect and filter segment classes"""

from typing import Union, Optional, List

from .time_util import Timerange
from .segment import Base_segment
from .video_segment import Video_effect, Filter

from .metadata import Video_scene_effect_type, Video_character_effect_type, Filter_type


class Effect_segment(Base_segment):
    """An effect segment placed on a dedicated effect track"""

    effect_inst: Video_effect
    """The underlying effect material.

    Automatically added to the materials list when the segment is placed on a track.
    """

    def __init__(self, effect_type: Union[Video_scene_effect_type, Video_character_effect_type],
                 target_timerange: Timerange, params: Optional[List[Optional[float]]] = None):
        self.effect_inst = Video_effect(effect_type, params, apply_target_type=2)  # global scope
        super().__init__(self.effect_inst.global_id, target_timerange)


class Filter_segment(Base_segment):
    """A filter segment placed on a dedicated filter track"""

    material: Filter
    """The underlying filter material.

    Automatically added to the materials list when the segment is placed on a track.
    """

    def __init__(self, meta: Filter_type, target_timerange: Timerange, intensity: float):
        self.material = Filter(meta.value, intensity)
        super().__init__(self.material.global_id, target_timerange)
