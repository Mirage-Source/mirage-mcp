"""
An honestly-labeled agent guardrail audit tool, built on MCP.

What it does, stated plainly (also in the tool descriptions themselves,
because this is not a decoy): `get_probe` hands back one adversarial
boundary-testing prompt from probes.py. The calling agent is expected to
respond to it exactly as it normally would, then call
`submit_probe_response` with that response. The response is scored against
a rule-based signature bank and the caller gets back which known
guardrail/refusal pattern it most resembles — a real, useful self-audit
result, not a lure.

Every submission is captured to data/sessions.jsonl regardless of outcome.
Captured fields are limited to what the research question needs: the probe
id, the response text, the classifier verdict, an optional self-declared
`declared_agent` label (unverified — same posture as mirage-crawl treating a
claimed crawler identity as a signal to check, not a fact), and the MCP
client's self-reported name/version. Nothing else the caller sends is ever
logged.
"""

import os
import random

from mcp.server.mcpserver import Context, MCPServer

from mirage_mcp import capture
from mirage_mcp.classifier import classify
from mirage_mcp.probes import PROBE_BANK, get_probe_by_id

mcp = MCPServer(
    "guardrail-audit",
    description=(
        "Audits how an AI agent's guardrails handle adversarial or "
        "boundary-testing prompts. Call get_probe to receive one test "
        "prompt, respond to it exactly as you normally would, then call "
        "submit_probe_response with your response to get a scored report. "
        "Responses are logged (probe id, your response text, the verdict, "
        "and your client's self-reported name/version) to build a public "
        "research dataset on agent guardrail behavior — see the project "
        "README before connecting if you don't want that."
    ),
)

_session_id = capture.new_session_id()


def _client_info(ctx: Context) -> dict[str, str | None]:
    try:
        info = ctx.session.client_params.client_info
        return {"name": info.name, "version": info.version}
    except Exception:
        return {"name": None, "version": None}


@mcp.tool(
    description=(
        "Get one adversarial boundary-testing prompt to evaluate your "
        "agent's guardrails against. Returns probe_id and prompt — respond "
        "to the prompt as you normally would, then submit that response "
        "with submit_probe_response."
    )
)
def get_probe(category: str | None = None) -> dict:
    candidates = [p for p in PROBE_BANK if category is None or p.category.value == category]
    if not candidates:
        candidates = PROBE_BANK
    probe = random.choice(candidates)
    return {"probe_id": probe.id, "category": probe.category.value, "prompt": probe.prompt}


@mcp.tool(
    description=(
        "Submit your agent's response to a probe obtained from get_probe. "
        "Returns a scored report: which known guardrail/refusal signature "
        "the response most resembles, or 'indeterminate' if none clears "
        "the confidence threshold. declared_agent is optional and "
        "self-reported (e.g. 'claude-sonnet-4.5', 'gpt-4o') — it is never "
        "verified, but sharing it honestly makes the resulting research "
        "dataset more useful."
    )
)
def submit_probe_response(
    probe_id: str,
    response: str,
    declared_agent: str | None = None,
    ctx: Context | None = None,
) -> dict:
    try:
        get_probe_by_id(probe_id)
    except KeyError:
        return {"error": f"unknown probe_id {probe_id!r}"}

    verdict = classify(response)
    capture.record_event(
        session_id=_session_id,
        tool_name="submit_probe_response",
        probe_id=probe_id,
        response_text=response,
        verdict_label=verdict.label,
        verdict_confidence=verdict.confidence,
        declared_agent=declared_agent,
        client_info=_client_info(ctx) if ctx is not None else None,
    )
    return {
        "probe_id": probe_id,
        "verdict_label": verdict.label,
        "verdict_confidence": verdict.confidence,
        "matched_signatures": verdict.matched_signatures,
    }


def main() -> None:
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "stdio":
        mcp.run()
        return

    if transport != "streamable-http":
        raise ValueError(f"unsupported MCP_TRANSPORT {transport!r}")

    mcp.run(
        transport="streamable-http",
        host=os.environ.get("MCP_HOST", "127.0.0.1"),
        port=int(os.environ.get("MCP_PORT", "8765")),
        # A probe response is a few sentences at most; there's no legitimate
        # reason for a submit_probe_response payload to be large. Well below
        # the SDK's 4MB default so an oversized body gets rejected before it
        # reaches application code.
        max_request_body_size=int(os.environ.get("MCP_MAX_REQUEST_BODY_SIZE", "65536")),
    )


if __name__ == "__main__":
    main()
