# CapCut MCP Backend

REST API backend that exposes CapCut's draft editing capabilities 
via HTTP endpoints. Used as the backend layer for capcut-mcp-server-extended.

## Based on

Fork of [fancyboi999/capcut-mcp](https://github.com/fancyboi999/capcut-mcp),
originally written in Chinese. This fork refactors the codebase to English,
improves error messages, and optimizes the API structure.

## What it does

- Creates and manages CapCut draft projects
- Adds video, audio, image, and text tracks
- Applies effects, transitions, and keyframe animations
- Saves drafts directly to CapCut's local folder structure
- Exposes everything via a clean REST API on localhost:9001

## Stack

Python · FastAPI · pyJianYingDraft

## Related

- [capcut-mcp-server-extended](https://github.com/MigueDuque/capcut-mcp-server-extended) — MCP server that wraps this API for Claude Code