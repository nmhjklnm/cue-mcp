![cuemcp banner](assets/banner.png)

_An MCP service on top of HAP (Human Agent Protocol) — compose humans and agents into a team._

[![PyPI](https://img.shields.io/pypi/v/cuemcp?label=cuemcp&color=0B7285)](https://pypi.org/project/cuemcp/)
[![Repo](https://img.shields.io/badge/repo-cue--mcp-111827)](https://github.com/nmhjklnm/cue-mcp)
![License](https://img.shields.io/badge/license-Apache--2.0-1E40AF)

---

## The pitch (10 seconds)

`cuemcp` is an MCP server that gives your agents a single “collaboration inbox” (`cue`/`cue()`), so you can run Claude Code, Cursor, Codex, Windsurf (and other MCP-capable runtimes) with one consistent collaboration flow.

Pair it with [`cue-console`](https://github.com/nmhjklnm/cue-console) for a desktop/mobile UI to view pending collaboration requests and respond from anywhere.

---

## Quickstart (1 minute)

### Goal

Add `cuemcp` as a local `stdio` MCP server inside your agent/runtime.

Assumptions:

- You have `uv`.
- Your machine can run `uvx`.

### Notes

- The current version can occasionally disconnect (for example, the agent replies directly without calling `cue()` at the end).
- If you get disconnected, type `cue` in the affected runtime to trigger auto-reconnect.

### Step 1: Add the HAP rule to your agent/runtime

Before using `cuemcp`, add a persistent HAP rule so your agent knows it must call `cue()` at the end of every response.

- **Windsurf**: add it to **Global Rules**.
- **Codex**: add it to `agents.md`.
- **Claude Code**: add it to `Claude.md`.

<details>
<summary>Human Agent Protocol (HAP) rules (required)</summary>

```text
Human Agent Protocol (HAP)

Hard rule: the agent must call the `cue` tool at the end of every response, no exceptions.
Always use the cue MCP to provide a final summary, ask a question, or request input.

Convention: when the user types `cue`, the user is accepting the HAP rules (supports disconnect + reconnect).

- First-time connection / no agent_id: call join() to obtain an agent_id, then call cue().
- Reconnect / existing agent_id (e.g. the cue call timed out but the chat continued):
  when the user types cue again, prefer calling cue() with the existing agent_id;
  only call join() again if you cannot determine the agent_id.

When to call

- On first message in a new chat (no history): call join().
- After completing any task: call cue().
- Before ending any response: call cue().

Forbidden behavior

- Using a self-chosen name without calling join() first.
- Ending a reply without calling cue().
- Replacing cue() with "let me know if you need anything else".
- Assuming there are no follow-ups.

Notes

If you are not sure whether to call it, call it.

Not calling cue() means the user cannot continue the interaction.
```

</details>

Then continue with MCP configuration below.

### Step 2: Configure the MCP server

### Step 3: Connect your runtime

In the agent/runtime you want to use, type `cue` to trigger connect (or reconnect) and route the collaboration flow to `cue-console`.

<details>
<summary>Claude Code</summary>

Claude Code can install local `stdio` MCP servers via `claude mcp add`.

```bash
claude mcp add --transport stdio cuemcp -- uvx --from cuemcp cuemcp
```

</details>

<details>
<summary>Windsurf</summary>

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

</details>

<details>
<summary>Cursor</summary>

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

</details>

<details>
<summary>VS Code</summary>

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

</details>

<details>
<summary>Codex</summary>

Codex can register a local stdio MCP server via the CLI:

```bash
codex mcp add cuemcp -- uvx --from cuemcp cuemcp
```

For deeper configuration, Codex stores MCP servers in `~/.codex/config.toml`.

</details>

<details>
<summary>Gemini CLI</summary>

Gemini CLI can add a local stdio MCP server via:

```bash
gemini mcp add cuemcp uvx --from cuemcp cuemcp
```

</details>

<details>
<summary>Fallback: run from source (no `uvx`)</summary>

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

</details>

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
