"""Agent host (FastAPI, :8000). Holds the MCP client, runs the agent loop, enforces approvals.

Demo auth: the frontend sends X-User-Id (Priya or Arjun picked on the login screen).
Every route still checks case membership server-side.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import Depends, FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select

from app import config
from app.agent import loop as agent
from app.agent import mcp_client as M
from app.db import AuditLog, ChatMessage, PendingAction, Report, SessionLocal, User, init_db
from app.services import cases as case_svc
from app.services import documents as doc_svc
from app.services.common import PermissionDenied, ServiceError, iso, require_member

app = FastAPI(title="Second Hour agent host")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def _startup() -> None:
    init_db()


@app.exception_handler(PermissionDenied)
async def _perm(_: Request, e: PermissionDenied):
    return JSONResponse({"detail": str(e)}, status_code=403)


@app.exception_handler(ServiceError)
async def _svc(_: Request, e: ServiceError):
    return JSONResponse({"detail": str(e)}, status_code=400)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def current_user(x_user_id: str = Header(default=""), db=Depends(get_db)) -> User:
    u = db.get(User, x_user_id)
    if not u:
        raise HTTPException(401, "Pick a demo user first")
    return u


def mcp_error(payload: dict) -> HTTPException:
    msg = payload.get("text", str(payload)) if isinstance(payload, dict) else str(payload)
    code = 403 if "not a member" in msg else 400
    return HTTPException(code, msg.replace("Error executing tool ", ""))


# ------------------------------------------------------------------ users / cases

@app.get("/api/users")
def users(db=Depends(get_db)):
    return [{"user_id": u.id, "name": u.name, "role_label": u.role_label} for u in db.scalars(select(User)).all()]


@app.get("/api/health")
async def health():
    try:
        info = await M.discover()
        return {"ok": True, "mcp": True, "llm": bool(config.ANTHROPIC_API_KEY), "model": config.LLM_MODEL,
                "tts": bool(config.ELEVENLABS_API_KEY), "tools": len(info["tools"])}
    except Exception as e:  # noqa: BLE001
        return {"ok": True, "mcp": False, "llm": bool(config.ANTHROPIC_API_KEY), "error": str(e)[:200]}


@app.get("/api/cases")
def my_cases(user: User = Depends(current_user), db=Depends(get_db)):
    return case_svc.list_cases_for(db, user.id)


class NewCase(BaseModel):
    incident_at: str
    approximate_location: str
    victim_display_name: str | None = None
    hospital_name: str | None = None
    life_threatening: bool = False


@app.post("/api/cases")
async def new_case(body: NewCase, user: User = Depends(current_user)):
    # User clicked "Create" in the UI: that click is the approval. Executed via MCP.
    out, err = await M.call_once("create_accident_case", {"actor_id": user.id, **body.model_dump()}, None, user.id, "approved")
    if err:
        raise mcp_error(out)
    return out


@app.get("/api/cases/{case_id}/summary")
def summary(case_id: str, user: User = Depends(current_user), db=Depends(get_db)):
    return case_svc.get_case_summary(db, user.id, case_id)


class PoliceStatus(BaseModel):
    status: str


@app.post("/api/cases/{case_id}/police-status")
def police_status(case_id: str, body: PoliceStatus, user: User = Depends(current_user), db=Depends(get_db)):
    return case_svc.set_police_status(db, user.id, case_id, body.status)


class Clock(BaseModel):
    hours: float


@app.post("/api/cases/{case_id}/clock")
def clock(case_id: str, body: Clock, user: User = Depends(current_user), db=Depends(get_db)):
    return case_svc.advance_clock(db, user.id, case_id, body.hours)


@app.get("/api/cases/{case_id}/alerts")
async def alerts(case_id: str, user: User = Depends(current_user)):
    out, err = await M.call_once("get_case_alerts", {"actor_id": user.id, "case_id": case_id}, case_id, user.id, "auto_read_only")
    if err:
        raise mcp_error(out)
    return out


@app.get("/api/cases/{case_id}/checklist")
def checklist(case_id: str, user: User = Depends(current_user), db=Depends(get_db)):
    return case_svc.get_missing_documents(db, user.id, case_id)


@app.get("/api/cases/{case_id}/timeline")
def timeline(case_id: str, user: User = Depends(current_user), db=Depends(get_db)):
    return case_svc.timeline(db, user.id, case_id)


# ------------------------------------------------------------------ documents

@app.get("/api/cases/{case_id}/documents")
def documents(case_id: str, user: User = Depends(current_user), db=Depends(get_db)):
    return doc_svc.list_documents(db, user.id, case_id)


@app.post("/api/cases/{case_id}/documents")
async def upload(case_id: str, file: UploadFile = File(...), user: User = Depends(current_user)):
    data = await file.read()
    db = SessionLocal()
    try:
        doc = doc_svc.save_upload(db, user.id, case_id, file.filename or "upload", data)
    finally:
        db.close()
    # Analysis runs through the MCP server (visible in the MCP activity panel)
    out, err = await M.call_once("analyze_case_documents",
                                 {"actor_id": user.id, "case_id": case_id, "document_ids": [doc["document_id"]]},
                                 case_id, user.id, "auto_on_upload")
    if err:
        return {**doc, "analysis_error": out.get("text")}
    return out["documents"][0] if out.get("documents") else doc


@app.post("/api/cases/{case_id}/documents/{doc_id}/analyze")
async def reanalyze(case_id: str, doc_id: str, user: User = Depends(current_user)):
    out, err = await M.call_once("analyze_case_documents", {"actor_id": user.id, "case_id": case_id, "document_ids": [doc_id]},
                                 case_id, user.id, "user_requested")
    if err:
        raise mcp_error(out)
    return out


class FieldUpdate(BaseModel):
    value: str | None = None
    confirm: bool = False


@app.post("/api/cases/{case_id}/fields/{field_id}")
def update_field(case_id: str, field_id: str, body: FieldUpdate, user: User = Depends(current_user), db=Depends(get_db)):
    return doc_svc.update_field(db, user.id, case_id, field_id, body.value, body.confirm)


class Category(BaseModel):
    category: str


@app.post("/api/cases/{case_id}/documents/{doc_id}/category")
def set_category(case_id: str, doc_id: str, body: Category, user: User = Depends(current_user), db=Depends(get_db)):
    return doc_svc.set_category(db, user.id, case_id, doc_id, body.category)


# ------------------------------------------------------------------ tasks

@app.get("/api/cases/{case_id}/tasks")
def tasks(case_id: str, user: User = Depends(current_user), db=Depends(get_db)):
    return case_svc.list_tasks(db, user.id, case_id)


class TaskStatus(BaseModel):
    status: str


@app.post("/api/cases/{case_id}/tasks/{task_id}/status")
def task_status(case_id: str, task_id: str, body: TaskStatus, user: User = Depends(current_user), db=Depends(get_db)):
    return case_svc.set_task_status(db, user.id, case_id, task_id, body.status)


class Assign(BaseModel):
    member_id: str


@app.post("/api/cases/{case_id}/tasks/{task_id}/assign")
async def assign(case_id: str, task_id: str, body: Assign, user: User = Depends(current_user)):
    out, err = await M.call_once("assign_family_task", {"actor_id": user.id, "case_id": case_id, "task_id": task_id,
                                                        "member_id": body.member_id}, case_id, user.id, "approved")
    if err:
        raise mcp_error(out)
    return out


class Propose(BaseModel):
    tool: str
    arguments: dict = {}


@app.post("/api/cases/{case_id}/propose")
async def propose(case_id: str, body: Propose, user: User = Depends(current_user), db=Depends(get_db)):
    """Create an approval card from the UI (e.g. an alert's suggested task)."""
    require_member(db, user.id, case_id)
    if body.tool not in ("create_followup_task", "generate_case_report", "assign_family_task"):
        raise HTTPException(400, "Only mutating tools can be proposed")
    args = {**body.arguments, "actor_id": user.id, "case_id": case_id}
    names = {m["user_id"]: m["name"] for m in case_svc.members(db, case_id)}
    return agent.propose(case_id, user.id, body.tool, args, names)


# ------------------------------------------------------------------ chat + approvals

class ChatIn(BaseModel):
    message: str


@app.get("/api/cases/{case_id}/chat")
def chat_history(case_id: str, user: User = Depends(current_user), db=Depends(get_db)):
    require_member(db, user.id, case_id)
    rows = db.scalars(select(ChatMessage).where(ChatMessage.case_id == case_id).order_by(ChatMessage.id)).all()
    statuses = {p.id: agent.action_dict(p) for p in db.scalars(select(PendingAction).where(PendingAction.case_id == case_id)).all()}
    out = []
    for r in rows:
        meta = json.loads(r.meta_json or "{}")
        meta["actions"] = [statuses.get(a["action_id"], a) for a in meta.get("actions", [])]
        names = {u.id: u.name for u in db.scalars(select(User)).all()}
        out.append({"id": r.id, "role": r.role, "content": r.content, "user": names.get(r.user_id), "at": iso(r.at), **meta})
    return out


@app.post("/api/cases/{case_id}/chat")
async def chat(case_id: str, body: ChatIn, user: User = Depends(current_user)):
    if not body.message.strip():
        raise HTTPException(400, "Empty message")
    try:
        return await agent.run_turn(case_id, user.id, user.name, body.message)
    except (PermissionDenied, ServiceError):
        raise
    except Exception as e:  # noqa: BLE001
        raise HTTPException(502, f"Agent error: {e}") from e


@app.get("/api/cases/{case_id}/actions")
def actions(case_id: str, user: User = Depends(current_user), db=Depends(get_db)):
    require_member(db, user.id, case_id)
    rows = db.scalars(select(PendingAction).where(PendingAction.case_id == case_id).order_by(PendingAction.created_at.desc())).all()
    return [agent.action_dict(p) for p in rows]


@app.post("/api/actions/{action_id}/approve")
async def approve(action_id: str, user: User = Depends(current_user)):
    try:
        return await agent.approve(action_id, user.id)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


@app.post("/api/actions/{action_id}/reject")
def reject(action_id: str, user: User = Depends(current_user)):
    try:
        return agent.reject(action_id, user.id)
    except LookupError as e:
        raise HTTPException(404, str(e)) from e


# ------------------------------------------------------------------ reports

@app.post("/api/cases/{case_id}/reports")
async def make_report(case_id: str, user: User = Depends(current_user)):
    out, err = await M.call_once("generate_case_report", {"actor_id": user.id, "case_id": case_id}, case_id, user.id, "approved")
    if err:
        raise mcp_error(out)
    return out


@app.get("/api/cases/{case_id}/reports")
def list_reports(case_id: str, user: User = Depends(current_user), db=Depends(get_db)):
    require_member(db, user.id, case_id)
    rows = db.scalars(select(Report).where(Report.case_id == case_id).order_by(Report.created_at.desc())).all()
    return [{"report_id": r.id, "created_at": iso(r.created_at), "download_url": f"/api/cases/{case_id}/reports/{r.id}",
             "filename": Path(r.path).name} for r in rows]


@app.get("/api/cases/{case_id}/reports/{report_id}")
def download_report(case_id: str, report_id: str, uid: str = "", x_user_id: str = Header(default=""), db=Depends(get_db)):
    # uid query param lets a plain <a href> download work; membership is still enforced.
    actor = x_user_id or uid
    require_member(db, actor, case_id)
    r = db.get(Report, report_id)
    if not r or r.case_id != case_id:
        raise HTTPException(404, "Report not found")
    return FileResponse(r.path, media_type="application/pdf", filename=Path(r.path).name)


# ------------------------------------------------------------------ voice (ElevenLabs)

class TTSIn(BaseModel):
    text: str


@app.post("/api/tts")
async def tts(body: TTSIn, user: User = Depends(current_user)):
    """Read an agent reply aloud with ElevenLabs (multilingual: English, Hindi, Kannada)."""
    if not config.ELEVENLABS_API_KEY:
        raise HTTPException(503, "Voice is not configured (set ELEVENLABS_API_KEY)")
    import re as _re

    import httpx

    text = _re.sub(r"\[(\d+)\]|[*_`#]", "", body.text)[:2500].strip()
    if not text:
        raise HTTPException(400, "Nothing to read")
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{config.ELEVENLABS_VOICE_ID}",
            headers={"xi-api-key": config.ELEVENLABS_API_KEY, "accept": "audio/mpeg"},
            json={"text": text, "model_id": config.ELEVENLABS_MODEL},
        )
    if r.status_code != 200:
        raise HTTPException(502, f"ElevenLabs error {r.status_code}: {r.text[:200]}")
    return Response(content=r.content, media_type="audio/mpeg")


@app.get("/api/config")
def ui_config():
    return {"tts": bool(config.ELEVENLABS_API_KEY), "llm": bool(config.ANTHROPIC_API_KEY), "demo": config.DEMO_MODE}


# ------------------------------------------------------------------ presenter controls (synthetic demo only)

@app.post("/api/demo/stage")
async def stage_demo(fresh: bool = False):
    """Reset the synthetic demo case and, unless fresh=true, stage it the way a family would after a day:
    bill + medical report uploaded and analysed through MCP, bill confirmed by Priya, police status
    'requested by hospital', clock +25h. Leaves the approval step for the live demo."""
    if not config.DEMO_MODE:
        raise HTTPException(404, "Demo mode is off")
    from scripts.seed import seed
    seed()
    if fresh:
        return {"staged": False, "case_id": "case_demo"}
    actor, cid = "u_priya", "case_demo"
    ids = []
    db = SessionLocal()
    try:
        for name in ("sample_hospital_bill.pdf", "sample_medical_report.pdf"):
            data = (config.DEMO_ASSETS_DIR / name).read_bytes()
            ids.append(doc_svc.save_upload(db, actor, cid, name, data)["document_id"])
    finally:
        db.close()
    out, err = await M.call_once("analyze_case_documents", {"actor_id": actor, "case_id": cid, "document_ids": ids},
                                 cid, actor, "auto_on_upload")
    if err:
        raise mcp_error(out)
    db = SessionLocal()
    try:
        for d in doc_svc.list_documents(db, actor, cid):
            if d.get("category") == "hospital_bill":
                for f in d.get("fields", []):
                    doc_svc.update_field(db, actor, cid, f["field_id"], None, True)
        case_svc.set_police_status(db, actor, cid, "requested_by_hospital")
        case_svc.advance_clock(db, actor, cid, 25)
    finally:
        db.close()
    return {"staged": True, "case_id": cid}


# ------------------------------------------------------------------ MCP panel

@app.get("/api/mcp/info")
async def mcp_info():
    try:
        return await M.discover()
    except Exception as e:  # noqa: BLE001
        return {"connected": False, "url": config.MCP_SERVER_URL, "error": str(e)[:300], "tools": [], "resources": [], "prompts": []}


@app.get("/api/cases/{case_id}/activity")
def activity(case_id: str, user: User = Depends(current_user), db=Depends(get_db)):
    require_member(db, user.id, case_id)
    rows = db.scalars(select(AuditLog).where(AuditLog.case_id == case_id).order_by(AuditLog.id.desc()).limit(80)).all()
    return [{"id": r.id, "tool": r.tool, "arguments": json.loads(r.arguments_json), "result_summary": r.result_summary,
             "approval_state": r.approval_state, "actor_id": r.actor_id, "at": iso(r.at)} for r in rows]


# ------------------------------------------------------------------ static frontend (built)

_dist = config.ROOT / "frontend" / "dist"
if _dist.exists():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="ui")
