import os
import json
import math
from copy import deepcopy

from typing import Optional, Literal, Union, overload
from typing import Type, Dict, List, Any

from . import util
from . import exceptions
from .template_mode import ImportedTrack, EditableTrack, ImportedMediaTrack, ImportedTextTrack, Shrink_mode, Extend_mode, import_track
from .time_util import Timerange, tim, srt_tstamp
from .local_materials import Video_material, Audio_material
from .segment import Base_segment, Speed, Clip_settings
from .audio_segment import Audio_segment, Audio_fade, Audio_effect
from .video_segment import Video_segment, Sticker_segment, Segment_animations, Video_effect, Transition, Filter, BackgroundFilling
from .effect_segment import Effect_segment, Filter_segment
from .text_segment import Text_segment, Text_style, TextBubble, Text_border, Text_background, TextEffect
from .track import Track_type, Base_track, Track

from settings.local import IS_CAPCUT_ENV
from .metadata import Video_scene_effect_type, Video_character_effect_type, Filter_type

class Script_material:
    """Materials section of a draft file"""

    audios: List[Audio_material]
    """Audio material list"""
    videos: List[Video_material]
    """Video material list"""
    stickers: List[Dict[str, Any]]
    """Sticker material list"""
    texts: List[Dict[str, Any]]
    """Text material list"""

    audio_effects: List[Audio_effect]
    """Audio effect list"""
    audio_fades: List[Audio_fade]
    """Audio fade-in/fade-out effect list"""
    animations: List[Segment_animations]
    """Animation material list"""
    video_effects: List[Video_effect]
    """Video effect list"""

    speeds: List[Speed]
    """Speed change list"""
    masks: List[Dict[str, Any]]
    """Mask list"""
    transitions: List[Transition]
    """Transition effect list"""
    filters: List[Union[Filter, TextBubble]]
    """Filter / text-effect / text-bubble list, exported under 'effects'"""
    canvases: List[BackgroundFilling]
    """Background filling list"""

    def __init__(self):
        self.audios = []
        self.videos = []
        self.stickers = []
        self.texts = []

        self.audio_effects = []
        self.audio_fades = []
        self.animations = []
        self.video_effects = []

        self.speeds = []
        self.masks = []
        self.transitions = []
        self.filters = []
        self.canvases = []

    @overload
    def __contains__(self, item: Union[Video_material, Audio_material]) -> bool: ...
    @overload
    def __contains__(self, item: Union[Audio_fade, Audio_effect]) -> bool: ...
    @overload
    def __contains__(self, item: Union[Segment_animations, Video_effect, Transition, Filter]) -> bool: ...

    def __contains__(self, item) -> bool:
        if isinstance(item, Video_material):
            return item.material_id in [video.material_id for video in self.videos]
        elif isinstance(item, Audio_material):
            return item.material_id in [audio.material_id for audio in self.audios]
        elif isinstance(item, Audio_fade):
            return item.fade_id in [fade.fade_id for fade in self.audio_fades]
        elif isinstance(item, Audio_effect):
            return item.effect_id in [effect.effect_id for effect in self.audio_effects]
        elif isinstance(item, Segment_animations):
            return item.animation_id in [ani.animation_id for ani in self.animations]
        elif isinstance(item, Video_effect):
            return item.global_id in [effect.global_id for effect in self.video_effects]
        elif isinstance(item, Transition):
            return item.global_id in [transition.global_id for transition in self.transitions]
        elif isinstance(item, Filter):
            return item.global_id in [filter_.global_id for filter_ in self.filters]
        else:
            raise TypeError("Invalid argument type '%s'" % type(item))

    def export_json(self) -> Dict[str, List[Any]]:
        result = {
            "ai_translates": [],
            "audio_balances": [],
            "audio_effects": [effect.export_json() for effect in self.audio_effects],
            "audio_fades": [fade.export_json() for fade in self.audio_fades],
            "audio_track_indexes": [],
            "audios": [audio.export_json() for audio in self.audios],
            "beats": [],
            "canvases": [canvas.export_json() for canvas in self.canvases],
            "chromas": [],
            "color_curves": [],
            "digital_humans": [],
            "drafts": [],
            "effects": [_filter.export_json() for _filter in self.filters],
            "flowers": [],
            "green_screens": [],
            "handwrites": [],
            "hsl": [],
            "images": [],
            "log_color_wheels": [],
            "loudnesses": [],
            "manual_deformations": [],
            "material_animations": [ani.export_json() for ani in self.animations],
            "material_colors": [],
            "multi_language_refs": [],
            "placeholders": [],
            "plugin_effects": [],
            "primary_color_wheels": [],
            "realtime_denoises": [],
            "shapes": [],
            "smart_crops": [],
            "smart_relights": [],
            "sound_channel_mappings": [],
            "speeds": [spd.export_json() for spd in self.speeds],
            "stickers": self.stickers,
            "tail_leaders": [],
            "text_templates": [],
            "texts": self.texts,
            "time_marks": [],
            "transitions": [transition.export_json() for transition in self.transitions],
            "video_effects": [effect.export_json() for effect in self.video_effects],
            "video_trackings": [],
            "videos": [video.export_json() for video in self.videos],
            "vocal_beautifys": [],
            "vocal_separations": []
        }

        # Use common_mask (CapCut) or masks (JianYing) depending on IS_CAPCUT_ENV
        if IS_CAPCUT_ENV:
            result["common_mask"] = self.masks
        else:
            result["masks"] = self.masks

        return result

class Script_file:
    """CapCut/JianYing draft file; most public APIs are defined here"""

    save_path: Optional[str]
    """Draft file save path; only valid in template mode"""
    content: Dict[str, Any]
    """Draft file content"""

    width: int
    """Video width in pixels"""
    height: int
    """Video height in pixels"""
    fps: int
    """Video frame rate"""
    duration: int
    """Total video duration in microseconds"""

    materials: Script_material
    """Materials section of the draft file"""
    tracks: Dict[str, Track]
    """Track information"""

    imported_materials: Dict[str, List[Dict[str, Any]]]
    """Imported material information"""
    imported_tracks: List[Track]
    """Imported track information"""

    TEMPLATE_FILE = "draft_content_template.json"

    def __init__(self, width: int, height: int, fps: int = 30):
        """Create a new CapCut/JianYing draft

        Args:
            width (int): Video width in pixels
            height (int): Video height in pixels
            fps (int, optional): Video frame rate. Defaults to 30.
        """
        self.save_path = None

        self.width = width
        self.height = height
        self.fps = fps
        self.duration = 0

        self.materials = Script_material()
        self.tracks = {}

        self.imported_materials = {}
        self.imported_tracks = []

        with open(os.path.join(os.path.dirname(__file__), self.TEMPLATE_FILE), "r", encoding="utf-8") as f:
            self.content = json.load(f)

    @staticmethod
    def load_template(json_path: str) -> "Script_file":
        """Load a draft template from a JSON file

        Args:
            json_path (str): Path to the JSON file

        Raises:
            `FileNotFoundError`: The JSON file does not exist
        """
        obj = Script_file(**util.provide_ctor_defaults(Script_file))
        obj.save_path = json_path
        if not os.path.exists(json_path):
            raise FileNotFoundError("JSON file '%s' does not exist" % json_path)
        with open(json_path, "r", encoding="utf-8") as f:
            obj.content = json.load(f)

        util.assign_attr_with_json(obj, ["fps", "duration"], obj.content)
        util.assign_attr_with_json(obj, ["width", "height"], obj.content["canvas_config"])

        obj.imported_materials = deepcopy(obj.content["materials"])
        obj.imported_tracks = [import_track(track_data, obj.imported_materials) for track_data in obj.content["tracks"]]

        return obj

    def add_material(self, material: Union[Video_material, Audio_material]) -> "Script_file":
        """Add a material to the draft"""
        if material in self.materials:  # material already exists
            return self
        if isinstance(material, Video_material):
            self.materials.videos.append(material)
        elif isinstance(material, Audio_material):
            self.materials.audios.append(material)
        else:
            raise TypeError("Unsupported material type: '%s'" % type(material))
        return self

    def add_track(self, track_type: Track_type, track_name: Optional[str] = None, *,
                  mute: bool = False,
                  relative_index: int = 0, absolute_index: Optional[int] = None) -> "Script_file":
        """Add a track of the specified type and name to the draft, with optional layer ordering

        Note: video segments on the primary video track (the bottom-most video track) must start at 0s,
        otherwise CapCut/JianYing will force-align them to 0s.

        To avoid ambiguity, omitting the name is only allowed when creating the first track of a given type.

        Args:
            track_type (Track_type): Track type
            track_name (str, optional): Track name. May be omitted only when creating the first track of this type.
            mute (bool, optional): Whether the track is muted. Defaults to False.
            relative_index (int, optional): Layer position relative to tracks of the same type; higher values are closer to the foreground. Defaults to 0.
            absolute_index (int, optional): Absolute layer position; higher values are closer to the foreground.
                This parameter directly overrides the `render_index` of the corresponding segments and is intended for advanced users.
                Cannot be used together with `relative_index`.

        Raises:
            `NameError`: A track of this type already exists and no name was specified, or a track with the given name already exists
        """

        if track_name is None:
            if track_type in [track.track_type for track in self.tracks.values()]:
                raise NameError("A track of type '%s' already exists; specify a name for the new track to avoid ambiguity" % track_type)
            track_name = track_type.name
        if track_name in [track.name for track in self.tracks.values()]:
            print("A track named '%s' already exists" % track_name)
            return self

        render_index = track_type.value.render_index + relative_index
        if absolute_index is not None:
            render_index = absolute_index

        self.tracks[track_name] = Track(track_type, track_name, render_index, mute)
        return self

    def get_track(self, segment_type: Type[Base_segment], track_name: Optional[str]) -> Track:
        # Track name specified
        if track_name is not None:
            if track_name not in self.tracks:
                raise NameError("No track named '%s' exists" % track_name)
            return self.tracks[track_name]
        # Find the unique track of the matching type
        count = sum([1 for track in self.tracks.values() if track.track_type == segment_type])
        if count == 0: raise exceptions.TrackNotFound(f"No track accepting '{segment_type}' was found")
        if count > 1: raise NameError(f"Multiple tracks accepting '{segment_type}' found; specify a track name")

        return next(track for track in self.tracks.values() if track.accept_segment_type == segment_type)

    def _get_track_and_imported_track(self, segment_type: Type[Base_segment], track_name: Optional[str]) -> List[Track]:
        """Get all tracks of the specified type (including both regular and imported tracks)

        Args:
            segment_type (Type[Base_segment]): Segment type
            track_name (Optional[str]): Track name; if specified, only that track is returned

        Returns:
            List[Track]: List of tracks matching the criteria

        Raises:
            NameError: A track name was specified but no matching track was found
        """
        result_tracks = []

        # If a track name was specified
        if track_name is not None:
            # Search in regular tracks
            if track_name in self.tracks:
                result_tracks.append(self.tracks[track_name])
            # Search in imported tracks
            for track in self.imported_tracks:
                if track.name == track_name:
                    result_tracks.append(track)
            if not result_tracks:
                raise NameError("No track named '%s' exists" % track_name)
        else:
            # Search regular tracks for those accepting this segment type
            for track in self.tracks.values():
                if track.accept_segment_type == segment_type:
                    result_tracks.append(track)
            # Search imported tracks for those accepting this segment type
            for track in self.imported_tracks:
                if track.accept_segment_type == segment_type:
                    result_tracks.append(track)
            if not result_tracks:
                raise NameError("No track accepting '%s' was found" % segment_type)
            if len(result_tracks) > 1:
                raise NameError("Multiple tracks accepting '%s' found; specify a track name" % segment_type)

        return result_tracks

    def add_segment(self, segment: Union[Video_segment, Sticker_segment, Audio_segment, Text_segment],
                    track_name: Optional[str] = None) -> "Script_file":
        """Add a segment to the specified track

        Args:
            segment (`Video_segment`, `Sticker_segment`, `Audio_segment`, or `Text_segment`): The segment to add
            track_name (`str`, optional): Name of the target track. May be omitted when there is only one track of this type.

        Raises:
            `NameError`: The specified track was not found, or `track_name` is required but was not provided
            `TypeError`: The segment type does not match the track type
            `SegmentOverlap`: The new segment overlaps an existing segment
        """
        tracks = self._get_track_and_imported_track(type(segment), track_name)
        target = tracks[0]

        # Add to track and update duration
        target.add_segment(segment)
        self.duration = max(self.duration, segment.end)

        # Automatically add related materials
        if isinstance(segment, Video_segment):
            # Entry/exit animations and similar
            if (segment.animations_instance is not None) and (segment.animations_instance not in self.materials):
                self.materials.animations.append(segment.animations_instance)
            # Effects
            for effect in segment.effects:
                if effect not in self.materials:
                    self.materials.video_effects.append(effect)
            # Filters
            for filter_ in segment.filters:
                if filter_ not in self.materials:
                    self.materials.filters.append(filter_)
            # Mask
            if segment.mask is not None:
                self.materials.masks.append(segment.mask.export_json())
            # Transition
            if (segment.transition is not None) and (segment.transition not in self.materials):
                self.materials.transitions.append(segment.transition)
            # Background filling
            if segment.background_filling is not None:
                self.materials.canvases.append(segment.background_filling)

            self.materials.speeds.append(segment.speed)
        elif isinstance(segment, Sticker_segment):
            self.materials.stickers.append(segment.export_material())
        elif isinstance(segment, Audio_segment):
            # Fade in/out
            if (segment.fade is not None) and (segment.fade not in self.materials):
                self.materials.audio_fades.append(segment.fade)
            # Effects
            for effect in segment.effects:
                if effect not in self.materials:
                    self.materials.audio_effects.append(effect)
            self.materials.speeds.append(segment.speed)
        elif isinstance(segment, Text_segment):
            # Entry/exit animations and similar
            if (segment.animations_instance is not None) and (segment.animations_instance not in self.materials):
                self.materials.animations.append(segment.animations_instance)
            # Bubble effect
            if segment.bubble is not None:
                self.materials.filters.append(segment.bubble)
            # Stylized-font text effect
            if segment.effect is not None:
                self.materials.filters.append(segment.effect)
            # Font style
            self.materials.texts.append(segment.export_material())

        # Add segment material
        if isinstance(segment, (Video_segment, Audio_segment)):
            self.add_material(segment.material_instance)

        return self

    def add_effect(self, effect: Union[Video_scene_effect_type, Video_character_effect_type],
                   t_range: Timerange, track_name: Optional[str] = None, *,
                   params: Optional[List[Optional[float]]] = None) -> "Script_file":
        """Add an effect segment to the specified effect track

        Args:
            effect (`Video_scene_effect_type` or `Video_character_effect_type`): Effect type
            t_range (`Timerange`): Time range of the effect segment
            track_name (`str`, optional): Name of the target track. May be omitted when there is only one effect track.
            params (`List[Optional[float]]`, optional): Effect parameter list; items that are missing or None use the default value.
                The value range (0–100) matches what is shown in CapCut/JianYing. Refer to the enum member annotations
                for the parameters available for a given effect type and their order.

        Raises:
            `NameError`: The specified track was not found, or `track_name` is required but was not provided
            `TypeError`: The specified track is not an effect track
            `ValueError`: The new segment overlaps an existing segment, too many parameters were provided, or a parameter value is out of range.
        """
        target = self.get_track(Effect_segment, track_name)

        # Add to track and update duration
        segment = Effect_segment(effect, t_range, params)
        target.add_segment(segment)
        self.duration = max(self.duration, t_range.start + t_range.duration)

        # Automatically add related materials
        if segment.effect_inst not in self.materials:
            self.materials.video_effects.append(segment.effect_inst)
        return self

    def add_filter(self, filter_meta: Filter_type, t_range: Timerange,
                   track_name: Optional[str] = None, intensity: float = 100.0) -> "Script_file":
        """Add a filter segment to the specified filter track

        Args:
            filter_meta (`Filter_type`): Filter type
            t_range (`Timerange`): Time range of the filter segment
            track_name (`str`, optional): Name of the target track. May be omitted when there is only one filter track.
            intensity (`float`, optional): Filter intensity (0–100). Only effective when the chosen filter supports intensity adjustment. Defaults to 100.

        Raises:
            `NameError`: The specified track was not found, or `track_name` is required but was not provided
            `TypeError`: The specified track is not a filter track
            `ValueError`: The new segment overlaps an existing segment
        """
        target = self.get_track(Filter_segment, track_name)

        # Add to track and update duration
        segment = Filter_segment(filter_meta, t_range, intensity / 100.0)  # convert to 0–1 range
        target.add_segment(segment)
        self.duration = max(self.duration, t_range.end)

        # Automatically add related materials
        self.materials.filters.append(segment.material)
        return self

    def import_srt(self, srt_content: str, track_name: str, *,
                   time_offset: Union[str, float] = 0.0,
                   style_reference: Optional[Text_segment] = None,
                   text_style: Text_style = Text_style(size=5, align=1),
                   clip_settings: Optional[Clip_settings] = Clip_settings(transform_y=-0.8),
                   border: Optional[Text_border] = None,
                   background: Optional[Text_background] = None,
                   bubble: Optional[TextBubble] = None,
                   effect: Optional[TextEffect] = None) -> "Script_file":
        """Import subtitles from an SRT file, optionally using a `Text_segment` as a style reference

        Note: by default the `clip_settings` attribute of the reference segment is NOT used;
        pass `clip_settings=None` explicitly if you want to inherit it from the reference.

        Args:
            srt_content (`str`): SRT subtitle content or a local file path
            track_name (`str`): Name of the text track to import into; created automatically if it does not exist
            style_reference (`Text_segment`, optional): A text segment to use as a style reference; its style will be applied if provided.
            time_offset (`Union[str, float]`, optional): Overall time offset for subtitles in microseconds. Defaults to 0.
            text_style (`Text_style`, optional): Subtitle style; mimics the default CapCut/JianYing import style and is overridden by `style_reference`.
            clip_settings (`Clip_settings`, optional): Image adjustment settings; mimics the default CapCut/JianYing import settings
                and overrides the `style_reference` settings unless set to `None`.
            border (`Text_border`, optional): Stroke settings; by default the stroke settings from the style reference are not modified.
            background (`Text_background`, optional): Background settings; by default the background settings from the style reference are not modified.
            bubble (`TextBubble`, optional): Bubble effect; no bubble effect is added by default.
            effect (`TextEffect`, optional): Stylized-font text effect; no text effect is added by default.

        Raises:
            `NameError`: A track with the same name already exists
            `TypeError`: Track type mismatch
        """
        if style_reference is None and clip_settings is None:
            raise ValueError("When no style_reference is provided, clip_settings must be specified")

        time_offset = tim(time_offset)
        # Check whether track_name exists in self.tracks or self.imported_tracks
        track_exists = (track_name in self.tracks) or any(track.name == track_name for track in self.imported_tracks)
        if not track_exists:
            self.add_track(Track_type.text, track_name, relative_index=999)  # Place above all existing text tracks

        # Check whether srt_content is a local file path
        if os.path.exists(srt_content):
            with open(srt_content, "r", encoding="utf-8-sig") as srt_file:
                lines = srt_file.readlines()
        else:
            # Split content into lines directly
            lines = srt_content.splitlines()

        def __add_text_segment(text: str, t_range: Timerange) -> None:
            fixed_width = -1
            if self.width < self.height:  # Portrait
                fixed_width = int(1080 * 0.6)
            else:  # Landscape
                fixed_width = int(1920 * 0.7)

            if style_reference:
                seg = Text_segment.create_from_template(text, t_range, style_reference)
                if clip_settings is not None:
                    seg.clip_settings = deepcopy(clip_settings)
                # Copy other optional attributes
                if border:
                    seg.border = deepcopy(border)
                if background:
                    seg.background = deepcopy(background)
                if bubble:
                    seg.bubble = deepcopy(bubble)
                if effect:
                    seg.effect = deepcopy(effect)
                # Set fixed width
                seg.fixed_width = fixed_width
            else:
                seg = Text_segment(text, t_range, style=text_style, clip_settings=clip_settings,
                                  border=border, background=background,
                                  fixed_width=fixed_width)
                # Add bubble and text effects
                if bubble:
                    seg.bubble = deepcopy(bubble)
                if effect:
                    seg.effect = deepcopy(effect)
            # If bubble or text effects are present, add them to the materials list
            if bubble:
                self.materials.filters.append(bubble)
            if effect:
                self.materials.filters.append(effect)
            self.add_segment(seg, track_name)

        index = 0
        text: str = ""
        text_trange: Timerange
        read_state: Literal["index", "timestamp", "content"] = "index"
        while index < len(lines):
            line = lines[index].strip()
            if read_state == "index":
                if len(line) == 0:
                    index += 1
                    continue
                if not line.isdigit():
                    raise ValueError("Expected a number at line %d, got '%s'" % (index+1, line))
                index += 1
                read_state = "timestamp"
            elif read_state == "timestamp":
                # Parse timestamp
                start_str, end_str = line.split(" --> ")
                start, end = srt_tstamp(start_str), srt_tstamp(end_str)
                text_trange = Timerange(start + time_offset, end - start)

                index += 1
                read_state = "content"
            elif read_state == "content":
                # End of content block — create segment
                if len(line) == 0:
                    __add_text_segment(text.strip(), text_trange)

                    text = ""
                    read_state = "index"
                else:
                    text += line + "\n"
                index += 1

        # Add the final segment
        if len(text) > 0:
            __add_text_segment(text.strip(), text_trange)

        return self

    def get_imported_track(self, track_type: Literal[Track_type.video, Track_type.audio, Track_type.text],
                           name: Optional[str] = None, index: Optional[int] = None) -> Track:
        """Get an imported track of the specified type for performing replacements on it

        Using the track name for filtering is recommended when the name is known.

        Args:
            track_type (`Track_type.video`, `Track_type.audio` or `Track_type.text`): Track type;
                currently only audio, video, and text tracks are supported.
            name (`str`, optional): Track name; if not specified, filtering by name is skipped.
            index (`int`, optional): Index of the track within **imported tracks of the same type**,
                where 0 is the bottom-most track. If not specified, filtering by index is skipped.

        Raises:
            `TrackNotFound`: No track matching the criteria was found
            `AmbiguousTrack`: Multiple tracks matching the criteria were found
        """
        tracks_of_same_type: List[Track] = []
        for track in self.imported_tracks:
            if track.track_type == track_type:
                assert isinstance(track, Track)
                tracks_of_same_type.append(track)

        ret: List[Track] = []
        for ind, track in enumerate(tracks_of_same_type):
            if (name is not None) and (track.name != name): continue
            if (index is not None) and (ind != index): continue
            ret.append(track)

        if len(ret) == 0:
            raise exceptions.TrackNotFound(
                "No track matching criteria: track_type=%s, name=%s, index=%s" % (track_type, name, index))
        if len(ret) > 1:
            raise exceptions.AmbiguousTrack(
                "Multiple tracks matching criteria: track_type=%s, name=%s, index=%s" % (track_type, name, index))

        return ret[0]

    def import_track(self, source_file: "Script_file", track: EditableTrack, *,
                     offset: Union[str, int] = 0,
                     new_name: Optional[str] = None, relative_index: Optional[int] = None) -> "Script_file":
        """Import an `EditableTrack` into the current `Script_file`, e.g. importing a specific text or
        video track from a template draft into the draft currently being edited

        Note: this method preserves the IDs of all segments and their materials, so importing the same
        track into the same draft more than once is not supported.

        Args:
            source_file (`Script_file`): Source file containing the track to import
            track (`EditableTrack`): The track to import; obtainable via `get_imported_track`.
            offset (`str | int`, optional): Time offset for the track in microseconds; can be an integer
                microsecond value or a time string (e.g. "1s"). Defaults to no offset.
            new_name (`str`, optional): New track name; defaults to the source track name.
            relative_index (`int`, optional): Relative index for adjusting the render layer of the imported track.
                Defaults to preserving the original layer.
        """
        # Copy the original track structure directly, adjusting render layer as needed
        imported_track = deepcopy(track)
        if relative_index is not None:
            imported_track.render_index = track.track_type.value.render_index + relative_index
        if new_name is not None:
            imported_track.name = new_name

        # Apply offset
        offset_us = tim(offset)
        if offset_us != 0:
            for seg in imported_track.segments:
                seg.target_timerange.start = max(0, seg.target_timerange.start + offset_us)
        self.imported_tracks.append(imported_track)

        # Collect all material IDs that need to be copied
        material_ids = set()
        segments: List[Dict[str, Any]] = track.raw_data.get("segments", [])
        for segment in segments:
            # Primary material ID
            material_id = segment.get("material_id")
            if material_id:
                material_ids.add(material_id)

            # Material IDs in extra_material_refs
            extra_refs: List[str] = segment.get("extra_material_refs", [])
            material_ids.update(extra_refs)

        # Copy materials
        for material_type, material_list in source_file.imported_materials.items():
            for material in material_list:
                if material.get("id") in material_ids:
                    self.imported_materials[material_type].append(deepcopy(material))
                    material_ids.remove(material.get("id"))

        assert len(material_ids) == 0, "The following materials were not found: %s" % material_ids

        # Update total duration
        self.duration = max(self.duration, track.end_time)

        return self

    def replace_material_by_name(self, material_name: str, material: Union[Video_material, Audio_material],
                                 replace_crop: bool = False) -> "Script_file":
        """Replace the material with the given name, affecting all segments that reference it

        This method does not change the duration or source range (`source_timerange`) of the
        corresponding segments, making it especially suitable for image materials.

        Args:
            material_name (`str`): Name of the material to replace
            material (`Video_material` or `Audio_material`): New material; currently only video and audio are supported
            replace_crop (`bool`, optional): Whether to replace the crop settings of the original material.
                Defaults to False. Only applicable to video materials.

        Raises:
            `MaterialNotFound`: No material of the same type as the new material was found with the given name
            `AmbiguousMaterial`: Multiple materials of the same type as the new material were found with the given name
        """
        video_mode = isinstance(material, Video_material)
        # Find the material
        target_json_obj: Optional[Dict[str, Any]] = None
        target_material_list = self.imported_materials["videos" if video_mode else "audios"]
        name_key = "material_name" if video_mode else "name"
        for mat in target_material_list:
            if mat[name_key] == material_name:
                if target_json_obj is not None:
                    raise exceptions.AmbiguousMaterial(
                        "Multiple materials named '%s' of type '%s' were found" % (material_name, type(material)))
                target_json_obj = mat
        if target_json_obj is None:
            raise exceptions.MaterialNotFound("No material named '%s' of type '%s' was found" % (material_name, type(material)))

        # Update material information
        target_json_obj.update({name_key: material.material_name, "path": material.path, "duration": material.duration})
        if video_mode:
            target_json_obj.update({"width": material.width, "height": material.height, "material_type": material.material_type})
            if replace_crop:
                target_json_obj.update({"crop": material.crop_settings.export_json()})

        return self

    def replace_material_by_seg(self, track: EditableTrack, segment_index: int, material: Union[Video_material, Audio_material],
                                source_timerange: Optional[Timerange] = None, *,
                                handle_shrink: Shrink_mode = Shrink_mode.cut_tail,
                                handle_extend: Union[Extend_mode, List[Extend_mode]] = Extend_mode.cut_material_tail) -> "Script_file":
        """Replace the material for the specified segment on the given audio/video track;
        variable-speed segments are not currently supported

        Args:
            track (`EditableTrack`): The track whose segment material should be replaced; obtained via `get_imported_track`
            segment_index (`int`): Zero-based index of the segment to replace
            material (`Video_material` or `Audio_material`): New material; must match the type of the original material
            source_timerange (`Timerange`, optional): Time range to clip from the new material;
                defaults to the full duration, or the original segment duration for image materials.
            handle_shrink (`Shrink_mode`, optional): How to handle the case where the new material is shorter than the original;
                defaults to trimming the tail so the segment length matches the material.
            handle_extend (`Extend_mode` or `List[Extend_mode]`, optional): How to handle the case where the new material
                is longer than the original; modes are tried in order until one succeeds or an exception is raised.
                Defaults to trimming the material tail to keep the segment length unchanged.

        Raises:
            `IndexError`: `segment_index` is out of range
            `TypeError`: The track or material type is incorrect
            `ExtensionFailed`: Handling of a longer new material failed
        """
        if not isinstance(track, ImportedMediaTrack):
            raise TypeError("The specified track (type %s) does not support material replacement" % track.track_type)
        if not 0 <= segment_index < len(track):
            raise IndexError("Segment index %d is out of range [0, %d)" % (segment_index, len(track)))
        if not track.check_material_type(material):
            raise TypeError("Material type %s does not match track type %s", (type(material), track.track_type))
        seg = track.segments[segment_index]

        if isinstance(handle_extend, Extend_mode):
            handle_extend = [handle_extend]
        if source_timerange is None:
            if isinstance(material, Video_material) and (material.material_type == "photo"):
                source_timerange = Timerange(0, seg.duration)
            else:
                source_timerange = Timerange(0, material.duration)

        # Handle time range changes
        track.process_timerange(segment_index, source_timerange, handle_shrink, handle_extend)

        # Finally, replace the material reference
        track.segments[segment_index].material_id = material.material_id
        self.add_material(material)

        # TODO: update total duration
        return self

    def replace_text(self, track: EditableTrack, segment_index: int, text: Union[str, List[str]],
                     recalc_style: bool = True) -> "Script_file":
        """Replace the text content of the specified segment on the given text track;
        supports both regular text segments and text template segments

        Args:
            track (`EditableTrack`): The text track whose segment text should be replaced; obtained via `get_imported_track`
            segment_index (`int`): Zero-based index of the segment to replace
            text (`str` or `List[str]`): New text content; for text templates a list of strings should be provided.
            recalc_style (`bool`): Whether to recalculate font-style range distribution, i.e. adjust the ranges of
                each font style to preserve the original proportions as closely as possible. Defaults to True.

        Raises:
            `IndexError`: `segment_index` is out of range
            `TypeError`: The track type is incorrect
            `ValueError`: The number of text strings does not match the text template
        """
        if not isinstance(track, ImportedTextTrack):
            raise TypeError("The specified track (type %s) does not support text content replacement" % track.track_type)
        if not 0 <= segment_index < len(track):
            raise IndexError("Segment index %d is out of range [0, %d)" % (segment_index, len(track)))

        def __recalc_style_range(old_len: int, new_len: int, styles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
            """Adjust font-style range distribution"""
            new_styles: List[Dict[str, Any]] = []
            for style in styles:
                start = math.ceil(style["range"][0] / old_len * new_len)
                end = math.ceil(style["range"][1] / old_len * new_len)
                style["range"] = [start, end]
                if start != end:
                    new_styles.append(style)
            return new_styles

        replaced: bool = False
        material_id: str = track.segments[segment_index].material_id
        # Try replacing in text materials
        for mat in self.imported_materials["texts"]:
            if mat["id"] != material_id:
                continue

            if isinstance(text, list):
                if len(text) != 1:
                    raise ValueError(f"A regular text segment can only have one text content, but the replacement is {text}")
                text = text[0]

            content = json.loads(mat["content"])
            if recalc_style:
                content["styles"] = __recalc_style_range(len(content["text"]), len(text), content["styles"])
            content["text"] = text
            mat["content"] = json.dumps(content, ensure_ascii=False)
            replaced = True
            break
        if replaced:
            return self

        # Try replacing in text templates
        for template in self.imported_materials["text_templates"]:
            if template["id"] != material_id:
                continue

            resources = template["text_info_resources"]
            if isinstance(text, str):
                text = [text]
            if len(text) > len(resources):
                raise ValueError(f"Text template '{template['name']}' has {len(resources)} text segments but {len(text)} replacement strings were provided")

            for sub_material_id, new_text in zip(map(lambda x: x["text_material_id"], resources), text):
                for mat in self.imported_materials["texts"]:
                    if mat["id"] != sub_material_id:
                        continue

                    if isinstance(mat["content"], str):
                        mat["content"] = new_text
                    else:
                        content = json.loads(mat["content"])
                        if recalc_style:
                            content["styles"] = __recalc_style_range(len(content["text"]), len(new_text), content["styles"])
                        content["text"] = new_text
                        mat["content"] = json.dumps(content, ensure_ascii=False)
                    break
            replaced = True
            break

        assert replaced, f"No material found for segment {material_id}"

        return self

    def inspect_material(self) -> None:
        """Output metadata for stickers, text bubbles, and text effects imported into the draft"""
        print("Sticker materials:")
        for sticker in self.imported_materials["stickers"]:
            print("\tResource id: %s '%s'" % (sticker["resource_id"], sticker.get("name", "")))

        print("Text bubble effects:")
        for effect in self.imported_materials["effects"]:
            if effect["type"] == "text_shape":
                print("\tEffect id: %s ,Resource id: %s '%s'" %
                      (effect["effect_id"], effect["resource_id"], effect.get("name", "")))

        print("Stylized-font text effects:")
        for effect in self.imported_materials["effects"]:
            if effect["type"] == "text_effect":
                print("\tResource id: %s '%s'" % (effect["resource_id"], effect.get("name", "")))

    def dumps(self) -> str:
        """Export the draft file content as a JSON string"""
        self.content["fps"] = self.fps
        self.content["duration"] = self.duration
        self.content["canvas_config"] = {"width": self.width, "height": self.height, "ratio": "original"}
        self.content["materials"] = self.materials.export_json()

        self.content["last_modified_platform"] = {
            "app_id": 359289,
            "app_source": "cc",
            "app_version": "6.5.0",
            "device_id": "c4ca4238a0b923820dcc509a6f75849b",
            "hard_disk_id": "307563e0192a94465c0e927fbc482942",
            "mac_address": "c3371f2d4fb02791c067ce44d8fb4ed5",
            "os": "mac",
            "os_version": "15.5"
        }

        self.content["platform"] = {
            "app_id": 359289,
            "app_source": "cc",
            "app_version": "6.5.0",
            "device_id": "c4ca4238a0b923820dcc509a6f75849b",
            "hard_disk_id": "307563e0192a94465c0e927fbc482942",
            "mac_address": "c3371f2d4fb02791c067ce44d8fb4ed5",
            "os": "mac",
            "os_version": "15.5"
        }

        # Merge imported materials
        for material_type, material_list in self.imported_materials.items():
            if material_type not in self.content["materials"]:
                self.content["materials"][material_type] = material_list
            else:
                self.content["materials"][material_type].extend(material_list)

        # Sort tracks and export
        track_list: List[Base_track] = list(self.tracks.values())
        track_list.extend(self.imported_tracks)
        track_list.sort(key=lambda track: track.render_index)
        self.content["tracks"] = [track.export_json() for track in track_list]

        return json.dumps(self.content, ensure_ascii=False, indent=4)

    def dump(self, file_path: str) -> None:
        """Write the draft file content to a file"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(self.dumps())

    def save(self) -> None:
        """Save the draft file to the path it was opened from; only available in template mode

        Raises:
            `ValueError`: Not in template mode
        """
        if self.save_path is None:
            raise ValueError("No save path is set; possibly not in template mode")
        self.dump(self.save_path)
