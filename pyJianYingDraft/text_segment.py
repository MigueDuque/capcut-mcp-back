"""Text segment and related classes"""

import json
import uuid
from copy import deepcopy
from math import cos, sin, radians

from typing import Dict, Tuple, Any
from typing import Union, Optional, Literal

from pyJianYingDraft.metadata.capcut_text_animation_meta import CapCut_Text_intro, CapCut_Text_outro, CapCut_Text_loop_anim

from .time_util import Timerange, tim
from .segment import Clip_settings, Visual_segment
from .animation import Segment_animations, Text_animation

from .metadata import Font_type, Effect_meta
from .metadata import Text_intro, Text_outro, Text_loop_anim


class Text_style:
    """Font style settings"""

    size: float
    """Font size"""

    bold: bool
    """Bold"""
    italic: bool
    """Italic"""
    underline: bool
    """Underline"""

    color: Tuple[float, float, float]
    """Font color as an RGB triple in [0, 1]"""
    alpha: float
    """Font opacity"""

    align: Literal[0, 1, 2]
    """Text alignment"""
    vertical: bool
    """Whether the text is laid out vertically"""

    letter_spacing: int
    """Letter spacing"""
    line_spacing: int
    """Line spacing"""

    def __init__(self, *, size: float = 8.0, bold: bool = False, italic: bool = False, underline: bool = False,
                 color: Tuple[float, float, float] = (1.0, 1.0, 1.0), alpha: float = 1.0,
                 align: Literal[0, 1, 2] = 0, vertical: bool = False,
                 letter_spacing: int = 0, line_spacing: int = 0):
        """
        Args:
            size (`float`, optional): Font size. Defaults to 8.0.
            bold (`bool`, optional): Bold. Defaults to False.
            italic (`bool`, optional): Italic. Defaults to False.
            underline (`bool`, optional): Underline. Defaults to False.
            color (`Tuple[float, float, float]`, optional): RGB color in [0, 1]. Defaults to white.
            alpha (`float`, optional): Opacity in [0, 1]. Defaults to 1.0 (opaque).
            align (`int`, optional): 0 = left, 1 = center, 2 = right. Defaults to left.
            vertical (`bool`, optional): Vertical layout. Defaults to False.
            letter_spacing (`int`, optional): Letter spacing (same scale as CapCut). Defaults to 0.
            line_spacing (`int`, optional): Line spacing (same scale as CapCut). Defaults to 0.
        """
        self.size = size
        self.bold = bold
        self.italic = italic
        self.underline = underline

        self.color = color
        self.alpha = alpha

        self.align = align
        self.vertical = vertical

        self.letter_spacing = letter_spacing
        self.line_spacing = line_spacing


class Text_border:
    """Text stroke (border) settings"""

    alpha: float
    """Stroke opacity"""
    color: Tuple[float, float, float]
    """Stroke color as an RGB triple in [0, 1]"""
    width: float
    """Stroke width"""

    def __init__(self, *, alpha: float = 1.0, color: Tuple[float, float, float] = (0.0, 0.0, 0.0), width: float = 40.0):
        """
        Args:
            alpha (`float`, optional): Stroke opacity in [0, 1]. Defaults to 1.0.
            color (`Tuple[float, float, float]`, optional): RGB color in [0, 1]. Defaults to black.
            width (`float`, optional): Stroke width (same scale as CapCut, range 0–100). Defaults to 40.0.
        """
        self.alpha = alpha
        self.color = color
        self.width = width / 100.0 * 0.2  # mapping may not be perfectly accurate

    def export_json(self) -> Dict[str, Any]:
        """Export JSON; placed inside the material content's styles array"""
        return {
            "content": {
                "solid": {
                    "alpha": self.alpha,
                    "color": list(self.color),
                }
            },
            "width": self.width
        }


class Text_background:
    """Text background settings"""

    style: Literal[0, 2]
    """Background style"""

    alpha: float
    """Background opacity"""
    color: str
    """Background color in '#RRGGBB' format"""
    round_radius: float
    """Background corner radius"""
    height: float
    """Background height"""
    width: float
    """Background width"""
    horizontal_offset: float
    """Background horizontal offset"""
    vertical_offset: float
    """Background vertical offset"""

    def __init__(self, *, color: str, style: Literal[1, 2] = 1, alpha: float = 1.0, round_radius: float = 0.0,
                 height: float = 0.14, width: float = 0.14,
                 horizontal_offset: float = 0.5, vertical_offset: float = 0.5):
        """
        Args:
            color (`str`): Background color in '#RRGGBB' format.
            style (`int`, optional): Background style (1 or 2, matching CapCut's two styles). Defaults to 1.
            alpha (`float`, optional): Opacity in [0, 1]. Defaults to 1.0.
            round_radius (`float`, optional): Corner radius in [0, 1]. Defaults to 0.0.
            height (`float`, optional): Height in [0, 1]. Defaults to 0.14.
            width (`float`, optional): Width in [0, 1]. Defaults to 0.14.
            horizontal_offset (`float`, optional): Horizontal offset in [0, 1]. Defaults to 0.5.
            vertical_offset (`float`, optional): Vertical offset in [0, 1]. Defaults to 0.5.
        """
        self.style = (0, 2)[style - 1]

        self.alpha = alpha
        self.color = color
        self.round_radius = round_radius
        self.height = height
        self.width = width
        self.horizontal_offset = horizontal_offset * 2 - 1
        self.vertical_offset = vertical_offset * 2 - 1

    def export_json(self) -> Dict[str, Any]:
        """Generate sub-JSON merged into Text_segment on export"""
        return {
            "background_style": self.style,
            "background_color": self.color,
            "background_alpha": self.alpha,
            "background_round_radius": self.round_radius,
            "background_height": self.height,
            "background_width": self.width,
            "background_horizontal_offset": self.horizontal_offset,
            "background_vertical_offset": self.vertical_offset,
        }


class Text_shadow:
    """Text drop-shadow settings"""

    alpha: float
    """Shadow opacity, 0–1"""
    color: str
    """Shadow color in '#RRGGBB' format"""
    angle: float
    """Shadow angle in degrees"""
    distance: float
    """Shadow distance"""
    smoothing: float
    """Shadow blur/smoothing, 0–1"""

    def __init__(self, *, alpha: float = 0.9, color: str = "#000000",
                 angle: float = -45.0, distance: float = 5.0, smoothing: float = 0.45):
        """
        Args:
            alpha (`float`, optional): Shadow opacity in [0, 1]. Defaults to 0.9.
            color (`str`, optional): Shadow color in '#RRGGBB' format. Defaults to black.
            angle (`float`, optional): Shadow angle in degrees. Defaults to -45.0.
            distance (`float`, optional): Shadow distance. Defaults to 5.0.
            smoothing (`float`, optional): Shadow blur in [0, 1]. Defaults to 0.45.
        """
        self.alpha = alpha
        self.color = color
        self.angle = angle
        self.distance = distance
        self.smoothing = smoothing

    def export_json(self) -> Dict[str, Any]:
        """Export JSON; merged into Text_segment material on export"""
        return {
            "has_shadow": True,
            "shadow_alpha": self.alpha,
            "shadow_angle": self.angle,
            "shadow_color": self.color,
            "shadow_distance": self.distance,
            "shadow_point": {
                "x": cos(radians(self.angle)) * self.distance / 10,
                "y": sin(radians(self.angle)) * self.distance / 10,
            },
            "shadow_smoothing": self.smoothing,
        }


class TextBubble:
    """Text bubble material (structurally identical to a filter material)"""

    global_id: str
    """Globally unique id, auto-generated"""

    effect_id: str
    resource_id: str

    def __init__(self, effect_id: str, resource_id: str):
        self.global_id = uuid.uuid4().hex
        self.effect_id = effect_id
        self.resource_id = resource_id

    def export_json(self) -> Dict[str, Any]:
        return {
            "apply_target_type": 0,
            "effect_id": self.effect_id,
            "id": self.global_id,
            "resource_id": self.resource_id,
            "type": "text_shape",
            "value": 1.0,
            # path and request_id are intentionally omitted
        }


class TextEffect(TextBubble):
    """Text stylized-font effect material (also structurally identical to a filter material)"""

    def export_json(self) -> Dict[str, Any]:
        ret = super().export_json()
        ret["type"] = "text_effect"
        ret["source_platform"] = 1
        return ret


class Text_segment(Visual_segment):
    """A text segment; currently supports basic font styling"""

    text: str
    """Text content"""
    font: Optional[Effect_meta]
    """Font type"""
    style: Text_style
    """Font style"""

    border: Optional[Text_border]
    """Stroke settings; None = no stroke"""
    background: Optional[Text_background]
    """Background settings; None = no background"""
    shadow: Optional[Text_shadow]
    """Drop-shadow settings; None = no shadow"""

    bubble: Optional[TextBubble]
    """Bubble effect; added to the materials list when the segment is placed on a track"""
    effect: Optional[TextEffect]
    """Stylized-font effect; added to the materials list when placed on a track (partial support)"""

    fixed_width: float
    """Fixed width in pixels; -1 = auto"""
    fixed_height: float
    """Fixed height in pixels; -1 = auto"""

    def __init__(self, text: str, timerange: Timerange, *,
                 font: Optional[Font_type] = None,
                 style: Optional[Text_style] = None, clip_settings: Optional[Clip_settings] = None,
                 border: Optional[Text_border] = None, background: Optional[Text_background] = None,
                 shadow: Optional[Text_shadow] = None,
                 fixed_width: int = -1, fixed_height: int = -1):
        """Create a text segment with optional font styling and image transforms.

        After creation, add to a track via `Script_file.add_segment`.

        Args:
            text (`str`): Text content
            timerange (`Timerange`): Time range on the track
            font (`Font_type`, optional): Font; defaults to the system font.
            style (`Text_style`, optional): Font style (size, color, alignment, opacity, etc.).
            clip_settings (`Clip_settings`, optional): Image transforms; defaults to no transformation.
            border (`Text_border`, optional): Stroke settings; defaults to no stroke.
            background (`Text_background`, optional): Background settings; defaults to no background.
            shadow (`Text_shadow`, optional): Drop-shadow settings; defaults to no shadow.
            fixed_width (`int`, optional): Fixed width in pixels; -1 = not fixed.
            fixed_height (`int`, optional): Fixed height in pixels; -1 = not fixed.
        """
        super().__init__(uuid.uuid4().hex, None, timerange, 1.0, 1.0, clip_settings=clip_settings)

        self.text = text
        self.font = font.value if font else None
        self.style = style or Text_style()
        self.border = border
        self.background = background
        self.shadow = shadow

        self.bubble = None
        self.effect = None

        self.fixed_width = fixed_width
        self.fixed_height = fixed_height

    @classmethod
    def create_from_template(cls, text: str, timerange: Timerange, template: "Text_segment") -> "Text_segment":
        """Create a new text segment by copying the style of an existing template segment"""
        new_segment = cls(text, timerange, style=deepcopy(template.style), clip_settings=deepcopy(template.clip_settings),
                          border=deepcopy(template.border), background=deepcopy(template.background),
                          shadow=deepcopy(template.shadow))
        new_segment.font = deepcopy(template.font)

        # Copy animations and effects
        if template.animations_instance:
            new_segment.animations_instance = deepcopy(template.animations_instance)
            new_segment.animations_instance.animation_id = uuid.uuid4().hex
            new_segment.extra_material_refs.append(new_segment.animations_instance.animation_id)
        if template.bubble:
            new_segment.add_bubble(template.bubble.effect_id, template.bubble.resource_id)
        if template.effect:
            new_segment.add_effect(template.effect.effect_id)

        return new_segment

    def add_animation(self, animation_type: Union[Text_intro, Text_outro, Text_loop_anim,
                                                  CapCut_Text_intro, CapCut_Text_outro, CapCut_Text_loop_anim],
                      duration: Union[str, float] = 500000) -> "Text_segment":
        """Add an intro, outro, or loop animation to this segment.

        Loop animations automatically fill the space not occupied by intro/outro animations.

        Note: if combining a loop animation with intro/outro animations,
        **add the intro/outro animations first**.

        Args:
            animation_type (`Text_intro`, `Text_outro` or `Text_loop_anim`): Animation type.
            duration (`str` or `float`, optional): Duration in microseconds (intro/outro only).
                Strings are parsed with `tim()`. Defaults to 0.5 seconds.
        """
        duration = min(tim(duration), self.target_timerange.duration)

        if (isinstance(animation_type, Text_intro) or isinstance(animation_type, CapCut_Text_intro)):
            start = 0
        elif (isinstance(animation_type, Text_outro) or isinstance(animation_type, CapCut_Text_outro)):
            start = self.target_timerange.duration - duration
        elif (isinstance(animation_type, Text_loop_anim) or isinstance(animation_type, CapCut_Text_loop_anim)):
            intro_trange = self.animations_instance and self.animations_instance.get_animation_trange("in")
            outro_trange = self.animations_instance and self.animations_instance.get_animation_trange("out")
            start = intro_trange.start if intro_trange else 0
            duration = self.target_timerange.duration - start - (outro_trange.duration if outro_trange else 0)
        else:
            raise TypeError("Invalid animation type %s" % type(animation_type))

        if self.animations_instance is None:
            self.animations_instance = Segment_animations()
            self.extra_material_refs.append(self.animations_instance.animation_id)

        self.animations_instance.add_animation(Text_animation(animation_type, start, duration))

        return self

    def add_bubble(self, effect_id: str, resource_id: str) -> "Text_segment":
        """Add a bubble effect using the given material ids.

        Material ids can be obtained from `Script_file.inspect_material`.

        Args:
            effect_id (`str`): Bubble effect_id
            resource_id (`str`): Bubble resource_id
        """
        self.bubble = TextBubble(effect_id, resource_id)
        self.extra_material_refs.append(self.bubble.global_id)
        return self

    def add_effect(self, effect_id: str) -> "Text_segment":
        """Add a stylized-font effect using the given effect id.

        The effect_id also serves as the resource_id.
        Material ids can be obtained from `Script_file.inspect_material`.

        Args:
            effect_id (`str`): Stylized-font effect_id
        """
        self.effect = TextEffect(effect_id, effect_id)
        self.extra_material_refs.append(self.effect.global_id)
        return self

    def export_material(self) -> Dict[str, Any]:
        """Export the material associated with this text segment (replaces a separate Text_material class)"""
        # Combine feature flags
        check_flag: int = 7
        if self.border:
            check_flag |= 8
        if self.background:
            check_flag |= 16
        if self.shadow:
            check_flag |= 32

        content_json = {
            "styles": [
                {
                    "fill": {
                        "alpha": 1.0,
                        "content": {
                            "render_type": "solid",
                            "solid": {
                                "alpha": self.style.alpha,
                                "color": list(self.style.color)
                            }
                        }
                    },
                    "range": [0, len(self.text)],
                    "size": self.style.size,
                    "bold": self.style.bold,
                    "italic": self.style.italic,
                    "underline": self.style.underline,
                    "strokes": [self.border.export_json()] if self.border else []
                }
            ],
            "text": self.text
        }
        if self.font:
            content_json["styles"][0]["font"] = {
                "id": self.font.resource_id,
                "path": "C:/%s.ttf" % self.font.name  # font file is not actually placed here
            }
        if self.effect:
            content_json["styles"][0]["effectStyle"] = {
                "id": self.effect.effect_id,
                "path": "C:"  # asset file is not actually placed here
            }

        if self.shadow:
            h = self.shadow.color.lstrip('#')
            shadow_rgb = [int(h[i:i+2], 16) / 255.0 for i in (0, 2, 4)]
            content_json["styles"][0]["shadows"] = [{
                "alpha": self.shadow.alpha,
                "blur": self.shadow.smoothing,
                "color": shadow_rgb,
                "offset_x": cos(radians(self.shadow.angle)) * self.shadow.distance,
                "offset_y": sin(radians(self.shadow.angle)) * self.shadow.distance,
            }]

        ret = {
            "id": self.material_id,
            "content": json.dumps(content_json, ensure_ascii=False),

            "typesetting": int(self.style.vertical),
            "alignment": self.style.align,
            "letter_spacing": self.style.letter_spacing * 0.05,
            "line_spacing": 0.02 + self.style.line_spacing * 0.05,

            "line_feed": 1,
            "line_max_width": 0.82,
            "force_apply_line_max_width": False,

            "check_flag": check_flag,

            "type": "text",

            "fixed_width": self.fixed_width,
            "fixed_height": self.fixed_height,

            # Blend (+4)
            # "global_alpha": 1.0,

            # Glow (+64) — tracked via extra_material_refs

            # Shadow (+32)
            # "has_shadow": False,
            # "shadow_alpha": 0.9,
            # "shadow_angle": -45.0,
            # "shadow_color": "",
            # "shadow_distance": 5.0,
            # "shadow_point": {"x": 0.636..., "y": -0.636...},
            # "shadow_smoothing": 0.45,

            # Global font settings — appear to be overridden by content
            # "font_category_id": "", "font_category_name": "", "font_id": "", ...

            # Also appear to be overridden by content
            # "text_alpha": 1.0, "text_color": "#FFFFFF", ...
        }

        if self.background:
            ret.update(self.background.export_json())
        if self.shadow:
            ret.update(self.shadow.export_json())

        return ret
