import json
from typing import Any


def render_payload(payload: str, *, debug: bool = False) -> str:
    """Render cue payload (JSON string) into human-friendly terminal text."""
    try:
        parsed: Any = json.loads(payload)
    except Exception:
        return payload

    if not isinstance(parsed, dict):
        return _maybe_debug("Structured data", parsed, debug=debug)

    ptype = parsed.get("type")

    if ptype == "choice":
        return _render_choice(parsed, debug=debug)
    if ptype == "confirm":
        return _render_confirm(parsed, debug=debug)
    if ptype == "form":
        return _render_form(parsed, debug=debug)

    return _maybe_debug(f"Structured request (type={ptype or 'unknown'})", parsed, debug=debug)


def _render_choice(parsed: dict[str, Any], *, debug: bool) -> str:
    options = parsed.get("options")
    allow_multiple = bool(parsed.get("allow_multiple", False))

    lines: list[str] = []
    title = "Please choose (multiple allowed):" if allow_multiple else "Please choose:"
    lines.append(title)

    if isinstance(options, list) and options:
        for opt in options:
            if isinstance(opt, dict):
                oid = str(opt.get("id", "")).strip()
                label = str(opt.get("label", "")).strip()
                if oid and label:
                    lines.append(f"{oid}: {label}")
                elif oid:
                    lines.append(f"{oid}")
                elif label:
                    lines.append(f"- {label}")
                else:
                    lines.append("- <empty>")
            else:
                lines.append(f"- {opt}")
    else:
        lines.append("(no options)")

    return _join_with_debug("\n".join(lines), parsed, debug=debug)


def _render_confirm(parsed: dict[str, Any], *, debug: bool) -> str:
    text = str(parsed.get("text", "")).strip()
    confirm_label = str(parsed.get("confirm_label", "Confirm")).strip() or "Confirm"
    cancel_label = str(parsed.get("cancel_label", "Cancel")).strip() or "Cancel"

    lines = ["Confirmation required:"]
    if text:
        lines.append(text)
    lines.append(f"Options: {confirm_label} / {cancel_label}")

    return _join_with_debug("\n".join(lines), parsed, debug=debug)


def _render_form(parsed: dict[str, Any], *, debug: bool) -> str:
    fields = parsed.get("fields")

    lines: list[str] = ["Please fill in the following:"]

    if isinstance(fields, list) and fields:
        for f in fields:
            if isinstance(f, dict):
                fid = str(f.get("id", "")).strip()
                label = str(f.get("label", "")).strip()
                kind = str(f.get("kind", "")).strip()

                name = label or fid or "Field"
                suffix = f" ({kind})" if kind else ""
                lines.append(f"- {name}{suffix}")
            else:
                lines.append(f"- {f}")
    else:
        lines.append("(no fields)")

    return _join_with_debug("\n".join(lines), parsed, debug=debug)


def _maybe_debug(title: str, data: Any, *, debug: bool) -> str:
    base = f"{title}:"
    if not debug:
        return base
    return base + "\n" + json.dumps(data, ensure_ascii=False, indent=2)


def _join_with_debug(text: str, data: Any, *, debug: bool) -> str:
    if not debug:
        return text
    return text + "\n\n---\n[debug]\n" + json.dumps(data, ensure_ascii=False, indent=2)
