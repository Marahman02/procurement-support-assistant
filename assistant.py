"""Suggest root causes and resolution steps for a new incident from similar past tickets."""

import json
import os
import re

import anthropic

import retriever

THRESHOLD = 0.40
MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You help a procurement support team diagnose invoice and purchase-order incidents.

You will be given a new incident and a few past support tickets retrieved by similarity search.
Rules:
- Use only the information in the retrieved tickets. Do not draw on outside knowledge or invent causes.
- Every root cause must cite the ID(s) of the ticket(s) it comes from, exactly as written (e.g. "TKT-001").
- Similarity search can return tickets that look related but are not. If none of the tickets actually fit
  the incident, do not guess: return empty root_causes and resolution_steps, and say in report_draft that
  no past ticket matches this incident.

Reply with a single JSON object and nothing else, using exactly these keys:
{
  "root_causes": [{"cause": "<string>", "cited_ids": ["<ticket id>", ...]}],
  "resolution_steps": ["<string>", ...],
  "report_draft": "<string>"
}"""


def _build_user_prompt(incident, matches):
    tickets = "\n\n".join(
        f"<ticket id=\"{m['id']}\">\n{m['text']}\n</ticket>" for m in matches
    )
    return f"<incident>\n{incident}\n</incident>\n\n<retrieved_tickets>\n{tickets}\n</retrieved_tickets>"


def _strip_code_fences(text):
    """Remove a surrounding ```json ... ``` (or plain ```) fence if the model added one."""
    text = text.strip()
    match = re.match(r"^```[a-zA-Z]*\s*\n?(.*?)\n?```$", text, re.DOTALL)
    return match.group(1).strip() if match else text


def _parse_reply(text):
    """Parse and shape-check the model's JSON. Raises ValueError if it isn't usable."""
    data = json.loads(_strip_code_fences(text))
    if not isinstance(data, dict):
        raise ValueError("reply is not a JSON object")

    root_causes = data.get("root_causes")
    resolution_steps = data.get("resolution_steps")
    report_draft = data.get("report_draft")

    if not isinstance(root_causes, list) or not all(
        isinstance(rc, dict)
        and isinstance(rc.get("cause"), str)
        and isinstance(rc.get("cited_ids"), list)
        for rc in root_causes
    ):
        raise ValueError("root_causes must be a list of {cause, cited_ids} objects")
    if not isinstance(resolution_steps, list) or not all(
        isinstance(step, str) for step in resolution_steps
    ):
        raise ValueError("resolution_steps must be a list of strings")
    if not isinstance(report_draft, str):
        raise ValueError("report_draft must be a string")

    return root_causes, resolution_steps, report_draft


def _check_citations(root_causes, retrieved_ids):
    """Drop cited IDs that weren't retrieved; return cleaned root causes and warnings."""
    warnings = []
    cleaned = []
    for rc in root_causes:
        valid = [cid for cid in rc["cited_ids"] if cid in retrieved_ids]
        invalid = [cid for cid in rc["cited_ids"] if cid not in retrieved_ids]
        if invalid:
            warnings.append(
                f"Removed citation(s) {invalid} from cause \"{rc['cause']}\": "
                "not among the retrieved tickets."
            )
        if not valid:
            warnings.append(
                f"Cause \"{rc['cause']}\" has no valid ticket citation; treat it with caution."
            )
        cleaned.append({"cause": rc["cause"], "cited_ids": valid})
    return cleaned, warnings


def answer(incident: str, api_key: str | None = None) -> dict:
    matches = retriever.search(incident, k=3)

    best = max((m["similarity"] for m in matches), default=None)
    if best is None or best < THRESHOLD:
        return {"status": "no_similar_cases", "matches": matches}

    api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {
            "status": "error",
            "message": "Enter your Anthropic API key in the sidebar.",
            "matches": matches,
        }

    client = anthropic.Anthropic(api_key=api_key)
    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=16000,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": _build_user_prompt(incident, matches)}],
        )
    except anthropic.APIError as e:
        return {"status": "error", "message": f"Anthropic API call failed: {e}", "matches": matches}

    if response.stop_reason != "end_turn":
        return {
            "status": "error",
            "message": f"Model stopped early (stop_reason={response.stop_reason}).",
            "matches": matches,
        }

    reply = "".join(block.text for block in response.content if block.type == "text")
    try:
        root_causes, resolution_steps, report_draft = _parse_reply(reply)
    except (json.JSONDecodeError, ValueError) as e:
        return {
            "status": "error",
            "message": f"Could not parse model reply as the expected JSON: {e}",
            "matches": matches,
        }

    retrieved_ids = {m["id"] for m in matches}
    root_causes, warnings = _check_citations(root_causes, retrieved_ids)

    return {
        "status": "ok",
        "matches": matches,
        "root_causes": root_causes,
        "resolution_steps": resolution_steps,
        "report_draft": report_draft,
        "warnings": warnings,
    }
