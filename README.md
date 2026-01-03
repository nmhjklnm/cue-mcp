# cuemcp

![cuemcp banner](assets/banner.png)

_An MCP service on top of HAP (Human Agent Protocol) — compose humans and agents into a team._

[![PyPI](https://img.shields.io/pypi/v/cuemcp?label=cuemcp&color=0B7285)](https://pypi.org/project/cuemcp/)
[![Repo](https://img.shields.io/badge/repo-cue--mcp-111827)](https://github.com/nmhjklnm/cue-mcp)
![License](https://img.shields.io/badge/license-Apache--2.0-1E40AF)

---

## The pitch (10 seconds)

`cuemcp` is an MCP service built on top of HAP (Human Agent Protocol): it lets you compose MCP-capable humans and agent components into a collaborating team.

In the long run, the “decision node” in that team can be a human, a human assistant agent, or any other coordinating agent.

---

## Quickstart (1 minute)

### Goal

Add `cuemcp` as a local `stdio` MCP server inside your agent/runtime.

Assumptions:

- You have `uv`.
- Your machine can run `uvx`.

### Claude Code

Claude Code can install local `stdio` MCP servers via `claude mcp add`.

```bash
claude mcp add --transport stdio cuemcp -- uvx --from cuemcp cuemcp
```

### Windsurf

Windsurf reads MCP config from `~/.codeium/mcp_config.json` and uses the Claude Desktop-compatible schema.

```json
{
  "mcpServers": {
    "cuemcp": {
      "command": "uvx",
      "args": ["--from", "cuemcp", "cuemcp"]
    }
  }
}
```

### Cursor

Cursor uses `mcp.json` for configuration, and the Cursor CLI (`cursor-agent`) can list and manage servers. The CLI uses the same MCP configuration as the editor.

```bash
cursor-agent mcp list
```

Create an `mcp.json` in your project (Cursor discovers configs with project → global → parent directory precedence) and add a `cuemcp` stdio server:

```json
{
  "mcpServers": {
    "cuemcp": {
      "command": "uvx",
      "args": ["--from", "cuemcp", "cuemcp"],
      "env": {}
    }
  }
}
```

### VS Code

VS Code MCP configuration uses a JSON file with `servers` and optional `inputs`.

```json
{
  "servers": {
    "cuemcp": {
      "type": "stdio",
      "command": "uvx",
      "args": ["--from", "cuemcp", "cuemcp"]
    }
  }
}
```

### Codex

Codex can register a local stdio MCP server via the CLI:

```bash
codex mcp add cuemcp -- uvx --from cuemcp cuemcp
```

For deeper configuration, Codex stores MCP servers in `~/.codex/config.toml`.

### Gemini CLI

Gemini CLI can add a local stdio MCP server via:

```bash
gemini mcp add cuemcp uvx --from cuemcp cuemcp
```

### Fallback: run from source (no `uvx`)

If you don’t want to rely on `uvx` (for example, you prefer pinned source or local hacking), you can run `cuemcp` from a cloned repository.

```bash
git clone https://github.com/nmhjklnm/cue-mcp.git
cd cue-mcp
uv sync
uv run cuemcp
```

Then configure your MCP client to run:

- `command`: `cuemcp`
- `args`: `[]`

---

## How it works (the contract)

### Semantics

- An MCP-capable agent issues a cue (a request that requires collaboration).
- The team responds (today via a UI; later possibly via a human assistant agent).
- `cuemcp` provides the MCP-facing surface so any MCP participant can plug in.

### Reference implementation (SQLite mailbox)

Current implementation uses a shared SQLite mailbox to connect the MCP server with a client/UI:

```text
MCP Server  ──writes──▶  ~/.cue/cue.db  ──reads/writes──▶  cue-console (UI)
             ◀─polls──                         ◀─responds──
```

- **DB path**: `~/.cue/cue.db`
- **Core tables**:
  - `cue_requests` — server ➜ UI/client
  - `cue_responses` — UI/client ➜ server

This keeps the integration simple: no websockets, no extra daemon, just a shared mailbox.

---

## Pairing with cue-console

**Rule #1:** both sides must agree on the same DB location.

- Start `cuemcp`.
- Start `cue-console`.

- Confirm `cue-console` is reading/writing `~/.cue/cue.db`.

When the UI shows pending items, you’re watching the current reference implementation route collaboration through the console.

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
