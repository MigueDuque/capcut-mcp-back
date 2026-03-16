"""
Local configuration module — loads settings from config.json.
"""

import os
import json

# Path to the configuration file
CONFIG_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

# Default: run in CapCut International mode
IS_CAPCUT_ENV = True

# Default domain for draft preview URLs
DRAFT_DOMAIN = "https://www.install-ai-guider.top"

# Default preview route
PREVIEW_ROUTER = "/draft/downloader"

# Whether to upload draft files to OSS after saving
IS_UPLOAD_DRAFT = False

# Server listen port
PORT = 9000

OSS_CONFIG = []
MP4_OSS_CONFIG = []

# Load overrides from config.json if it exists
if os.path.exists(CONFIG_FILE_PATH):
    try:
        with open(CONFIG_FILE_PATH, "r", encoding="utf-8") as f:
            local_config = json.load(f)

            # CapCut International vs JianYing (China)
            if "is_capcut_env" in local_config:
                IS_CAPCUT_ENV = local_config["is_capcut_env"]

            # Draft preview domain
            if "draft_domain" in local_config:
                DRAFT_DOMAIN = local_config["draft_domain"]

            # Server port
            if "port" in local_config:
                PORT = local_config["port"]

            # Preview route
            if "preview_router" in local_config:
                PREVIEW_ROUTER = local_config["preview_router"]

            # OSS upload toggle
            if "is_upload_draft" in local_config:
                IS_UPLOAD_DRAFT = local_config["is_upload_draft"]

            # Aliyun OSS config for draft ZIPs
            if "oss_config" in local_config:
                OSS_CONFIG = local_config["oss_config"]

            # Aliyun OSS config for MP4 exports
            if "mp4_oss_config" in local_config:
                MP4_OSS_CONFIG = local_config["mp4_oss_config"]

    except (json.JSONDecodeError, IOError):
        # Config file unreadable — fall back to defaults
        pass
