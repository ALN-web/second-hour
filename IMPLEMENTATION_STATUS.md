# Implementation status

_Last updated: 24 Nov 2026_

## Done

- **MCP server** (MCP Python SDK v2.3, `MCPServer`, Streamable HTTP at `:8001/mcp`): all 9 tools, 3 resources (1 static, 2 templates) and the `accident_case_review` prompt. Tool annotations drive the approval policy.
- **Agent host** (FastAPI `:8000`): a real `mcp.Client` over Streamable HTTP. Tools are discovered each turn and MCP schemas converted to Claude tool definitions. `actor_id` and `case_id` are injected by the host. It runs a multi-step tool-use loop and turns mutating tools into approval cards (approve or reject executes through MCP). Every call goes to the audit log.
- **Proactive alerts.** The agent calls `get_case_alerts` at the start of each turn and mentions new alerts once.
- **Deterministic watchers**: the cover window and confirmed-bills tracker, and the police authentication watcher (24h/48h). There is a demo clock in the UI and a `now` parameter on the tool.
- **RAG**: BM25 over the paragraphs of 4 curated knowledge files with front-matter. Results carry citations, and unmatched questions get "not found".
- **Documents**: private upload with SHA-256, PyMuPDF text extraction, rule-based classification and field extraction with confidence, and Claude vision fallback for images and scans. Every field starts as "Needs review", with Confirm/Edit per field and category override.
- **Checklist** of missing documents with reasons, labelled as guidance.
- **Tasks**: create (approval), assign (membership-checked) and mark done. There is a timeline of all events.
- **PDF case package** via ReportLab, downloadable only by members.
- **UI**: login (Priya/Arjun), case list and create, dashboard, agent chat with citations and approval cards, document vault, tasks and timeline, report, and an MCP panel with a live activity log. It has a persistent 112 banner.
- **Offline mode**: without `ANTHROPIC_API_KEY`, a deterministic agent still goes through MCP.
- **Tests** (9): MCP discovery and calls through an in-process MCP client, permissions, the due-date rule, both watchers including the 48h case, and RAG citations and refusal.
- One-command start (`start.sh`, `start.ps1`), `.env.example` and a seed script with synthetic PDFs.

## Known limitations

- **Demo auth only**: the user is picked on a login screen and sent as the `X-User-Id` header. A real deployment needs proper authentication. Membership checks themselves are enforced server-side.
- **The MCP server has no auth.** It is bound to `127.0.0.1` and trusts the `actor_id` argument. For remote use, add OAuth (the SDK supports it) and derive the actor from the token.
- The case resources (`secondhour://cases/{id}/...`) carry no actor, so they return the coordinator's view. Fine for local demo hosts; restrict them before any shared deployment.
- Rule-based extraction is tuned for typical Indian hospital bill and report layouts. Unusual layouts fall back to fewer fields, and the family can edit them.
- The MoRTH gazette file only contains points cross-checked with PIB; the rest is explicitly marked not verified. Official pages were not fetched during the build.
- The cover window uses `incident_at` + 7×24h. The scheme counts "7 days from the date of the accident", and the exact cut-off may differ by hospital.
- No Kannada or Hindi UI yet. No notifications (SMS/WhatsApp) yet.
- SQLite with a single process per server is fine for the demo but not for multi-instance deployment.

## Next

- OAuth on the MCP server, and per-actor resources.
- Kannada and Hindi UI and answers.
- WhatsApp reminders for assigned tasks.
- A hospital-desk contact log and call scripts.
