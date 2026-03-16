"""
Settings package entry point — exports all configuration values.
"""

# Re-export all config from local module (which already imports from env and base modules)
from .local import *

__all__ = [
    "IS_CAPCUT_ENV",
    "API_KEYS",
    "MODEL_CONFIG",
    "PURCHASE_LINKS",
    "LICENSE_CONFIG"
]


def get_platform_info():
    """
    Return platform metadata used by Script_file.dumps() for CapCut drafts.

    Returns:
        dict: Platform info dict, or None when running in JianYing mode.
    """
    if not IS_CAPCUT_ENV:
        return None

    return {
        "app_id": 359289,
        "app_source": "cc",
        "app_version": "6.5.0",
        "device_id": "c4ca4238a0b923820dcc509a6f75849b",
        "hard_disk_id": "307563e0192a94465c0e927fbc482942",
        "mac_address": "c3371f2d4fb02791c067ce44d8fb4ed5",
        "os": "mac",
        "os_version": "15.5"
    }
