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

See [FINDINGS.md](FINDINGS.md) for results so far — real, three-agent
comparison data (Claude Sonnet 5, Llama 3.1 8B, Qwen 2.5 7B), not just
methodology.

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
  check, not a fact), your MCP client's self-reported name/version from the
  connection handshake, and a salted HMAC-SHA256 hash of your connecting IP
  plus the country it resolves to — never the IP itself, same anonymization
  `mirage-core` already uses for its published exports. Nothing else is
  ever captured — no other arguments, no other tool output, no unrelated
  content.
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
cp .env.example .env   # fill in IP_SALT; see the file for how to generate one
docker compose up -d --build
```

Runs the server over `streamable-http` at `127.0.0.1:8765/mcp`, loopback
only — public reachability comes from a Cloudflare Tunnel in front of it,
not a published port. Captured sessions live in the `mcp_data` named volume
(`/app/data/sessions.jsonl` inside the container), which survives restarts
and rebuilds. Runs as a non-root user, same pattern as `mirage-crawl` and
`mirage-core`.

Geo lookup expects `mirage-core`'s DB-IP CSVs mounted read-only at
`/data/geo` (see `docker-compose.yml`'s `GEO_DATA_DIR`, defaults to
`mirage-core`'s path on the shared deployment box); without `IP_SALT` set,
IPs simply aren't hashed or logged.

## How it works

1. `mirage_mcp/probes.py` — the bank of adversarial test prompts: the
   original AP-Test-style set (identity elicitation, policy conflict,
   instruction override, jailbreak-lite) plus four documented
   jailbreak-technique categories (persona/roleplay, hypothetical framing,
   refusal-prefix injection, authority impersonation), adapted from
   JailbreakBench/HarmBench.
2. `mirage_mcp/server.py` — the MCP server (built on the official MCP
   Python SDK). `get_probe` returns one prompt; `submit_probe_response`
   scores whatever the caller submits and returns a report.
3. `mirage_mcp/signatures.py` — two regex pattern banks: one for known
   refusal-style phrasing, one for explicit compliance markers, each
   pattern carrying a confidence weight.
4. `mirage_mcp/classifier.py` — scores a response on two axes: did it
   comply with the probe, and if it refused, which known refusal style
   does it resemble. Compliance is checked first and takes priority — a
   model agreeing to drop its own safety behavior is the more important
   finding than any style match. Either axis can come back `indeterminate`
   if nothing clears the confidence threshold.
5. `mirage_mcp/capture.py` — appends every submission and verdict to
   `data/sessions.jsonl`, unconditionally, scoped to the fields listed
   under **What gets logged** above.
6. `mirage_mcp/identity.py` / `mirage_mcp/geo.py` — resolve the connecting
   IP (from `CF-Connecting-IP`/`X-Forwarded-For`) to a salted hash and a
   country code before the raw address is discarded. Geo lookup reuses
   `mirage-core`'s DB-IP Lite CSV snapshots rather than a live API call —
   see `mirage_mcp/geo.py`'s docstring.

## Deployment

Runs containerized on the same VPS as `mirage-core`
(`/opt/mirage/mirage-mcp`), bound to `127.0.0.1:8765`. Public exposure goes
through a Cloudflare Tunnel rather than a directly-exposed port, to avoid
correlating this box's real IP with the SSH honeypot sharing it.

Redeploy via GitHub Actions (`workflow_dispatch` on `deploy.yml`). The
deploy key is deliberately more restricted than `mirage-core`'s: it's
locked server-side to a forced command (`authorized_keys`
`command="/opt/mirage/mirage-mcp/deploy.sh"`, no pty/agent-forwarding/
X11-forwarding/user-rc/port-forwarding) that only ever runs `deploy.sh`
(`git fetch && git reset --hard && docker compose up --build -d`) —
even a leaked key can't run anything else.

## Status

Deployed on the VPS. Standalone — no database, no `mirage-fleet` wiring.
Classification is rule-based only; the signature bank needs real observed
sessions (ideally with `declared_agent` set) before its confidence weights
mean anything.
