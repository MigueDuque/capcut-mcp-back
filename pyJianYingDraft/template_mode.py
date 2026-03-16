"""Classes and functions related to template mode"""

from enum import Enum
from copy import deepcopy

from . import util
from . import exceptions
from .time_util import Timerange
from .segment import Base_segment
from .track import Base_track, Track_type, Track
from .local_materials import Video_material, Audio_material
from .video_segment import Video_segment, Clip_settings
from .audio_segment import Audio_segment
from .keyframe import Keyframe_list, Keyframe_property, Keyframe
from .metadata import Audio_scene_effect_type, Tone_effect_type, Speech_to_song_type, Effect_param_instance

from typing import List, Dict, Any

class Shrink_mode(Enum):
    """Strategy for handling material shrinkage when replacing a material"""

    cut_head = "cut_head"
    """Trim the head — move the segment start forward"""
    cut_tail = "cut_tail"
    """Trim the tail — move the segment end backward"""

    cut_tail_align = "cut_tail_align"
    """Trim the tail and close the gap — shift subsequent segments forward"""

    shrink = "shrink"
    """Shrink inward from both ends toward the midpoint"""

class Extend_mode(Enum):
    """Strategy for handling material extension when replacing a material"""

    cut_material_tail = "cut_material_tail"
    """Trim the material tail (overrides source_timerange), keeping segment length unchanged; always succeeds"""

    extend_head = "extend_head"
    """Extend the head — try to move the segment start backward; fails if it would overlap the previous segment"""
    extend_tail = "extend_tail"
    """Extend the tail — try to move the segment end forward; fails if it would overlap the next segment"""

    push_tail = "push_tail"
    """Extend the tail, shifting subsequent segments as needed; always succeeds"""

class ImportedSegment(Base_segment):
    """An imported segment"""

    raw_data: Dict[str, Any]
    """Raw JSON data"""

    __DATA_ATTRS = ["material_id", "target_timerange"]
    def __init__(self, json_data: Dict[str, Any]):
        self.raw_data = deepcopy(json_data)

        util.assign_attr_with_json(self, self.__DATA_ATTRS, json_data)

    def export_json(self) -> Dict[str, Any]:
        json_data = deepcopy(self.raw_data)
        json_data.update(util.export_attr_to_json(self, self.__DATA_ATTRS))
        return json_data

class ImportedMediaSegment(ImportedSegment):
    """An imported video or audio segment"""

    source_timerange: Timerange
    """Time range clipped from the source material"""

    __DATA_ATTRS = ["source_timerange"]
    def __init__(self, json_data: Dict[str, Any]):
        super().__init__(json_data)

        util.assign_attr_with_json(self, self.__DATA_ATTRS, json_data)

    def export_json(self) -> Dict[str, Any]:
        json_data = super().export_json()
        json_data.update(util.export_attr_to_json(self, self.__DATA_ATTRS))
        return json_data


class ImportedTrack(Base_track):
    """A track imported in template mode"""

    raw_data: Dict[str, Any]
    """Raw track data"""

    def __init__(self, json_data: Dict[str, Any]):
        self.track_type = Track_type.from_name(json_data["type"])
        self.name = json_data["name"]
        self.track_id = json_data["id"]
        self.render_index = max([int(seg["render_index"]) for seg in json_data["segments"]], default=0)

        self.raw_data = deepcopy(json_data)

    def export_json(self) -> Dict[str, Any]:
        ret = deepcopy(self.raw_data)
        ret.update({
            "name": self.name,
            "id": self.track_id
        })
        return ret

class EditableTrack(ImportedTrack):
    """An imported, editable track (audio, video, or text)"""

    segments: List[ImportedSegment]
    """List of segments on this track"""

    def __len__(self):
        return len(self.segments)

    @property
    def start_time(self) -> int:
        """Track start time in microseconds"""
        if len(self.segments) == 0:
            return 0
        return self.segments[0].target_timerange.start

    @property
    def end_time(self) -> int:
        """Track end time in microseconds"""
        if len(self.segments) == 0:
            return 0
        return self.segments[-1].target_timerange.end

    def export_json(self) -> Dict[str, Any]:
        ret = super().export_json()
        # Write render_index into each segment
        segment_exports = [seg.export_json() for seg in self.segments]
        for seg in segment_exports:
            seg["render_index"] = self.render_index
        ret["segments"] = segment_exports
        return ret

class ImportedTextTrack(EditableTrack):
    """An imported text track in template mode"""

    def __init__(self, json_data: Dict[str, Any]):
        super().__init__(json_data)
        self.segments = [ImportedSegment(seg) for seg in json_data["segments"]]

class ImportedMediaTrack(EditableTrack):
    """An imported audio/video track in template mode"""

    segments: List[ImportedMediaSegment]
    """List of segments on this track"""

    def __init__(self, json_data: Dict[str, Any]):
        super().__init__(json_data)
        self.segments = [ImportedMediaSegment(seg) for seg in json_data["segments"]]

    def check_material_type(self, material: object) -> bool:
        """Check whether the material type matches the track type"""
        if self.track_type == Track_type.video and isinstance(material, Video_material):
            return True
        if self.track_type == Track_type.audio and isinstance(material, Audio_material):
            return True
        return False

    def process_timerange(self, seg_index: int, src_timerange: Timerange,
                          shrink: Shrink_mode, extend: List[Extend_mode]) -> None:
        """Handle time range changes when replacing a material"""
        seg = self.segments[seg_index]
        new_duration = src_timerange.duration

        # Duration decreased
        delta_duration = abs(new_duration - seg.duration)
        if new_duration < seg.duration:
            if shrink == Shrink_mode.cut_head:
                seg.start += delta_duration
            elif shrink == Shrink_mode.cut_tail:
                seg.duration -= delta_duration
            elif shrink == Shrink_mode.cut_tail_align:
                seg.duration -= delta_duration
                for i in range(seg_index+1, len(self.segments)):  # shift subsequent segments forward by the same amount (preserving gaps)
                    self.segments[i].start -= delta_duration
            elif shrink == Shrink_mode.shrink:
                seg.duration -= delta_duration
                seg.start += delta_duration // 2
            else:
                raise ValueError(f"Unsupported shrink mode: {shrink}")
        # Duration increased
        elif new_duration > seg.duration:
            success_flag = False
            prev_seg_end = int(0) if seg_index == 0 else self.segments[seg_index-1].target_timerange.end
            next_seg_start = int(1e15) if seg_index == len(self.segments)-1 else self.segments[seg_index+1].start
            for mode in extend:
                if mode == Extend_mode.extend_head:
                    if seg.start - delta_duration >= prev_seg_end:
                        seg.start -= delta_duration
                        success_flag = True
                elif mode == Extend_mode.extend_tail:
                    if seg.target_timerange.end + delta_duration <= next_seg_start:
                        seg.duration += delta_duration
                        success_flag = True
                elif mode == Extend_mode.push_tail:
                    shift_duration = max(0, seg.target_timerange.end + delta_duration - next_seg_start)
                    seg.duration += delta_duration
                    if shift_duration > 0:  # push subsequent segments back only if necessary
                        for i in range(seg_index+1, len(self.segments)):
                            self.segments[i].start += shift_duration
                    success_flag = True
                elif mode == Extend_mode.cut_material_tail:
                    src_timerange.duration = seg.duration
                    success_flag = True
                else:
                    raise ValueError(f"Unsupported extend mode: {mode}")

                if success_flag:
                    break
            if not success_flag:
                raise exceptions.ExtensionFailed(f"Failed to extend segment to {new_duration}μs; attempted modes: {extend}")

        # Write the source time range
        seg.source_timerange = src_timerange

def import_track(json_data: Dict[str, Any], imported_materials: Dict[str, Any] = None) -> Track:
    """Import a track.
    :param json_data: Raw track data
    :param imported_materials: Already-imported materials dict, used to create material instances for segments
    """
    track_type = Track_type.from_name(json_data["type"])
    # Create a new Track instance, preserving all original attributes
    track = Track(
        track_type=track_type,
        name=json_data["name"],
        render_index=max([int(seg.get("render_index", 0)) for seg in json_data.get("segments", [])], default=0),
        mute=bool(json_data.get("attribute", 0))
    )

    # Use the original track id
    track.track_id = json_data.get("id")

    # Import all segments if the track type supports modification
    if track_type.value.allow_modify and imported_materials:
        for segment_data in json_data.get("segments", []):
            material_id = segment_data.get("material_id")
            material = None

            # Process keyframe data
            common_keyframes = []
            for kf_list_data in segment_data.get("common_keyframes", []):
                # Create keyframe list
                kf_list = Keyframe_list(Keyframe_property(kf_list_data["property_type"]))
                kf_list.list_id = kf_list_data["id"]

                # Add keyframes
                for kf_data in kf_list_data["keyframe_list"]:
                    keyframe = Keyframe(kf_data["time_offset"], kf_data["values"][0])
                    keyframe.kf_id = kf_data["id"]
                    keyframe.values = kf_data["values"]
                    kf_list.keyframes.append(keyframe)

                common_keyframes.append(kf_list)

            # Find the matching material by track type
            if track_type == Track_type.video:
                # Look up video material from imported_materials
                for video_material in imported_materials.get("videos", []):
                    if video_material["id"] == material_id:
                        material = Video_material.from_dict(video_material)
                        break

                if material:
                    # Create video segment
                    segment = Video_segment(
                        material=material,
                        target_timerange=Timerange(
                            start=segment_data["target_timerange"]["start"],
                            duration=segment_data["target_timerange"]["duration"]
                        ),
                        source_timerange=Timerange(
                            start=segment_data["source_timerange"]["start"],
                            duration=segment_data["source_timerange"]["duration"]
                        ),
                        speed=segment_data.get("speed", 1.0),
                        clip_settings=Clip_settings(
                            transform_x=segment_data["clip"]["transform"]["x"],
                            transform_y=segment_data["clip"]["transform"]["y"],
                            scale_x=segment_data["clip"]["scale"]["x"],
                            scale_y=segment_data["clip"]["scale"]["y"]
                        )
                    )
                    segment.volume = segment_data.get("volume", 1.0)
                    segment.visible = segment_data.get("visible", True)
                    segment.common_keyframes = common_keyframes
                    track.segments.append(segment)

            elif track_type == Track_type.audio:
                # Look up audio material from imported_materials
                for audio_material in imported_materials.get("audios", []):
                    if audio_material["id"] == material_id:
                        material = Audio_material.from_dict(audio_material)
                        break

                if material:
                    # Create audio segment
                    segment = Audio_segment(
                        material=material,
                        target_timerange=Timerange(
                            start=segment_data["target_timerange"]["start"],
                            duration=segment_data["target_timerange"]["duration"]
                        ),
                        volume=segment_data.get("volume", 1.0)
                    )
                    # Add audio effects
                    if "audio_effects" in imported_materials and imported_materials["audio_effects"]:
                        effect_data = imported_materials["audio_effects"][0]
                        # Look up the effect type by resource ID
                        for effect_type in Audio_scene_effect_type:
                            if effect_type.value.resource_id == effect_data["resource_id"]:
                                # Map param values from 0–1 to 0–100
                                params = []
                                for param in effect_data["audio_adjust_params"]:
                                    params.append(param["value"] * 100)
                                segment.add_effect(effect_type, params,effect_id=effect_data["id"])
                                break
                    segment.common_keyframes = common_keyframes
                    track.segments.append(segment)
            else:
                # Other segment types: keep as-is
                segment = ImportedSegment(segment_data)
                segment.common_keyframes = common_keyframes
                track.segments.append(segment)

    return track
