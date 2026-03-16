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

The codebase has three layers:

### 1. FastAPI Layer (`app/`)
- `app/__init__.py` — app factory: registers all routers and mounts FastAPI-MCP at `/mcp`
- `app/routes/` — thin router files, one per domain (video, audio, text, image, effect, draft, meta)
- `app/controllers/` — business logic called by routes
- `app/schemas/` — Pydantic request/response models

### 2. Implementation Layer (root `*_impl.py` files)
Bridge between controllers and the core library. Each file handles one operation type (e.g., `add_video_impl.py`, `add_text_impl.py`). Also includes:
- `draft_cache.py` — in-memory store mapping `draft_id` → `Script_file` object
- `save_task_cache.py` — background task status tracking for async save operations
- `downloader.py` — downloads remote media URLs to local temp files
- `util.py` — color conversion (hex→RGB), URL hashing, draft URL generation

### 3. Core Draft Library (`pyJianYingDraft/`)
Handles CapCut draft file format (ZIP-based JSON). Key classes:
- `Script_file` — represents the entire video project; the central object passed through caching
- `draft_folder.py` — writes the final draft ZIP to disk
- `segment.py`, `video_segment.py`, `audio_segment.py`, `text_segment.py`, `effect_segment.py` — segment types
- `metadata/` — static JSON metadata for effects, animations, fonts, transitions, masks

## Configuration (`config.json`)

Key fields:
- `is_capcut_env` — `true` for CapCut International, `false` for JianYing (China)
- `draft_domain` — base URL used when generating draft preview URLs
- `port` — server listen port
- `is_upload_draft` — whether to upload finished drafts to Aliyun OSS
- `oss_config` / `mp4_oss_config` — Aliyun OSS credentials (leave empty if not uploading)

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

## Typical API Workflow

1. `POST /create_draft` → returns `draft_id`
2. `POST /add_video`, `/add_audio`, `/add_text`, etc. with `draft_id`
3. `POST /save_draft` with `draft_id` and target `draft_folder`
4. Copy the generated `dfd_*` folder to the CapCut drafts directory

See `example.py` for comprehensive usage examples.
