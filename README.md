
# cuemcp

_Cue MCP server/adapter — a tiny, opinionated bridge between an MCP runtime and a human-in-the-loop UI._

[![PyPI](https://img.shields.io/pypi/v/cuemcp?label=cuemcp&color=0B7285)](https://pypi.org/project/cuemcp/)
[![Repo](https://img.shields.io/badge/repo-cue--mcp-111827)](https://github.com/nmhjklnm/cue-mcp)
![License](https://img.shields.io/badge/license-Apache--2.0-1E40AF)

---

## The pitch (10 seconds)

`cuemcp` runs an MCP server that **hands control back to a human**.

It does this via a shared SQLite mailbox:

```text
MCP Server  ──writes──▶  ~/.cue/cue.db  ──reads/writes──▶  cue-console (UI)
             ◀─polls──                         ◀─responds──
```

---

## Quickstart (1 minute)

### 1) Install

```bash
pip install cuemcp
```

### 2) Start the MCP server

```bash
cuemcp
```

### 3) Start a client

- **Option A — cue-console (recommended)**
  - Run the Next.js UI and point it at the same DB path: `~/.cue/cue.db`.
- **Option B — terminal simulator**

```bash
cuemcp-sim
```

---

## How it works (the contract)

### Storage

- **DB path**: `~/.cue/cue.db`
- **Core tables**:
  - `cue_requests` — server ➜ UI/client
  - `cue_responses` — UI/client ➜ server

### Semantics

- Server writes a request row.
- UI/client writes a response row.
- Server waits/polls until a response exists.

This keeps the integration simple: no websockets, no extra daemon, just a shared mailbox.

---

## Pairing with cue-console

**Rule #1:** both sides must agree on the same DB location.

- Start `cuemcp`.
- Start `cue-console`.
- Confirm `cue-console` is reading/writing `~/.cue/cue.db`.

When the UI shows pending items, you’re effectively watching the MCP server “wait for a human”.

---

## Dev workflow (uv)

```bash
uv sync
uv run cuemcp
```

---

## Safety

- **Do not commit tokens.**
  - If you store publish credentials in a project file (e.g. `.secret`), ensure it stays ignored.
- **Do not share tokens in chat.**

---

## Links

- **PyPI**: [pypi.org/project/cuemcp](https://pypi.org/project/cuemcp/)
- **Repo**: [github.com/nmhjklnm/cue-mcp](https://github.com/nmhjklnm/cue-mcp)
