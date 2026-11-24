"""MCP client used by the agent host. All agent tool calls go through here (real MCP over Streamable HTTP)."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any

from mcp import Client

from app import config
from app.db import AuditLog, SessionLocal

# Arguments the host injects from the authenticated session; the LLM never chooses them.
INJECTED_ARGS = ("actor_id", "case_id")


def requires_approval(tool) -> bool:
    """Policy from MCP tool annotations (not hardcoded names):
    read-only tools run automatically; non-idempotent writes need human approval."""
    a = tool.annotations
    if a is None:
        return True
    if a.read_only_hint:
        return False
    return not a.idempotent_hint


def to_llm_tool(tool) -> dict:
    """Convert an MCP tool schema into an Anthropic tool definition, hiding injected args."""
    schema = json.loads(json.dumps(tool.input_schema))
    props = schema.get("properties", {})
    for k in INJECTED_ARGS:
        props.pop(k, None)
    if "required" in schema:
        schema["required"] = [r for r in schema["required"] if r not in INJECTED_ARGS]
    schema.pop("title", None)
    desc = (tool.description or "").strip()
    if requires_approval(tool):
        desc += "\n[Host policy: calling this tool only PROPOSES the action to the family; it runs after a human clicks Approve.]"
    return {"name": tool.name, "description": desc[:1024], "input_schema": schema}


def inject_args(tool, args: dict, actor_id: str, case_id: str | None) -> dict:
    props = (tool.input_schema or {}).get("properties", {})
    out = {k: v for k, v in args.items() if k not in INJECTED_ARGS}
    if "actor_id" in props:
        out["actor_id"] = actor_id
    if "case_id" in props and case_id:
        out["case_id"] = case_id
    return out


def result_payload(result) -> dict:
    if result.structured_content is not None:
        sc = result.structured_content
        # Tools returning dict are wrapped as {"result": {...}} by some SDK paths
        return sc.get("result", sc) if isinstance(sc, dict) and set(sc) == {"result"} else sc
    text = "".join(getattr(c, "text", "") for c in result.content)
    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return {"text": text}


def summarize(payload: Any, is_error: bool = False) -> str:
    if is_error:
        return f"ERROR: {str(payload.get('text', payload))[:300]}" if isinstance(payload, dict) else f"ERROR: {payload}"
    if isinstance(payload, dict):
        keys = list(payload)[:6]
        if "case_number" in payload and "milestones" in payload:
            cw = payload["milestones"]["cover_window"]
            return f"{payload['case_number']}: day {cw['day']} of {cw['of']}, {len(payload.get('alerts', []))} alert(s)"
        if "alerts" in payload:
            return f"{len(payload['alerts'])} alert(s)"
        if "results" in payload:
            return f"{len(payload['results'])} passage(s) found" if payload.get("found") else "no matching passage"
        if "task_id" in payload:
            return f"task {payload['task_id']}: {payload.get('title')}"
        if "report_id" in payload:
            return f"report {payload['report_id']}"
        if "documents" in payload:
            return f"{len(payload['documents'])} document(s) analysed"
        if "missing" in payload:
            return f"{len(payload['present'])} present, {len(payload['missing'])} missing, {len(payload['needs_review'])} need review"
        return "keys: " + ", ".join(keys)
    return str(payload)[:200]


def audit(case_id: str | None, actor_id: str | None, tool: str, args: dict, summary: str, state: str) -> None:
    db = SessionLocal()
    try:
        db.add(AuditLog(case_id=case_id, actor_id=actor_id, tool=tool, arguments_json=json.dumps(args, default=str)[:4000],
                        result_summary=summary[:1000], approval_state=state))
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def connect():
    async with Client(config.MCP_SERVER_URL, client_info=None) as c:
        yield c


async def call_logged(client: Client, tool_name: str, args: dict, case_id: str | None, actor_id: str,
                      state: str) -> tuple[dict, bool]:
    try:
        res = await client.call_tool(tool_name, args)
        payload = result_payload(res)
        is_err = bool(res.is_error)
    except Exception as e:  # noqa: BLE001  transport/protocol failure
        payload, is_err = {"text": f"MCP call failed: {e}"}, True
    audit(case_id, actor_id, tool_name, args, summarize(payload, is_err), "error" if is_err else state)
    return payload, is_err


async def call_once(tool_name: str, args: dict, case_id: str | None, actor_id: str, state: str) -> tuple[dict, bool]:
    async with connect() as c:
        return await call_logged(c, tool_name, args, case_id, actor_id, state)


async def discover() -> dict:
    async with connect() as c:
        tools = (await c.list_tools()).tools
        resources = (await c.list_resources()).resources
        templates = (await c.list_resource_templates()).resource_templates
        prompts = (await c.list_prompts()).prompts
        info = c.server_info
        return {
            "connected": True, "url": config.MCP_SERVER_URL,
            "server": {"name": getattr(info, "name", None), "version": getattr(info, "version", None)},
            "protocol_version": c.protocol_version,
            "tools": [{"name": t.name, "title": t.title, "description": (t.description or "").split("\n")[0],
                       "read_only": bool(t.annotations and t.annotations.read_only_hint),
                       "requires_approval": requires_approval(t),
                       "params": list((t.input_schema or {}).get("properties", {}))} for t in tools],
            "resources": [str(r.uri) for r in resources] + [t.uri_template for t in templates],
            "prompts": [p.name for p in prompts],
        }
