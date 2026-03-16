# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CapCutAPI is a Python FastAPI server that provides programmatic access to CapCut (剪映) draft file creation and manipulation. It exposes REST HTTP APIs and an MCP (Model Context Protocol) endpoint to automate video editing workflows.

## Setup & Running

```bash
# Install dependencies (requires Python 3.8.20)
pip install -r requirements.txt

# Copy and edit configuration
cp config.json.example config.json

# Start server (default port from config, typically 9000–9001)
python main.py
```

**Prerequisites:** `ffmpeg` must be installed and on the system PATH.

## Linting

```bash
flake8 .
```

Config is in `.flake8`: max line length 140, metadata files excluded.

## Architecture

The codebase has four layers stacked in this call order:

```
HTTP Request
    ↓
app/routes/<domain>_routes.py     — FastAPI router (defines endpoints, delegates to controller)
    ↓
app/controllers/<domain>_controller.py  — validates input, calls impl function
    ↓
<operation>_impl.py               — orchestrates core library: loads draft from cache,
                                    builds segment/material objects, adds to tracks
    ↓
pyJianYingDraft/                  — core draft-file library; builds/serializes CapCut JSON
    ↓
draft_cache.py                    — in-memory LRU store (draft_id → Script_file); shared state
```

### 1. FastAPI Layer (`app/`)

- `app/__init__.py` — `create_app()` factory: registers all routers and mounts FastAPI-MCP at `/mcp`
- `app/routes/` — thin router files per domain (video, audio, text, image, effect, draft, meta); each just maps HTTP verbs to controller calls
- `app/controllers/` — domain logic: validates request schemas, calls impl functions, wraps results in `{"success": bool, "output": ..., "error": ...}`
- `app/schemas/` — Pydantic request/response models

### 2. Implementation Layer (root `*_impl.py` files)

Each file handles one operation. Pattern:
1. Load `Script_file` from `draft_cache` by `draft_id`
2. If media URL provided, call `downloader.py` to fetch to a local temp path
3. Create material objects (`Video_material`, `Audio_material`, etc.)
4. Create segment objects (`Video_segment`, `Audio_segment`, `Text_segment`, etc.)
5. Get or create a named `Track` on the `Script_file`
6. Call `track.add_segment(segment)` — raises `SegmentOverlap` on conflict
7. Return result dict with updated `draft_id`

Supporting utilities:
- `draft_cache.py` — `DraftCache` singleton; `get(draft_id)` → `Script_file`; `put(draft_id, script)` stores it
- `save_task_cache.py` — tracks status of async `save_draft` operations (background thread)
- `downloader.py` — downloads remote URLs or copies local paths to a temp dir; returns local path
- `util.py` — hex→RGB conversion, URL hash helpers

### 3. Core Draft Library (`pyJianYingDraft/`)

Handles the CapCut/JianYing draft file format. The format is a folder containing `draft_info.json` (a large JSON blob).

**Central object:** `Script_file` in `script_file.py`
- Holds all tracks and a `Script_material` bag (videos, audios, texts, effects, filters, etc.)
- `add_track(track_type, name)` — creates a named track of the right type
- `get_track(name)` — retrieves existing track by name
- `add_segment(track, segment)` — validates segment type, adds to track, registers associated materials
- `save()` — serializes everything to `draft_info.json` inside the draft folder

**Segment hierarchy:**
```
Base_segment
└── Media_segment (has source_timerange, speed, volume, extra_material_refs)
    ├── Visual_segment (adds clip_settings, animations_instance, keyframes)
    │   ├── Video_segment  (mask, transition, background)
    │   ├── Text_segment   (text, style, border, background, bubble, effect)
    │   └── Sticker_segment
    └── Audio_segment      (fade, effects list)
Effect_segment / Filter_segment (applied to a timerange, not a media file)
```

**Track types** (`Track_type` enum in `track.py`): `video`, `audio`, `text`, `effect`, `filter`, `sticker`, `adjust`. Each has a `render_index` (higher = foreground).

**Template mode** (`template_mode.py`): `Script_file.load_template()` opens an existing draft for editing. `ImportedMediaTrack` wraps imported tracks; segments can be shrunk/extended via `Shrink_mode`/`Extend_mode` policies.

**Keyframes** (`keyframe.py`): `Keyframe_property` enum lists animatable properties (position, scale, rotation, alpha, volume, etc.). `add_keyframe(property, time_offset, value)` on any `Visual_segment` or `Audio_segment`.

**Metadata** (`pyJianYingDraft/metadata/`): Static enum/dataclass definitions for every built-in CapCut effect, animation, font, filter, transition, mask type. **Do not modify** — these are data files that must match CapCut's internal IDs exactly.

### 4. Configuration (`settings/`)

- `settings/__init__.py` — loads `config.json` at import time, exposes `IS_CAPCUT_ENV`, `PORT`, `OSS_CONFIG`, etc.
- `settings/local.py` — `Settings` Pydantic model (schema for `config.json`)
- `IS_CAPCUT_ENV = True` → CapCut International behavior; `False` → JianYing (China) behavior (affects export automation)

## MCP Integration

The server auto-exposes all FastAPI endpoints via `fastapi-mcp` at `http://localhost:<port>/mcp`. To connect from Claude or Cursor:

```json
{
    "mcpServers": {
        "capcut-mcp": {
            "type": "http",
            "url": "http://localhost:9000/mcp"
        }
    }
}
```

## End-to-End Request Flow Example

`POST /add_text` with `{draft_id, text, start, duration, font_size, ...}`:

1. `app/routes/text_routes.py` — router receives POST, calls `add_text_controller(request)`
2. `app/controllers/text_controller.py` — validates schema, calls `add_text_impl(**kwargs)`
3. `add_text_impl.py`:
   - Loads `Script_file` from `draft_cache.get(draft_id)`
   - Builds `Text_style(size=font_size, color=..., align=...)`
   - Builds `Text_segment(text, Timerange(start, duration), style=style, ...)`
   - Gets or creates a text `Track` via `script.get_track(track_name)` or `script.add_track(Track_type.text, ...)`
   - Calls `track.add_segment(segment)` — raises `SegmentOverlap` if time overlaps
   - Stores updated `Script_file` back via `draft_cache.put(draft_id, script)`
4. Returns `{"success": true, "output": {"draft_id": "..."}, "error": ""}`

`POST /save_draft` with `{draft_id, draft_folder}`:
1. Controller calls `save_draft_impl(draft_id, draft_folder)`
2. Loads `Script_file` from cache, calls `script.save(draft_folder)` (writes `dfd_*/draft_info.json`)
3. The draft folder can be copied to CapCut's drafts directory for immediate use

## Key Conventions

- **Chinese strings in pyJianYingDraft**: Some strings like `"场景音"`, `"音色"`, `"声音成曲"` in `audio_segment.py` are **CapCut draft file format values** — they must remain Chinese for JianYing compatibility.
- **UI automation strings**: `"暂不启用"`, `"剪映专业版"`, `"导出"` in `jianying_controller.py` are Chinese app window/control names used for UI automation — must not be translated.
- **Font names like `"文轩体"`, `"思源中宋"`**: These are CapCut font identifier strings (data values), not translatable text.
- All new code should use English for comments, docstrings, error messages, and log strings.

## Typical API Workflow

1. `POST /create_draft` → returns `draft_id`
2. `POST /add_video`, `/add_audio`, `/add_text`, etc. with `draft_id`
3. `POST /save_draft` with `draft_id` and target `draft_folder`
4. Copy the generated `dfd_*` folder to the CapCut drafts directory

See `example.py` for comprehensive usage examples.
