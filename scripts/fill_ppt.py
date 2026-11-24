"""Fill the wHACKiest 2026 PPT template for Team Alpha (no slides added).

Usage: python scripts/fill_ppt.py template.pptx submission/Alpha_Track1.pptx
"""
import copy
import sys

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Inches, Pt

NAVY = RGBColor(0x1B, 0x1F, 0x6B)
ORANGE = RGBColor(0xFD, 0x9B, 0x36)
BLUE = RGBColor(0x2A, 0x5B, 0xC8)
INK = RGBColor(0x11, 0x11, 0x11)
MUTED = RGBColor(0x6B, 0x64, 0x59)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LINE = RGBColor(0xD9, 0xD2, 0xC5)
TINT = RGBColor(0xEE, 0xF1, 0xFA)
FONT = "Calibri"

TEAM = {"name": "Alpha", "id": "9fe3c6a4", "track": "Track 1: Make MCP Matter (AI Agents for Everyday Life)",
        "college": "", "members": ["Anjankumar LN", "Kanishka S", "Gagandeep G", "Deekshith K"],
        "usns": ["", "", "", ""]}


# ------------------------------------------------------------------ helpers

def shape_by_id(slide, sid):
    for sh in slide.shapes:
        if sh.shape_id == sid:
            return sh
    raise KeyError(sid)


def set_first_run(shape, text):
    p = shape.text_frame.paragraphs[0]
    p.runs[0].text = text
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    for extra in shape.text_frame.paragraphs[1:]:
        extra._p.getparent().remove(extra._p)


def append_value(shape, value, para=0):
    """Append a value run after a label like 'TEAM NAME:' keeping the label run's font."""
    p = shape.text_frame.paragraphs[para]
    label = p.runs[0]
    r = copy.deepcopy(label._r)
    r.find(qn("a:t")).text = "  " + value
    rpr = r.find(qn("a:rPr"))
    rpr.set("b", "0")
    label._r.addnext(r)


def fill_bullets(shape, items, size=1500):
    """items: list of (lead, rest). Reuses the template's second bullet paragraph as the pattern."""
    txBody = shape.text_frame._txBody
    paras = txBody.findall(qn("a:p"))
    pattern = copy.deepcopy(paras[1] if len(paras) > 1 else paras[0])
    for p in paras:
        txBody.remove(p)
    for i, (lead, rest) in enumerate(items):
        p = copy.deepcopy(pattern)
        if i == 0:
            p.find(qn("a:pPr")).find(qn("a:spcBef")).find(qn("a:spcPts")).set("val", "0")
        runs = p.findall(qn("a:r"))
        base = runs[0]
        for r in runs[1:]:
            p.remove(r)
        base.find(qn("a:rPr")).set("sz", str(size))
        if lead:
            lr = copy.deepcopy(base)
            lr.find(qn("a:t")).text = lead + " "
            rpr = lr.find(qn("a:rPr"))
            rpr.set("b", "1")
            _set_color(rpr, "1B1F6B")
            base.addprevious(lr)
        base.find(qn("a:t")).text = rest
        _set_color(base.find(qn("a:rPr")), "111111")
        txBody.append(p)


def _set_color(rpr, hexcolor):
    sf = rpr.find(qn("a:solidFill"))
    if sf is None:
        sf = etree.SubElement(rpr, qn("a:solidFill"))
        rpr.insert(0, sf)
    for c in list(sf):
        sf.remove(c)
    etree.SubElement(sf, qn("a:srgbClr")).set("val", hexcolor)


def remove(shape):
    shape._element.getparent().remove(shape._element)


def text_box(slide, x, y, w, h, runs_by_para, size=13, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, name=None):
    """runs_by_para: list of paragraphs, each a list of (text, {bold, color, size, italic})."""
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        tb.name = name
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    for i, runs in enumerate(runs_by_para):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if i:
            p.space_before = Pt(3)
        for text, o in runs:
            r = p.add_run()
            r.text = text
            f = r.font
            f.name = FONT
            f.size = Pt(o.get("size", size))
            f.bold = o.get("bold", False)
            f.italic = o.get("italic", False)
            f.color.rgb = o.get("color", INK)
    return tb


def card(slide, x, y, w, h, fill=WHITE, line=LINE, name=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE):
    s = slide.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if name:
        s.name = name
    s.fill.solid()
    s.fill.fore_color.rgb = fill
    if line is None:
        s.line.fill.background()
    else:
        s.line.color.rgb = line
        s.line.width = Pt(0.75)
    s.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        s.adjustments[0] = 0.08
    s.text_frame.text = ""
    return s


def labeled_card(slide, x, y, w, h, title, lines, fill=WHITE, title_color=NAVY, size=12.5, name=None):
    card(slide, x, y, w, h, fill=fill, name=name)
    paras = [[(title, {"bold": True, "color": title_color, "size": size + 1.5})]]
    for ln in lines:
        if isinstance(ln, tuple):
            paras.append([(ln[0] + " ", {"bold": True, "color": NAVY, "size": size}), (ln[1], {"size": size})])
        else:
            paras.append([(ln, {"size": size})])
    text_box(slide, x + 0.18, y + 0.14, w - 0.36, h - 0.24, paras, size=size)


def arrow(slide, x1, y1, x2, y2, color=NAVY, width=1.75):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(width)
    ln = c.line._get_or_add_ln()
    tail = etree.SubElement(ln, qn("a:tailEnd"))
    tail.set("type", "triangle")
    tail.set("w", "med")
    tail.set("len", "med")
    return c


def circle_num(slide, x, y, d, n, fill=ORANGE):
    s = card(slide, x, y, d, d, fill=fill, line=None, shape=MSO_SHAPE.OVAL)
    tf = s.text_frame
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.alignment = PP_ALIGN.CENTER
    r = p.add_run()
    r.text = str(n)
    r.font.name = FONT
    r.font.bold = True
    r.font.size = Pt(13)
    r.font.color.rgb = WHITE


def content_frame(slide, subtitle, label, label_id, sub_id, bullets_id):
    set_first_run(shape_by_id(slide, sub_id), subtitle)
    lab = shape_by_id(slide, label_id)
    if label:
        set_first_run(lab, label)
    else:
        remove(lab)
    return shape_by_id(slide, bullets_id)


def ids(slide):
    """(subtitle, label, bullets) shape ids on a content slide."""
    named = sorted([sh for sh in slide.shapes if sh.has_text_frame], key=lambda s: s.shape_id)
    title = next(s for s in named if s.is_placeholder and s.placeholder_format.type == 1)
    others = [s for s in named if s is not title and not (s.is_placeholder and "sldNum" in s._element.xml[:600])]
    sub = next(s for s in others if s.is_placeholder)
    label = next(s for s in others if s.text_frame.text.strip().upper().startswith("INCLUDE"))
    bullets = max((s for s in others if s not in (sub, label)), key=lambda s: s.height)
    return sub.shape_id, label.shape_id, bullets.shape_id


# ------------------------------------------------------------------ slides

def cover(s):
    by = {sh.text_frame.text.strip(): sh for sh in s.shapes if sh.has_text_frame}
    append_value(by["TEAM NAME:"], TEAM["name"])
    if TEAM["college"]:
        append_value(by["COLLEGE NAME:"], TEAM["college"])
    append_value(by["TRACK:"], TEAM["track"])
    append_value(by["TEAM ID:"], TEAM["id"])
    mem = next(sh for sh in s.shapes if sh.has_text_frame and sh.text_frame.text.startswith("Member 1"))
    for i, name in enumerate(TEAM["members"]):
        append_value(mem, name, para=i)
    usn = next(sh for sh in s.shapes if sh.has_text_frame and sh.text_frame.text.startswith("USN"))
    for i, u in enumerate(TEAM["usns"]):
        if u:
            append_value(usn, u, para=i)


def problem(s):
    sub, lab, bl = ids(s)
    b = content_frame(s, "After a road accident, families juggle hospital, PM-RAHAT, police and paperwork with no single view of the case.",
                      "THE PROBLEM", lab, sub, bl)
    b.width = Inches(6.9)
    fill_bullets(b, [
        ("What:", "The family of an accident victim must coordinate a cashless scheme, hospital desks, police follow-ups and documents in the hardest hours of their lives."),
        ("Who:", "Families of road-accident victims across India. PM-RAHAT alone covered 22,481 victims in 34 States/UTs by 31 July 2026."),
        ("Why it matters:", "Cover is capped at ₹1.5 lakh for 7 days from the accident, and 3,674 victims were discharged after no police response within the prescribed timelines."),
        ("Gaps today:", "Rules live in press releases; TMS/eDAR portals serve hospitals and police, not families; generic chatbots guess rules and cannot track a case."),
    ], size=1500)
    stats = [("3,674", "victims discharged after no police response in time"),
             ("₹1.5 lakh", "cashless cover per victim, max 7 days"),
             ("22,481", "victims covered across 34 States/UTs")]
    for i, (num, lbl) in enumerate(stats):
        y = 2.45 + i * 0.98
        card(s, 8.0, y, 4.55, 0.82, name=f"Stat {i + 1}")
        text_box(s, 8.2, y + 0.08, 1.95, 0.66, [[(num, {"bold": True, "color": ORANGE if i == 0 else NAVY, "size": 26})]],
                 anchor=MSO_ANCHOR.MIDDLE)
        text_box(s, 10.2, y + 0.08, 2.2, 0.66, [[(lbl, {"size": 12, "color": INK})]], anchor=MSO_ANCHOR.MIDDLE)
    text_box(s, 8.0, 5.4, 4.55, 0.3, [[("Source: PIB, 11 Mar 2026 and 12 Aug 2026", {"italic": True, "size": 10, "color": MUTED})]])


def solution(s):
    sub, lab, bl = ids(s)
    b = content_frame(s, "Second Hour: one shared case workspace and a proactive AI agent built on a real MCP server.",
                      "KEY FEATURES", lab, sub, bl)
    b.width = Inches(6.6)
    fill_bullets(b, [
        ("Case memory:", "one workspace per accident, shared by the whole family."),
        ("Cited answers:", "PM-RAHAT questions answered only from official PIB/MoRTH text."),
        ("Document vault:", "bills and reports auto-classified; fields stay “Needs review” until confirmed."),
        ("Watchers:", "Day X of 7 and ₹ used vs ₹1.5 lakh; police-authentication follow-up alerts."),
        ("Human approval:", "agent proposes tasks and reports; family approves and assigns."),
        ("Case package:", "one-click PDF to share with hospital, insurer or lawyer."),
        ("MVP today:", "9 MCP tools, live web app, tests. Next 24 hrs: voice, Kannada/Hindi, AWS."),
    ], size=1400)
    text_box(s, 7.75, 2.42, 4.8, 0.3, [[("USER FLOW", {"bold": True, "color": BLUE, "size": 14})]])
    steps = ["Create the case (incident, hospital)", "Upload bills and medical reports",
             "Agent checks rules, flags alerts", "Family approves and assigns tasks", "Share the PDF case package"]
    for i, st in enumerate(steps):
        y = 2.85 + i * 0.5
        circle_num(s, 7.75, y, 0.36, i + 1, fill=ORANGE if i == 2 else NAVY)
        text_box(s, 8.25, y, 4.3, 0.36, [[(st, {"size": 13})]], anchor=MSO_ANCHOR.MIDDLE)


def tech(s):
    sub, lab, bl = ids(s)
    b = content_frame(s, "Proven, fast-to-build tools around one idea: every capability lives in an MCP server any AI host can use.",
                      None, lab, sub, bl)
    remove(b)
    cards = [
        ("Frontend", [("React + TypeScript + Vite,", "Tailwind CSS v4"), "Mobile-first, fast to iterate, calm UI for stressed families."]),
        ("Agent host", [("FastAPI + Anthropic Claude", "(tool use)"), "Runs the tool loop, approval gate and audit log; LLM is swappable."]),
        ("MCP layer", [("Official MCP Python SDK v2,", "Streamable HTTP"), "9 tools, 3 resources, 1 prompt; Inspector or Claude Desktop connect too."]),
        ("Documents & reports", [("PyMuPDF + Claude vision;", "ReportLab"), "Rule-based extraction for text PDFs, vision for photos, PDF case package."]),
        ("Knowledge (RAG)", [("rank-bm25", "over curated PIB/MoRTH corpus"), "Small, auditable corpus: answers carry title, URL and date."]),
        ("Data & cloud", [("SQLite + SQLAlchemy", "→ AWS RDS/S3"), "Zero-setup for the MVP; private uploads with SHA-256 hashes."]),
    ]
    w, h, gx, gy = 3.75, 1.3, 0.3, 0.22
    for i, (t, lines) in enumerate(cards):
        x = 0.7 + (i % 3) * (w + gx)
        y = 2.45 + (i // 3) * (h + gy)
        labeled_card(s, x, y, w, h, t, lines, title_color=BLUE if i == 2 else NAVY, size=12, name=f"Stack {t}")
    text_box(s, 0.7, 5.5, 9.4, 0.5, [[("Next 24 hrs: ", {"bold": True, "color": ORANGE, "size": 13}),
                                      ("ElevenLabs voice read-out (Kannada/Hindi/English) and AWS deployment (App Runner + RDS + S3).", {"size": 13})]])


def architecture(s):
    sub, lab, bl = ids(s)
    b = content_frame(s, "Every agent action goes through the MCP server; writes wait for a family member's approval.",
                      None, lab, sub, bl)
    remove(b)
    top, h = 2.45, 1.15
    boxes = [
        ("Family web app", "React + Tailwind", "Dashboard, chat, vault, tasks, MCP panel", NAVY),
        ("Agent host", "FastAPI + Claude", "Tool-use loop, approval gate, audit log", NAVY),
        ("MCP server :8001", "MCP SDK v2 · HTTP", "9 tools · 3 resources · 1 prompt", ORANGE),
        ("Services", "Python", "Cases, watchers, documents, RAG, PDF", NAVY),
    ]
    w, gap = 2.6, 0.42
    xs = [0.7 + i * (w + gap) for i in range(4)]
    for (t, tech_, desc, col), x in zip(boxes, xs):
        card(s, x, top, w, h, fill=col, line=None, name=f"Block {t}")
        text_box(s, x + 0.15, top + 0.1, w - 0.3, h - 0.2,
                 [[(t, {"bold": True, "color": WHITE, "size": 14})], [(tech_, {"italic": True, "color": WHITE, "size": 11})],
                  [(desc, {"color": WHITE, "size": 11})]])
    labels = ["REST", "MCP", "calls"]
    for i in range(3):
        x1, x2 = xs[i] + w + 0.03, xs[i + 1] - 0.03
        arrow(s, x1, top + h / 2, x2, top + h / 2)
        text_box(s, x1 - 0.1, top + h / 2 - 0.32, x2 - x1 + 0.2, 0.25, [[(labels[i], {"size": 9, "color": MUTED})]], align=PP_ALIGN.CENTER)
    low, lh = 4.05, 0.8
    lows = [
        (xs[1], "Claude API", "Picks tools from the live MCP list", BLUE),
        (xs[2], "2nd MCP host", "MCP Inspector / Claude Desktop", BLUE),
        (xs[3], "Data", "SQLite · private uploads · knowledge/", BLUE),
    ]
    for x, t, d, col in lows:
        card(s, x, low, w, lh, fill=TINT, line=col, name=f"Block {t}")
        text_box(s, x + 0.15, low + 0.08, w - 0.3, lh - 0.12, [[(t, {"bold": True, "color": col, "size": 12.5})], [(d, {"size": 11})]])
        arrow(s, x + w / 2, top + h + 0.03, x + w / 2, low - 0.03, color=BLUE, width=1.25)
    # process strip
    steps = ["Input: question or upload", "Discover MCP tools", "Read-only tools run", "Writes → Approve card", "Output: cited answer, alert, task, PDF"]
    sx, sw, sy = 0.7, 1.78, 5.2
    for i, st in enumerate(steps):
        x = sx + i * (sw + 0.12)
        card(s, x, sy, sw, 0.62, fill=WHITE, name=f"Step {i + 1}")
        text_box(s, x + 0.1, sy + 0.05, sw - 0.2, 0.52, [[(f"{i + 1}. ", {"bold": True, "color": ORANGE, "size": 11}), (st, {"size": 11})]],
                 anchor=MSO_ANCHOR.MIDDLE)


def novelty(s):
    sub, lab, bl = ids(s)
    b = content_frame(s, "Not another chatbot: a case agent that is cited, proactive, approval-gated and open through MCP.",
                      "OUR USP", lab, sub, bl)
    b.width = Inches(4.7)
    fill_bullets(b, [
        ("MCP-native:", "the same live case works in our app, MCP Inspector or Claude Desktop."),
        ("Deterministic watchers,", "not LLM guesses, for the 7-day window, ₹1.5 lakh cover and police follow-ups."),
        ("Safety by design:", "official-source answers only, untrusted documents, approvals from tool annotations."),
    ], size=1400)
    rows = [("", "Second Hour", "Generic AI chatbot", "Helpline / portal"),
            ("Remembers the whole case", "Yes", "No", "No"),
            ("Cited official answers only", "Yes", "Often guesses", "Partly"),
            ("Proactive deadline alerts", "Yes", "No", "No"),
            ("Approval before any action", "Yes", "n/a", "n/a"),
            ("Family shares one workspace", "Yes", "No", "No"),
            ("Open to other AI hosts (MCP)", "Yes", "No", "No")]
    x, y, w = 5.75, 2.45, 6.8
    tbl = s.shapes.add_table(len(rows), 4, Inches(x), Inches(y), Inches(w), Inches(0.36 * len(rows))).table
    widths = [2.6, 1.35, 1.5, 1.35]
    for i, cw in enumerate(widths):
        tbl.columns[i].width = Inches(cw)
    for r, row in enumerate(rows):
        tbl.rows[r].height = Inches(0.36)
        for c, val in enumerate(row):
            cell = tbl.cell(r, c)
            cell.fill.solid()
            cell.fill.fore_color.rgb = NAVY if r == 0 else (TINT if c == 1 else WHITE)
            cell.margin_left = cell.margin_right = Inches(0.08)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT if c == 0 else PP_ALIGN.CENTER
            run = p.add_run()
            run.text = val
            run.font.name = FONT
            run.font.size = Pt(12)
            run.font.bold = r == 0 or (c == 1)
            run.font.color.rgb = WHITE if r == 0 else (BLUE if c == 1 else INK)


def impact(s):
    sub, lab, bl = ids(s)
    b = content_frame(s, "Fewer missed steps for families in crisis, built on a stack we already have running end to end.",
                      None, lab, sub, bl)
    remove(b)
    cols = [
        ("Impact", NAVY, [("Who:", "families of road-accident victims, hospital help desks, NGOs."),
                          ("Outcomes:", "fewer missed police follow-ups, earlier billing conversations, complete paperwork."),
                          ("Scale:", "any state; MCP lets hospital and insurer agents plug in.")]),
        ("Feasibility", BLUE, [("Technical:", "working MVP: 9 MCP tools, approvals, PDF, 9 passing tests."),
                               ("Time:", "core built in one day; 24 hrs adds voice, languages, cloud."),
                               ("Cost:", "open-source stack; pay-per-use LLM and voice APIs.")]),
        ("Risks → mitigation", ORANGE, [("Wrong rules:", "answers only from cited official text."),
                                        ("Bad extraction:", "every field “Needs review” until confirmed."),
                                        ("Over-reliance:", "112 banner, no legal advice, no eligibility calls."),
                                        ("Privacy:", "membership checks, private uploads, audit log.")]),
    ]
    w, gap, y, h = 3.75, 0.3, 2.45, 2.4
    for i, (t, col, lines) in enumerate(cols):
        labeled_card(s, 0.7 + i * (w + gap), y, w, h, t, lines, title_color=col, size=12.5, name=f"Column {t}")
    text_box(s, 0.7, 5.15, 9.5, 0.4, [[("Stat behind it: ", {"bold": True, "color": ORANGE, "size": 13}),
                                       ("3,674 PM-RAHAT victims discharged after no police response in time (PIB, 12 Aug 2026).", {"size": 13})]])


def business(s):
    sub, lab, bl = ids(s)
    b = content_frame(s, "Free for families; sustained by hospitals, insurers and partners who benefit from organised cases.",
                      "MODEL", lab, sub, bl)
    b.width = Inches(6.7)
    fill_bullets(b, [
        ("Customers:", "every PM-RAHAT family (22,481 victims by 31 Jul 2026), plus hospital help desks, TPAs and insurers."),
        ("Revenue:", "free for families; B2B licence for hospitals/TPAs per active case; insurer and CSR sponsorship."),
        ("Go-to-market:", "pilot at Bengaluru empanelled hospitals via a QR code at the emergency desk; road-safety NGOs."),
        ("Key costs:", "LLM and voice API usage, cloud hosting, support. Partners: hospitals, insurers, NGOs, AWS, ElevenLabs."),
        ("Growth:", "more schemes and claims (motor accident claims, insurance), Indian languages, open MCP for partner agents."),
    ], size=1400)
    tiers = [("Families", "Free, always", NAVY), ("Hospitals & TPAs", "Per-case licence", BLUE), ("Insurers & CSR", "Sponsorship", ORANGE)]
    for i, (t, d, col) in enumerate(tiers):
        y = 2.45 + i * 0.95
        card(s, 7.85, y, 4.7, 0.78, fill=WHITE, line=col, name=f"Tier {t}")
        circle_num(s, 8.02, y + 0.2, 0.38, i + 1, fill=col)
        text_box(s, 8.55, y + 0.1, 3.9, 0.6, [[(t, {"bold": True, "color": col, "size": 14})], [(d, {"size": 12})]], anchor=MSO_ANCHOR.MIDDLE)


def footer(prs):
    for layout in prs.slide_layouts:
        for sh in layout.shapes:
            if sh.has_text_frame and "<Team Name>" in sh.text_frame.text:
                for p in sh.text_frame.paragraphs:
                    for r in p.runs:
                        r.text = r.text.replace("<Team Name>", TEAM["name"]).replace("<Team ID>", TEAM["id"])


def main(src, dst):
    prs = Presentation(src)
    sl = prs.slides
    footer(prs)
    cover(sl[0])
    problem(sl[1])
    solution(sl[2])
    tech(sl[3])
    architecture(sl[4])
    novelty(sl[5])
    impact(sl[6])
    business(sl[7])
    prs.save(dst)
    print("saved", dst)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
