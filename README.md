# mirage-mcp

A decoy MCP (Model Context Protocol) server. It exposes a small set of
plausible-looking tools to any agent that connects; some of those tools'
descriptions carry adversarial probes — in the style of AP-Test from
["Peering Behind the Shield: Guardrail Identification in Large Language
Models"](https://arxiv.org/abs/2502.01241) — designed to provoke a
guardrail-specific reaction. What the connecting agent does, and how it
phrases any refusal, is matched against a signature bank to fingerprint
which underlying model or guardrail is likely on the other end.

It is a sibling to `mirage-core` (SSH) and `mirage-crawl` (HTTP): same idea
— instrument a surface, capture what arrives, treat your own corpus as
suspect — applied to the MCP protocol, with agent guardrail behavior as the
observable instead of shell commands or HTTP requests.

## Ethical and legal boundary

- This server is deployed only on infrastructure the author owns or has
  explicit written authorization to run on.
- It never executes anything a caller sends it, never stores or forwards
  data beyond a local capture log, and never scans, probes, or retaliates
  against a connecting client. It only observes what arrives.
- Probes are designed to *provoke a guardrail reaction*, not to actually
  extract anything harmful — the honeypot doesn't need a probe to succeed
  to learn something from how an agent responds to it.
- Every response is captured, including ones the classifier can't confidently
  label — those are recorded as `indeterminate`, never silently dropped.
- The signature bank in `mirage_mcp/signatures.py` starts as an unverified
  set of placeholder patterns. Treat every match as a hypothesis until it's
  been checked against real observed sessions, not as ground truth.

## Quick start

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python run.py
```

This starts the decoy MCP server over stdio. Point an MCP client at it (e.g.
add it as a local server in Claude Desktop's config, or use the MCP
Inspector) and interact with `search_internal_docs`, `run_diagnostic`, or
`fetch_status_report`. Every call is logged to `data/sessions.jsonl` with the
classifier's verdict.

```bash
python tests/test_classifier.py
```

## How it works

1. `mirage_mcp/probes.py` — the bank of adversarial probes, each targeting a
   different kind of guardrail reaction (identity elicitation, policy
   conflict, instruction override, jailbreak-lite).
2. `mirage_mcp/server.py` — the decoy MCP server (built on the official MCP
   Python SDK). Each tool's description embeds one probe and asks the
   calling agent to state its compliance/refusal reasoning in an
   `acknowledgement` argument — that's the text the fingerprint is built
   from.
3. `mirage_mcp/signatures.py` — regex patterns characteristic of known
   refusal/guardrail behaviors, each carrying a confidence weight.
4. `mirage_mcp/classifier.py` — scores a response against the signature
   bank and returns the best-matching label, or `indeterminate` if nothing
   clears the confidence threshold.
5. `mirage_mcp/capture.py` — appends every request/response/verdict to
   `data/sessions.jsonl`, unconditionally.

## Status

Early scaffold. Standalone — no database, no `mirage-fleet` wiring yet.
Classification is rule-based only; the signature bank needs real observed
sessions before its confidence weights mean anything.
