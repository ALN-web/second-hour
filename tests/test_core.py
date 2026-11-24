"""Tests: MCP discovery (in-process MCP client), permissions, watchers, RAG, approval policy."""
import asyncio
import os
import tempfile
from datetime import timedelta

os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="sh_test_")
os.environ["ANTHROPIC_API_KEY"] = ""

import pytest  # noqa: E402
from mcp import Client  # noqa: E402

from app.agent import mcp_client as M  # noqa: E402
from app.db import Case, SessionLocal  # noqa: E402
from app.mcp_server import mcp  # noqa: E402
from app.services import cases, documents, guidance  # noqa: E402
from app.services.common import PermissionDenied, ServiceError  # noqa: E402
from scripts.seed import seed  # noqa: E402

from app import config  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db():
    seed()
    yield


def run(coro):
    return asyncio.run(coro)


# ------------------------------------------------------------ MCP discovery

def test_mcp_discovery_lists_all_tools_resources_prompt():
    async def go():
        async with Client(mcp) as c:
            tools = {t.name: t for t in (await c.list_tools()).tools}
            templates = [t.uri_template for t in (await c.list_resource_templates()).resource_templates]
            resources = [str(r.uri) for r in (await c.list_resources()).resources]
            prompts = [p.name for p in (await c.list_prompts()).prompts]
            return tools, templates, resources, prompts
    tools, templates, resources, prompts = run(go())
    assert set(tools) == {"create_accident_case", "get_case_summary", "search_pmrahat_guidance", "analyze_case_documents",
                          "get_missing_documents", "get_case_alerts", "create_followup_task", "assign_family_task",
                          "generate_case_report"}
    assert "pmrahat://guidance/overview" in resources
    assert "secondhour://cases/{case_id}/timeline" in templates
    assert "accident_case_review" in prompts
    # approval policy comes from annotations
    needs = {n for n, t in tools.items() if M.requires_approval(t)}
    assert needs == {"create_accident_case", "create_followup_task", "assign_family_task", "generate_case_report"}
    # LLM schema hides host-injected args
    llm = M.to_llm_tool(tools["create_followup_task"])
    assert "actor_id" not in llm["input_schema"]["properties"] and "case_id" not in llm["input_schema"]["properties"]


def test_mcp_call_tool_and_permission_error():
    async def go():
        async with Client(mcp) as c:
            ok = await c.call_tool("get_case_summary", {"actor_id": "u_priya", "case_id": "case_demo"})
            bad = await c.call_tool("get_case_summary", {"actor_id": "u_outsider", "case_id": "case_demo"})
            return ok, bad
    ok, bad = run(go())
    assert not ok.is_error and M.result_payload(ok)["case_number"] == "SH-2026-0001"
    assert bad.is_error and "not a member" in bad.content[0].text


# ------------------------------------------------------------ permissions

def test_non_member_denied_everywhere():
    db = SessionLocal()
    for fn, args in [(cases.get_case_summary, ()), (cases.get_case_alerts, ()), (cases.get_missing_documents, ()),
                     (cases.create_task, ("x",)), (documents.list_documents, ())]:
        with pytest.raises(PermissionDenied):
            fn(db, "u_outsider", "case_demo", *args)
    db.close()


def test_cannot_assign_to_non_member():
    db = SessionLocal()
    t = cases.create_task(db, "u_priya", "case_demo", "Call hospital desk")
    with pytest.raises(PermissionDenied):
        cases.assign_task(db, "u_priya", "case_demo", t["task_id"], "u_outsider")
    assert cases.assign_task(db, "u_priya", "case_demo", t["task_id"], "u_arjun")["assignee_id"] == "u_arjun"
    db.close()


def test_due_date_requires_source():
    db = SessionLocal()
    with pytest.raises(ServiceError):
        cases.create_task(db, "u_priya", "case_demo", "x", due_at="2026-12-01T10:00:00")
    db.close()


# ------------------------------------------------------------ watchers

def _upload_and_confirm_bill(db):
    data = (config.DEMO_ASSETS_DIR / "sample_hospital_bill.pdf").read_bytes()
    d = documents.save_upload(db, "u_priya", "case_demo", "bill.pdf", data)
    out = documents.analyze_documents(db, "u_priya", "case_demo", [d["document_id"]])
    doc = out["documents"][0]
    assert doc["category"] == "hospital_bill"
    total = next(f for f in doc["fields"] if f["name"] == "total_amount")
    assert total["value"] == "124000" and total["status"] == "needs_review"
    return total


def test_cover_watcher_only_counts_confirmed_bills():
    db = SessionLocal()
    total = _upload_and_confirm_bill(db)
    assert cases.get_case_alerts(db, "u_priya", "case_demo")["alerts"] == []  # unconfirmed: no alert
    documents.update_field(db, "u_priya", "case_demo", total["field_id"], None, True)
    alerts = cases.get_case_alerts(db, "u_priya", "case_demo")["alerts"]
    assert [a["id"] for a in alerts] == ["cover_window"]
    assert "1,24,000" in alerts[0]["message"]
    db.close()


def test_cover_window_day6_alert():
    db = SessionLocal()
    case = db.get(Case, "case_demo")
    later = (case.incident_at + timedelta(days=5, hours=1)).isoformat()
    res = cases.get_case_alerts(db, "u_priya", "case_demo", now=later)
    assert res["day_of_cover"] == 6 and res["alerts"][0]["id"] == "cover_window"
    db.close()


def test_police_watcher_24h_and_48h():
    db = SessionLocal()
    cases.set_police_status(db, "u_priya", "case_demo", "requested_by_hospital")
    case = db.get(Case, "case_demo")
    t0 = case.police_auth_updated_at
    ids = lambda h: [a["id"] for a in cases.get_case_alerts(db, "u_priya", "case_demo", now=(t0 + timedelta(hours=h)).isoformat())["alerts"]]
    assert "police_auth" not in ids(23)
    assert "police_auth" in ids(25)
    case.life_threatening = True
    db.commit()
    assert "police_auth" not in ids(47)
    assert "police_auth" in ids(49)
    msg = cases.get_case_alerts(db, "u_priya", "case_demo", now=(t0 + timedelta(hours=49)).isoformat())["alerts"]
    assert "not a family deadline" in [a for a in msg if a["id"] == "police_auth"][0]["message"]
    db.close()


# ------------------------------------------------------------ RAG

def test_guidance_cites_official_sources_and_refuses_unknown():
    r = guidance.search("How much does PM-RAHAT cover and for how many days?")
    assert r["found"] and "1.5 lakh" in r["results"][0]["snippet"]
    assert r["results"][0]["source"]["url"].startswith("https://www.pib.gov.in")
    r2 = guidance.search("3,674 discharged without police response")
    assert any("3,674" in x["snippet"] for x in r2["results"])
    assert not guidance.search("best biryani in Bengaluru")["found"]
