"""Agent host (FastAPI, :8000). Holds the MCP client, runs the agent loop, enforces approvals.

Demo auth: the frontend sends X-User-Id (Priya or Arjun picked on the login screen).
Every route still checks case membership server-side.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy import select

from app import config
from app.agent import loop as agent
from app.agent import mcp_client as M
from app.db import AuditLog, ChatMessage, PendingAction, Report, SessionLocal, User, check_connection, init_db
from app.services import cases as case_svc
from app.services import central_documents as central_docs_svc
from app.services import documents as doc_svc
from app.services import vehicles as veh_svc
from app.services import assistant as asst_svc
from app.services import profile as profile_svc
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
    db_info = check_connection()
    try:
        info = await M.discover()
        return {
            "ok": True,
            "database": {"ok": db_info.get("ok"), "dialect": db_info.get("dialect"), "target": db_info.get("target")},
            "mcp": True,
            "llm": bool(config.ANTHROPIC_API_KEY),
            "model": config.LLM_MODEL,
            "tts": bool(config.ELEVENLABS_API_KEY),
            "tools": len(info["tools"]),
        }
    except Exception as e:  # noqa: BLE001
        return {
            "ok": True,
            "database": {"ok": db_info.get("ok"), "dialect": db_info.get("dialect"), "target": db_info.get("target")},
            "mcp": False,
            "llm": bool(config.ANTHROPIC_API_KEY),
            "error": str(e)[:200],
        }


@app.get("/api/cases")
def my_cases(
    overview: bool = Query(False),
    search: str | None = Query(None),
    status: str | None = Query(None),
    date: str | None = Query(None),
    user: User = Depends(current_user),
    db=Depends(get_db),
):
    if overview or search is not None or status is not None:
        return case_svc.list_cases_overview(db, user.id, search=search, status_filter=status, date_filter=date)
    return case_svc.list_cases_for(db, user.id)


@app.get("/api/cases/overview")
def cases_overview(
    search: str | None = Query(None),
    status: str | None = Query(None),
    date: str | None = Query(None),
    user: User = Depends(current_user),
    db=Depends(get_db),
):
    return case_svc.list_cases_overview(db, user.id, search=search, status_filter=status, date_filter=date)


class NewCase(BaseModel):
    incident_at: str
    approximate_location: str
    victim_display_name: str | None = None
    hospital_name: str | None = None
    life_threatening: bool = False
    vehicle_id: str | None = None
    accident_type: str | None = None
    injury_severity: str | None = None
    accident_description: str | None = None
    damage_severity: str | None = None


@app.post("/api/cases")
async def new_case(body: NewCase, user: User = Depends(current_user), db=Depends(get_db)):
    # Try calling MCP tool first; if MCP is offline, execute directly via case_svc
    try:
        out, err = await M.call_once(
            "create_accident_case",
            {"actor_id": user.id, **body.model_dump()},
            None,
            user.id,
            "approved",
        )
        if not err and out:
            return out
    except Exception:
        pass
    return case_svc.create_case(
        db,
        user.id,
        body.incident_at,
        body.approximate_location,
        body.victim_display_name,
        body.hospital_name,
        body.life_threatening,
        body.vehicle_id,
        body.accident_type,
        body.injury_severity,
        body.accident_description,
        body.damage_severity,
    )


@app.get("/api/cases/{case_id}/workspace")
def case_workspace(case_id: str, user: User = Depends(current_user), db=Depends(get_db)):
    return case_svc.get_case_workspace(db, user.id, case_id)


class SectionUpdate(BaseModel):
    section: str
    data: dict


@app.patch("/api/cases/{case_id}/section")
def update_section(case_id: str, body: SectionUpdate, user: User = Depends(current_user), db=Depends(get_db)):
    return case_svc.update_case_section(db, user.id, case_id, body.section, body.data)


class PoliceApprove(BaseModel):
    approved: bool
    feedback: str = ""


@app.post("/api/cases/{case_id}/police/approve")
def approve_police(case_id: str, body: PoliceApprove, user: User = Depends(current_user), db=Depends(get_db)):
    return case_svc.approve_police_draft(db, user.id, case_id, body.approved, body.feedback)


class LinkVehicle(BaseModel):
    vehicle_id: str | None = None


@app.post("/api/cases/{case_id}/vehicle")
def link_vehicle(case_id: str, body: LinkVehicle, user: User = Depends(current_user), db=Depends(get_db)):
    return case_svc.link_case_vehicle(db, user.id, case_id, body.vehicle_id)


class MemberAdd(BaseModel):
    name: str
    role: str = "member"
    relationship: str = "Family"
    contact_number: str = ""
    permissions_summary: str = "View & Add Tasks"


@app.post("/api/cases/{case_id}/members")
def add_member(case_id: str, body: MemberAdd, user: User = Depends(current_user), db=Depends(get_db)):
    return case_svc.add_case_member(
        db, user.id, case_id, body.name, body.role, body.relationship, body.contact_number, body.permissions_summary
    )


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    due_at: str | None = None
    due_source: str | None = None
    assignee_id: str | None = None


@app.post("/api/cases/{case_id}/tasks/create")
def create_task_endpoint(case_id: str, body: TaskCreate, user: User = Depends(current_user), db=Depends(get_db)):
    return case_svc.create_task(
        db, user.id, case_id, body.title, body.description, body.priority, body.due_at, body.due_source
    )


@app.post("/api/cases/{case_id}/tasks/{task_id}/toggle")
def toggle_task(case_id: str, task_id: str, user: User = Depends(current_user), db=Depends(get_db)):
    return case_svc.toggle_task_status(db, user.id, case_id, task_id)


@app.post("/api/cases/{case_id}/evidence")
async def upload_evidence(
    case_id: str,
    file: UploadFile = File(...),
    document_type: str = Form("accident_photo"),
    category: str = Form("accident_case"),
    notes: str = Form(""),
    user: User = Depends(current_user),
    db=Depends(get_db),
):
    require_member(db, user.id, case_id)
    data = await file.read()
    cdoc = central_docs_svc.save_central_document(
        db=db,
        user_id=user.id,
        file_name=file.filename or "evidence.jpg",
        file_data=data,
        mime_type=file.content_type or "image/jpeg",
        document_type=document_type,
        category=category,
        resource_type="ACCIDENT_CASE",
        resource_id=case_id,
        notes=notes,
    )
    case_svc.add_event(db, case_id, user.id, "evidence_uploaded", f"Evidence uploaded: {cdoc.document_name}")
    db.commit()
    return {"ok": True, "id": cdoc.id, "document_name": cdoc.document_name}


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


# ------------------------------------------------------------------ vehicles

class InsuranceIn(BaseModel):
    provider: str
    policy_number: str
    policy_type: str = "Comprehensive"
    start_date: str | None = None
    expiry_date: str | None = None


class VehicleCreateIn(BaseModel):
    registration_number: str
    category: str = "Four Wheeler"
    manufacturer: str
    model: str
    variant: str | None = None
    manufacturing_year: int | None = None
    fuel_type: str = "Petrol"
    color: str | None = None
    chassis_number: str | None = None
    engine_number: str | None = None
    vin: str | None = None
    engine_capacity: str | None = None
    transmission: str | None = None
    owner_name: str | None = None
    ownership_type: str = "Individual"
    relationship_to_user: str | None = "Self"
    main_image: str | None = None
    insurance: InsuranceIn | None = None


class VehicleUpdateIn(BaseModel):
    registration_number: str | None = None
    category: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    variant: str | None = None
    manufacturing_year: int | None = None
    fuel_type: str | None = None
    color: str | None = None
    chassis_number: str | None = None
    engine_number: str | None = None
    vin: str | None = None
    engine_capacity: str | None = None
    transmission: str | None = None
    owner_name: str | None = None
    ownership_type: str | None = None
    relationship_to_user: str | None = None
    main_image: str | None = None
    insurance: InsuranceIn | None = None


@app.get("/api/vehicles")
def list_vehicles(user: User = Depends(current_user), db=Depends(get_db)):
    return veh_svc.list_vehicles(db, user.id)


@app.post("/api/vehicles")
def create_vehicle(body: VehicleCreateIn, user: User = Depends(current_user), db=Depends(get_db)):
    return veh_svc.create_vehicle(db, user.id, body.model_dump())


@app.get("/api/vehicles/{vehicle_id}")
def get_vehicle(vehicle_id: str, user: User = Depends(current_user), db=Depends(get_db)):
    return veh_svc.get_vehicle(db, user.id, vehicle_id)


@app.put("/api/vehicles/{vehicle_id}")
def update_vehicle(vehicle_id: str, body: VehicleUpdateIn, user: User = Depends(current_user), db=Depends(get_db)):
    return veh_svc.update_vehicle(db, user.id, vehicle_id, body.model_dump(exclude_unset=True))


@app.delete("/api/vehicles/{vehicle_id}")
def delete_vehicle(vehicle_id: str, user: User = Depends(current_user), db=Depends(get_db)):
    veh_svc.delete_vehicle(db, user.id, vehicle_id)
    return {"ok": True}


@app.post("/api/vehicles/{vehicle_id}/photos")
async def upload_vehicle_photo(
    vehicle_id: str,
    file: UploadFile = File(...),
    photo_category: str = Form(default="main"),
    is_primary: bool = Form(default=False),
    user: User = Depends(current_user),
    db=Depends(get_db),
):
    content = await file.read()
    return veh_svc.add_vehicle_photo(
        db, user.id, vehicle_id, photo_category, file.filename or "photo.jpg", content, is_primary
    )


@app.post("/api/vehicles/{vehicle_id}/photos/{photo_id}/primary")
def set_primary_vehicle_photo(
    vehicle_id: str, photo_id: str, user: User = Depends(current_user), db=Depends(get_db)
):
    return veh_svc.set_primary_photo(db, user.id, vehicle_id, photo_id)


@app.delete("/api/vehicles/{vehicle_id}/photos/{photo_id}")
def delete_vehicle_photo(
    vehicle_id: str, photo_id: str, user: User = Depends(current_user), db=Depends(get_db)
):
    veh_svc.delete_vehicle_photo(db, user.id, vehicle_id, photo_id)
    return {"ok": True}


@app.get("/api/vehicles/{vehicle_id}/photos/{photo_id}/file")
def get_vehicle_photo_file(
    vehicle_id: str, photo_id: str, user: User = Depends(current_user), db=Depends(get_db)
):
    path, mime, filename = veh_svc.get_photo_file(db, user.id, vehicle_id, photo_id)
    return FileResponse(path, media_type=mime, filename=filename)


@app.post("/api/vehicles/{vehicle_id}/documents")
async def upload_vehicle_document(
    vehicle_id: str,
    file: UploadFile = File(...),
    document_type: str = Form(default="other"),
    document_name: str = Form(default=""),
    expiry_date: str = Form(default=""),
    user: User = Depends(current_user),
    db=Depends(get_db),
):
    from datetime import datetime
    content = await file.read()
    exp_dt = None
    if expiry_date:
        try:
            exp_dt = datetime.fromisoformat(expiry_date.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            pass
    return veh_svc.add_vehicle_document(
        db, user.id, vehicle_id, document_type, document_name or (file.filename or "doc"), file.filename or "doc.pdf", content, exp_dt
    )


@app.delete("/api/vehicles/{vehicle_id}/documents/{doc_id}")
def delete_vehicle_document(
    vehicle_id: str, doc_id: str, user: User = Depends(current_user), db=Depends(get_db)
):
    veh_svc.delete_vehicle_document(db, user.id, vehicle_id, doc_id)
    return {"ok": True}


@app.get("/api/vehicles/{vehicle_id}/documents/{doc_id}/file")
def get_vehicle_document_file(
    vehicle_id: str, doc_id: str, user: User = Depends(current_user), db=Depends(get_db)
):
    path, mime, filename = veh_svc.get_document_file(db, user.id, vehicle_id, doc_id)
    return FileResponse(path, media_type=mime, filename=filename)


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


# ------------------------------------------------------------------ centralized documents module

class DocumentUpdatePayload(BaseModel):
    document_name: str | None = None
    category: str | None = None
    document_type: str | None = None
    document_number: str | None = None
    issuing_authority: str | None = None
    issue_date: str | None = None
    expiry_date: str | None = None
    notes: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None


@app.get("/api/documents")
def list_documents_endpoint(
    category: str = Query(default="all"),
    status: str = Query(default="all"),
    vehicle_id: str = Query(default="all"),
    case_id: str = Query(default="all"),
    search: str = Query(default=""),
    sort_by: str = Query(default="uploaded_at"),
    sort_dir: str = Query(default="desc"),
    user: User = Depends(current_user),
    db=Depends(get_db),
):
    return central_docs_svc.list_documents(
        db, user.id, category, status, vehicle_id, case_id, search, sort_by, sort_dir
    )


@app.get("/api/documents/summary")
def document_summary_endpoint(
    user: User = Depends(current_user),
    db=Depends(get_db),
):
    return central_docs_svc.get_document_summary(db, user.id)


@app.get("/api/documents/{doc_id}")
def get_document_endpoint(
    doc_id: str,
    user: User = Depends(current_user),
    db=Depends(get_db),
):
    return central_docs_svc.get_document(db, user.id, doc_id)


@app.post("/api/documents")
async def create_document_endpoint(
    file: UploadFile = File(...),
    document_name: str = Form(default=""),
    category: str = Form(default="personal"),
    document_type: str = Form(default="other"),
    document_number: str = Form(default=""),
    issuing_authority: str = Form(default=""),
    issue_date: str = Form(default=""),
    expiry_date: str = Form(default=""),
    resource_type: str = Form(default="USER"),
    resource_id: str = Form(default=""),
    notes: str = Form(default=""),
    user: User = Depends(current_user),
    db=Depends(get_db),
):
    content = await file.read()
    iss_dt = None
    if issue_date:
        try:
            iss_dt = datetime.fromisoformat(issue_date.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            pass
    exp_dt = None
    if expiry_date:
        try:
            exp_dt = datetime.fromisoformat(expiry_date.replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:
            pass

    return central_docs_svc.create_document(
        db=db,
        user_id=user.id,
        document_name=document_name or (file.filename or "Document"),
        category=category,
        document_type=document_type,
        file_name=file.filename or "document.pdf",
        content=content,
        document_number=document_number or None,
        issuing_authority=issuing_authority or None,
        issue_date=iss_dt,
        expiry_date=exp_dt,
        notes=notes or None,
        resource_type=resource_type,
        resource_id=resource_id or None,
    )


@app.patch("/api/documents/{doc_id}")
@app.put("/api/documents/{doc_id}")
def update_document_endpoint(
    doc_id: str,
    payload: DocumentUpdatePayload,
    user: User = Depends(current_user),
    db=Depends(get_db),
):
    return central_docs_svc.update_document(db, user.id, doc_id, payload.model_dump(exclude_unset=True))


@app.post("/api/documents/{doc_id}/replace")
async def replace_document_file_endpoint(
    doc_id: str,
    file: UploadFile = File(...),
    user: User = Depends(current_user),
    db=Depends(get_db),
):
    content = await file.read()
    return central_docs_svc.replace_document_file(db, user.id, doc_id, file.filename or "document.pdf", content)


@app.delete("/api/documents/{doc_id}")
def delete_document_endpoint(
    doc_id: str,
    hard: bool = Query(default=False),
    user: User = Depends(current_user),
    db=Depends(get_db),
):
    central_docs_svc.delete_document(db, user.id, doc_id, hard=hard)
    return {"ok": True}


@app.get("/api/documents/{doc_id}/file")
def get_document_file_endpoint(
    doc_id: str,
    download: bool = Query(default=False),
    user: User = Depends(current_user),
    db=Depends(get_db),
):
    path, mime, filename = central_docs_svc.get_document_file(db, user.id, doc_id)
    return FileResponse(
        path,
        media_type=mime,
        filename=filename,
        content_disposition_type="attachment" if download else "inline",
    )


# ------------------------------------------------------------------ Ask Second Hour AI Assistant

class CreateConversationPayload(BaseModel):
    title: str | None = None


class PinConversationPayload(BaseModel):
    pinned: bool


class AssistantMessagePayload(BaseModel):
    content: str


class AssistantActionPayload(BaseModel):
    action_type: str
    payload: dict = {}


@app.get("/api/ai/conversations")
def list_ai_conversations(user: User = Depends(current_user), db=Depends(get_db)):
    return asst_svc.list_conversations(db, user.id)


@app.post("/api/ai/conversations")
def create_ai_conversation(body: CreateConversationPayload, user: User = Depends(current_user), db=Depends(get_db)):
    return asst_svc.create_conversation(db, user.id, body.title)


@app.get("/api/ai/conversations/{conv_id}")
def get_ai_conversation(conv_id: str, user: User = Depends(current_user), db=Depends(get_db)):
    return asst_svc.get_conversation(db, user.id, conv_id)


@app.delete("/api/ai/conversations/{conv_id}")
def delete_ai_conversation(conv_id: str, user: User = Depends(current_user), db=Depends(get_db)):
    asst_svc.delete_conversation(db, user.id, conv_id)
    return {"ok": True}


@app.delete("/api/ai/conversations")
def clear_ai_conversations(user: User = Depends(current_user), db=Depends(get_db)):
    cnt = asst_svc.clear_conversations(db, user.id)
    return {"ok": True, "cleared_count": cnt}


@app.patch("/api/ai/conversations/{conv_id}/pin")
def pin_ai_conversation(conv_id: str, body: PinConversationPayload, user: User = Depends(current_user), db=Depends(get_db)):
    return asst_svc.pin_conversation(db, user.id, conv_id, body.pinned)


@app.post("/api/ai/conversations/{conv_id}/messages")
def send_ai_message(conv_id: str, body: AssistantMessagePayload, user: User = Depends(current_user), db=Depends(get_db)):
    return asst_svc.post_user_message(db, user.id, conv_id, body.content)


@app.post("/api/ai/actions/execute")
def execute_ai_action(body: AssistantActionPayload, user: User = Depends(current_user), db=Depends(get_db)):
    return asst_svc.execute_assistant_action(db, user.id, body.action_type, body.payload)


# ------------------------------------------------------------------ My Profile & Emergency Management

class PersonalInfoPayload(BaseModel):
    name: str | None = None
    gender: str | None = None
    date_of_birth: str | None = None
    phone: str | None = None
    email: str | None = None
    preferred_language: str | None = None
    profile_photo: str | None = None


class VerifyRequestPayload(BaseModel):
    channel: str  # email | phone


class VerifyConfirmPayload(BaseModel):
    channel: str
    otp: str


class EmergencyContactPayload(BaseModel):
    full_name: str
    relationship: str
    mobile_number: str
    alternate_number: str | None = None
    email: str | None = None
    priority: int | None = None
    is_primary: bool = False
    preferred_contact_method: str = "phone"
    permissions: dict = {}


class ReorderContactsPayload(BaseModel):
    ordered_ids: list[str]


class MedicalInfoPayload(BaseModel):
    blood_group: str | None = None
    allergies: str | None = None
    medical_conditions: str | None = None
    medications: str | None = None
    emergency_notes: str | None = None
    share_with_ems: bool = False
    share_with_ai: bool = False


class AddressPayload(BaseModel):
    address_line_1: str | None = None
    address_line_2: str | None = None
    city: str | None = None
    state: str | None = None
    pin_code: str | None = None
    country: str = "India"
    is_same_as_current: bool = False


class ChangePasswordPayload(BaseModel):
    current_password: str
    new_password: str


class DeleteAccountPayload(BaseModel):
    confirmation: str


@app.get("/api/profile")
def get_user_profile(user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.get_profile(db, user.id)


@app.patch("/api/profile")
def update_user_profile(body: PersonalInfoPayload, user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.update_personal_info(db, user.id, body.model_dump(exclude_unset=True))


@app.post("/api/profile/verify/request-otp")
def request_profile_otp(body: VerifyRequestPayload, user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.request_verification_otp(db, user.id, body.channel)


@app.post("/api/profile/verify/confirm-otp")
def confirm_profile_otp(body: VerifyConfirmPayload, user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.confirm_verification_otp(db, user.id, body.channel, body.otp)


@app.get("/api/profile/contacts")
def list_contacts(user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.list_emergency_contacts(db, user.id)


@app.post("/api/profile/contacts")
def create_contact(body: EmergencyContactPayload, user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.add_emergency_contact(db, user.id, body.model_dump())


@app.patch("/api/profile/contacts/{contact_id}")
def update_contact(contact_id: str, body: dict, user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.update_emergency_contact(db, user.id, contact_id, body)


@app.delete("/api/profile/contacts/{contact_id}")
def delete_contact(contact_id: str, user: User = Depends(current_user), db=Depends(get_db)):
    profile_svc.delete_emergency_contact(db, user.id, contact_id)
    return {"ok": True}


@app.post("/api/profile/contacts/{contact_id}/primary")
def make_primary_contact(contact_id: str, user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.set_primary_contact(db, user.id, contact_id)


@app.post("/api/profile/contacts/reorder")
def reorder_contacts(body: ReorderContactsPayload, user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.reorder_emergency_contacts(db, user.id, body.ordered_ids)


@app.get("/api/profile/medical")
def get_medical(request: Request, user: User = Depends(current_user), db=Depends(get_db)):
    ip = request.client.host if request.client else None
    ua = request.headers.get("user-agent")
    return profile_svc.get_medical_info(db, user.id, actor_id=user.id, access_purpose="user_self_view", ip_address=ip, user_agent=ua)


@app.get("/api/profile/medical/access-logs")
def get_medical_access_logs(user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.list_medical_access_logs(db, user.id)


@app.patch("/api/profile/medical")
def update_medical(body: MedicalInfoPayload, user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.update_medical_info(db, user.id, body.model_dump(exclude_unset=True))


@app.delete("/api/profile/medical")
def clear_medical(user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.clear_medical_info(db, user.id)


@app.get("/api/profile/addresses")
def get_user_addresses(user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.get_addresses(db, user.id)


@app.post("/api/profile/addresses/{address_type}")
def save_user_address(address_type: str, body: AddressPayload, user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.save_address(db, user.id, address_type, body.model_dump())


@app.get("/api/profile/identity-documents")
def get_identity_docs(user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.get_identity_documents(db, user.id)


@app.get("/api/profile/privacy")
def get_privacy(user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.get_privacy_preferences(db, user.id)


@app.patch("/api/profile/privacy")
def update_privacy(body: dict, user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.update_privacy_preferences(db, user.id, body)


@app.get("/api/profile/notifications")
def get_notifications(user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.get_notification_preferences(db, user.id)


@app.patch("/api/profile/notifications")
def update_notifications(body: dict, user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.update_notification_preferences(db, user.id, body)


@app.get("/api/profile/security")
def get_security(user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.get_security_overview(db, user.id)


@app.post("/api/profile/security/change-password")
def change_pwd(body: ChangePasswordPayload, user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.change_password(db, user.id, body.current_password, body.new_password)


@app.post("/api/profile/security/delete-account")
def delete_acct(body: DeleteAccountPayload, user: User = Depends(current_user), db=Depends(get_db)):
    return profile_svc.request_account_deletion(db, user.id, body.confirmation)


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
