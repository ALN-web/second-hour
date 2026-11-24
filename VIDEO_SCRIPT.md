# Second Hour: video pitch script (about 4 minutes)

Team Alpha · wHACKiest 2026 · Track 1: Make MCP Matter

**Setup before recording**
- Run `.\start.ps1 -Seed` and open http://localhost:5173.
- Open MCP Inspector in a second browser tab (`npx @modelcontextprotocol/inspector`, Streamable HTTP, `http://localhost:8001/mcp`) and click Connect.
- Keep `demo_assets/` open in File Explorer for the uploads.
- Optional: put `ANTHROPIC_API_KEY` and `ELEVENLABS_API_KEY` in `.env` before starting, so the live Claude agent and the Listen button are on.

---

## 0:00–0:35 · Problem (slide: Problem Statement)

> "A road accident happens. In the second hour, the family is at the hospital. They have to understand the government's PM-RAHAT cashless scheme, talk to the billing desk, wait on police paperwork and keep track of documents, all at once and all from different people.
>
> PM-RAHAT covers up to one and a half lakh rupees per victim, but only for seven days from the accident. The hospital needs police authentication to proceed. As of July 2026, the government reports that 3,674 victims were discharged after no police response within the prescribed time. Families had no way to see that clock running."

## 0:35–1:05 · Solution (slide: Proposed Solution)

> "Second Hour gives the family one shared case workspace and a proactive AI agent. It remembers the case. It answers scheme questions only from official sources, with citations. It reads bills and reports, watches the deadlines on its own, and proposes next steps. It never acts without a family member's approval.
>
> Every capability lives in a real MCP server, which is what makes this a Track 1 project."

## 1:05–1:40 · Architecture (slide: Architecture)

> "Our React app talks to a FastAPI agent host. At the start of every chat turn, the host discovers its tools from our MCP server over Streamable HTTP, converts them into Claude tool definitions, and runs the tool loop.
>
> Read-only tools run directly. Tools that create, assign or generate become approval cards, decided from MCP tool annotations rather than hardcoded names. The server has nine tools, three resources and a review prompt. Business logic, the watchers and the BM25 search over official PIB text all sit behind it."

## 1:40–3:35 · Live demo

1. **Log in as Priya → case SH-2026-0001.** *"Ravi was in an accident last night in Bengaluru."*
2. **Documents → upload `sample_hospital_bill.pdf`.** *"The bill is classified and its fields extracted through the `analyze_case_documents` MCP tool. Every field says Needs review. We never trust a machine reading of a medical bill."* Click **Confirm** on the total, ₹1,24,000.
3. **Dashboard.** *"The cover tracker now shows ₹1.24 lakh of 1.5 lakh, and a watcher alert fires. This is plain code, not an LLM guess."* Click **Propose task**, then **Approve**. *"The task is created through MCP only after a human approves."*
4. **Police status → 'Requested by hospital', then Demo clock +25 h.** *"A second alert appears. It explains that this is the hospital's and police's 24-hour clock, not the family's, and it cites PIB."*
5. **Agent tab.** Ask *"Who starts police authentication, and is there anything I need to do?"*. Point out the citation [1] with the PIB link. If voice is on, click **▶ Listen** (ElevenLabs). Then ask *"Create a task for the alert"* and show the approval card.
6. **Tasks.** Assign the task to Arjun. *"Both of them must be case members; the server checks."*
7. **Report → Generate.** Open the PDF: summary, timeline, document hashes, confirmed versus unconfirmed fields, and a not-legal-advice notice.
8. **MCP tab.** *"Here is every tool call, with arguments and approval state."* Switch to **MCP Inspector**, call `get_case_alerts` with `actor_id u_priya` and `case_id case_demo`. *"A second MCP host reads the same live case. That's MCP making the agent portable."*

## 3:35–4:00 · Safety, impact and close (slide: Impact & Feasibility)

> "Safety is built in. There's a permanent 'call 112' banner. The agent gives no legal advice and makes no eligibility or compensation calls. Uploaded documents are treated as untrusted data. Unverified statuses are labelled. Every action needs approval and is audited.
>
> In the next 24 hours we'll add Kannada and Hindi voice with ElevenLabs and deploy on AWS. Second Hour: so no family is alone in the second hour. Thank you from Team Alpha."
