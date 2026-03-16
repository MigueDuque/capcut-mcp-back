"""Custom exception classes"""


class TrackNotFound(NameError):
    """No track matching the specified criteria was found"""

class AmbiguousTrack(ValueError):
    """Multiple tracks matching the specified criteria were found"""

class SegmentOverlap(ValueError):
    """New segment overlaps with an existing segment on the track"""


class MaterialNotFound(NameError):
    """No material matching the specified criteria was found"""

class AmbiguousMaterial(ValueError):
    """Multiple materials matching the specified criteria were found"""


class ExtensionFailed(ValueError):
    """Failed to extend a segment while replacing a material"""


class DraftNotFound(NameError):
    """Draft not found"""

class AutomationError(Exception):
    """Automation operation failed"""

class ExportTimeout(Exception):
    """Export timed out"""
