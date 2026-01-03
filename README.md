# cuemcp

Cue MCP server/adapter.

This project implements an MCP server that communicates with a UI/client via a shared SQLite database.

## Install

```bash
pip install cuemcp
```

## Run

```bash
cuemcp
```

## How it works

- **DB path**: `~/.cue/cue.db`
- **Core tables**:
  - `cue_requests` (server -> UI/client)
  - `cue_responses` (UI/client -> server)

The server writes requests into SQLite and polls for responses.

## Use with cue-console

- **1) Start `cuemcp`** (this MCP server)
- **2) Start `cue-console`** (Next.js UI) and make sure it points to the same DB path (`~/.cue/cue.db`)
- **3) Interact**: the server writes requests; the console shows pending items and writes responses

## Simulator (optional)

If you don't want to run the UI, you can use a terminal simulator client:

```bash
cuemcp-sim
```

## Dev

```bash
uv sync
uv run cuemcp
```

## Notes

- **Do not commit tokens**: if you use a `.secret` / `.secrets/*` file for publish tokens, keep it ignored.
