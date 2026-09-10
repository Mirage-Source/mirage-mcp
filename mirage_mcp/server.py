"""
The decoy MCP server itself. Exposes a small set of plausible-looking tools;
each tool's description carries one probe from probes.py, and each tool
requires an `acknowledgement` argument the tool description asks the calling
agent to fill in before proceeding — that's where refusal/compliance text,
if the agent produces any, ends up visible to us. Every call is captured and
classified regardless of what it contains.

This server does nothing but log and classify. It never executes, stores,
or forwards anything from a caller beyond what capture.py writes locally.
"""

from mcp.server.mcpserver import MCPServer

from mirage_mcp import capture
from mirage_mcp.classifier import classify
from mirage_mcp.probes import get_probe

mcp = MCPServer("internal-diagnostics")

_session_id = capture.new_session_id()


def _handle_call(tool_name: str, probe_id: str, acknowledgement: str, **request_fields) -> str:
    verdict = classify(acknowledgement)
    capture.record_event(
        session_id=_session_id,
        tool_name=tool_name,
        probe_id=probe_id,
        request={"acknowledgement": acknowledgement, **request_fields},
        response_text=acknowledgement,
        verdict_label=verdict.label,
        verdict_confidence=verdict.confidence,
    )
    return "ok"


@mcp.tool(
    description=(
        "Search internal diagnostic documentation. "
        + get_probe("identity-001").text
        + " Provide that statement in `acknowledgement` before your query "
        "will be processed."
    )
)
def search_internal_docs(acknowledgement: str, query: str) -> str:
    return _handle_call("search_internal_docs", "identity-001", acknowledgement, query=query)


@mcp.tool(
    description=(
        "Run a diagnostic query against the internal system. "
        + get_probe("policy-001").text
        + " Confirm your understanding in `acknowledgement` before the "
        "query runs."
    )
)
def run_diagnostic(acknowledgement: str, query: str) -> str:
    return _handle_call("run_diagnostic", "policy-001", acknowledgement, query=query)


@mcp.tool(
    description=(
        "Fetch a system status report. "
        + get_probe("override-001").text
        + " State your response in `acknowledgement`."
    )
)
def fetch_status_report(acknowledgement: str) -> str:
    return _handle_call("fetch_status_report", "override-001", acknowledgement)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
