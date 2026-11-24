"""BM25 retrieval over the curated PM-RAHAT knowledge base in knowledge/."""
from __future__ import annotations

import re
from functools import lru_cache

from rank_bm25 import BM25Okapi

from app.config import KNOWLEDGE_DIR

STOP = set("a an the of to in for on and or is are be by with from at as it this that what how when who do does can i my we our you your".split())


def _tok(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9₹.]+", s.lower().replace("pm-rahat", "pmrahat")) if w not in STOP]


def _parse(path) -> tuple[dict, str]:
    raw = path.read_text(encoding="utf-8")
    meta: dict = {}
    body = raw
    if raw.startswith("---"):
        _, fm, body = raw.split("---", 2)
        for line in fm.strip().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip().strip('"')
    meta["file"] = path.name
    return meta, body.strip()


@lru_cache(maxsize=1)
def _index():
    chunks: list[dict] = []
    for p in sorted(KNOWLEDGE_DIR.glob("*.md")):
        meta, body = _parse(p)
        section = ""
        for para in re.split(r"\n\s*\n", body):
            para = para.strip()
            if not para:
                continue
            if para.startswith("#"):
                section = para.lstrip("# ").splitlines()[0]
                rest = "\n".join(para.splitlines()[1:]).strip()
                if not rest:
                    continue
                para = rest
            chunks.append({"text": para, "section": section, **meta})
    bm25 = BM25Okapi([_tok(c["section"] + " " + c["text"]) for c in chunks]) if chunks else None
    return chunks, bm25


def search(question: str, k: int = 4) -> dict:
    if not question or not question.strip():
        return {"question": question, "results": [], "found": False, "message": "Empty question."}
    chunks, bm25 = _index()
    q = _tok(question)
    if not bm25 or not q:
        return {"question": question, "results": [], "found": False,
                "message": "No matching passage in the curated official sources."}
    scores = bm25.get_scores(q)
    ranked = sorted(range(len(chunks)), key=lambda i: scores[i], reverse=True)
    results = []
    for i in ranked[:k]:
        if scores[i] <= 0.5:
            break
        c = chunks[i]
        results.append({"snippet": c["text"], "section": c["section"], "score": round(float(scores[i]), 2),
                        "source": {"title": c.get("title"), "publisher": c.get("publisher"), "url": c.get("url"),
                                   "date": c.get("date"), "last_reviewed": c.get("last_reviewed"),
                                   "verification": c.get("verification", "verified")}})
    if not results:
        return {"question": question, "results": [], "found": False,
                "message": "No matching passage in the curated official sources. Second Hour will not answer this from memory."}
    return {"question": question, "results": results, "found": True,
            "instructions": "Answer only from these snippets and cite source title, URL and date."}


def overview_text() -> str:
    p = KNOWLEDGE_DIR / "00_overview.md"
    return p.read_text(encoding="utf-8") if p.exists() else "No overview available."
