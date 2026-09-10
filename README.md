# mirage-mcp

An MCP (Model Context Protocol) server that audits how an AI agent's
guardrails respond to adversarial, boundary-testing prompts — in the style
of AP-Test from ["Peering Behind the Shield: Guardrail Identification in
Large Language Models"](https://arxiv.org/abs/2502.01241). Connect it to
your agent, call `get_probe` to get a test prompt, let your agent respond to
it as it normally would, then call `submit_probe_response` with that
response to get back a scored report of which known guardrail/refusal
pattern it most resembles.

This is disclosed, not covert: the probe battery is the advertised feature,
not a hidden trick. Responses are logged to build a public research dataset
on agent guardrail behavior — see **What gets logged** below before
connecting if that's not something you want.

It's a sibling to `mirage-core` (SSH) and `mirage-crawl` (HTTP): same idea —
instrument a surface, capture what arrives, treat your own corpus as
suspect — applied to the MCP protocol, with guardrail behavior as the
observable instead of shell commands or HTTP requests. Unlike those two,
mirage-mcp doesn't get passive traffic (nothing scans the internet for MCP
servers) — it has to be found and connected to deliberately, which is why
it's built as a genuinely useful self-audit tool rather than a disguised one.

## Ethical and legal boundary

- Deployed only on infrastructure the author owns or has explicit written
  authorization to run on.
- Never executes anything a caller sends it, never scans, probes, or
  retaliates against a connecting client. It only scores what's submitted
  to it.
- Nothing about this tool is disguised. Its description states plainly what
  it does and that responses are logged for research.
- **What gets logged**, per submission: the probe id, your response text to
  that probe, the classifier's verdict, the optional self-reported
  `declared_agent` label (if you provide one — never verified, same posture
  as `mirage-crawl` treating a claimed crawler identity as a signal to
  check, not a fact), and your MCP client's self-reported name/version from
  the connection handshake. Nothing else is ever captured — no other
  arguments, no other tool output, no unrelated content.
- Every submission is captured, including ones the classifier can't
  confidently label — those are recorded as `indeterminate`, never
  silently dropped.
- The signature bank in `mirage_mcp/signatures.py` starts as an unverified
  set of placeholder patterns. Treat every match as a hypothesis until it's
  been checked against real observed sessions, not as ground truth.

## Quick start

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python run.py
```

This starts the server over stdio for local testing. Point an MCP client at
it (Claude Desktop's config, the MCP Inspector, or your own client code),
call `get_probe`, respond to the prompt, then call `submit_probe_response`.

```bash
python tests/test_classifier.py
```

### Containerized (streamable-http)

```bash
docker compose up -d --build
```

Runs the server over `streamable-http` at `127.0.0.1:8765/mcp` — loopback
only, since there's no reverse proxy/TLS in front of it yet. Captured
sessions live in the `mcp_data` named volume (`/app/data/sessions.jsonl`
inside the container), which survives restarts and rebuilds. Runs as a
non-root user, same pattern as `mirage-crawl` and `mirage-core`.

## How it works

1. `mirage_mcp/probes.py` — the bank of adversarial test prompts, each
   targeting a different kind of guardrail reaction (identity elicitation,
   policy conflict, instruction override, jailbreak-lite).
2. `mirage_mcp/server.py` — the MCP server (built on the official MCP
   Python SDK). `get_probe` returns one prompt; `submit_probe_response`
   scores whatever the caller submits and returns a report.
3. `mirage_mcp/signatures.py` — regex patterns characteristic of known
   refusal/guardrail behaviors, each carrying a confidence weight.
4. `mirage_mcp/classifier.py` — scores a response against the signature
   bank and returns the best-matching label, or `indeterminate` if nothing
   clears the confidence threshold.
5. `mirage_mcp/capture.py` — appends every submission and verdict to
   `data/sessions.jsonl`, unconditionally, scoped to the fields listed
   under **What gets logged** above.

## Status

Early scaffold, not yet deployed. Standalone — no database, no
`mirage-fleet` wiring yet. Classification is rule-based only; the signature
bank needs real observed sessions (ideally with `declared_agent` set) before
its confidence weights mean anything. Deployment target is a public MCP
registry listing over streamable-http, once the classifier's been sanity
checked.
