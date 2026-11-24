"""PDF case package via ReportLab."""
from __future__ import annotations

from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config
from app.db import Case, ExtractedField, Report, new_id
from app.services import cases as case_svc
from app.services import documents as doc_svc
from app.services.common import ServiceError, add_event, iso, require_member

NAVY = colors.HexColor("#1e3a5f")


def _p(text, style):
    return Paragraph(escape(str(text if text is not None else "-")), style)


def generate_report(db: Session, actor_id: str, case_id: str) -> dict:
    case: Case = require_member(db, actor_id, case_id)
    summary = case_svc.get_case_summary(db, actor_id, case_id)
    docs = doc_svc.list_documents(db, actor_id, case_id)
    checklist = case_svc.get_missing_documents(db, actor_id, case_id)
    events = case_svc.timeline(db, actor_id, case_id)
    tasks = case_svc.list_tasks(db, actor_id, case_id)

    rid = new_id("rpt")
    path = config.REPORT_DIR / f"{case.case_number}_{rid}.pdf"
    ss = getSampleStyleSheet()
    h1, h2, body, small = ss["Title"], ss["Heading2"], ss["BodyText"], ss["Italic"]
    h1.textColor = NAVY
    h2.textColor = NAVY
    tbl_style = TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef6")),
                            ("VALIGN", (0, 0), (-1, -1), "TOP"), ("FONTSIZE", (0, 0), (-1, -1), 8)])

    def table(rows, widths):
        t = Table([[_p(c, body) for c in r] for r in rows], colWidths=widths, repeatRows=1)
        t.setStyle(tbl_style)
        return t

    m = summary["milestones"]
    story = [
        _p(f"Second Hour case package: {case.case_number}", h1),
        _p("Prepared by Second Hour. Not legal advice. Not an emergency service: in an emergency, call 112.", small),
        _p("Fields marked 'Needs review' have not been confirmed by the family. Police authentication status is user-provided and unverified.", small),
        Spacer(1, 6 * mm),
        _p("Case summary", h2),
        table([["Item", "Value"],
               ["Victim (display name)", case.victim_display_name], ["Incident at (UTC)", iso(case.incident_at)],
               ["Approximate location", case.approximate_location], ["Hospital", case.hospital_name],
               ["Life-threatening (family-reported)", "Yes" if case.life_threatening else "No"],
               ["PM-RAHAT window", f"Day {m['cover_window']['day']} of 7 (ends {m['cover_window']['window_ends_at']} UTC)"],
               ["Confirmed hospital bills", f"Rs. {m['cover_amount']['confirmed_bills_inr']:,.0f} of Rs. 1,50,000 cover ({m['cover_amount']['percent_used']}%)"],
               ["Police authentication", f"{m['police_authentication']['status']} (user-provided, unverified)"],
               ["Members", ", ".join(x["name"] for x in summary["members"])]], [60 * mm, 110 * mm]),
        Spacer(1, 4 * mm),
        _p("Alerts", h2),
    ]
    if summary["alerts"]:
        story.append(table([["Alert", "Detail"]] + [[a["title"], a["message"]] for a in summary["alerts"]], [50 * mm, 120 * mm]))
    else:
        story.append(_p("No active alerts.", body))
    story += [Spacer(1, 4 * mm), _p("Document index", h2)]
    story.append(table([["File", "Category", "SHA-256 (prefix)", "Uploaded"]] +
                       [[d["filename"], d["category"] or "unclassified", d["sha256"][:16], d["uploaded_at"]] for d in docs]
                       or [["File", "", "", ""]], [55 * mm, 35 * mm, 40 * mm, 40 * mm]))
    confirmed = db.scalars(select(ExtractedField).where(ExtractedField.case_id == case_id)).all()
    story += [Spacer(1, 4 * mm), _p("Extracted fields", h2)]
    story.append(table([["Field", "Value", "Status"]] +
                       [[f.name, f.value, "Confirmed" if f.status == "confirmed" else "Needs review"] for f in confirmed],
                       [45 * mm, 90 * mm, 35 * mm]))
    story += [Spacer(1, 4 * mm), _p("Missing documents (guidance, not a legal determination)", h2)]
    story.append(table([["Document", "Status", "Why it may help"]] +
                       [[i["label"], i["status"], i["reason"]] for i in checklist["missing"] + checklist["needs_review"]],
                       [55 * mm, 30 * mm, 85 * mm]))
    story += [Spacer(1, 4 * mm), _p("Tasks", h2)]
    story.append(table([["Task", "Priority", "Status", "Assignee"]] +
                       [[t["title"], t["priority"], t["status"], t["assignee_id"] or "-"] for t in tasks],
                       [90 * mm, 25 * mm, 25 * mm, 30 * mm]))
    story += [Spacer(1, 4 * mm), _p("Timeline", h2)]
    story.append(table([["When (UTC)", "Event"]] + [[e["at"], e["summary"]] for e in reversed(events)], [35 * mm, 135 * mm]))
    story += [Spacer(1, 6 * mm),
              _p("Sources: PIB press release 11 March 2026 (" + config.PIB_MARCH_URL + "); PIB 12 August 2026 (" + config.PIB_AUGUST_URL + ").", small),
              _p("Prepared by Second Hour, not legal advice. Second Hour does not decide eligibility, predict compensation or file anything on your behalf.", small)]

    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                      title=f"Second Hour {case.case_number}").build(story)
    if not path.exists():
        raise ServiceError("Report generation failed")
    db.add(Report(id=rid, case_id=case_id, path=str(path), created_by=actor_id))
    add_event(db, case_id, actor_id, "report_generated", f"Case package PDF generated ({rid})")
    db.commit()
    return {"report_id": rid, "case_id": case_id, "download_url": f"/api/cases/{case_id}/reports/{rid}",
            "filename": path.name, "pages_note": "PDF includes summary, timeline, document index, fields, missing items and alerts."}
