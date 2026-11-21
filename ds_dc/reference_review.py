"""Small independently reviewed excerpts for the offline operator pilot."""
from pathlib import Path
import re
import subprocess

from .corpus import BKD, PIN, MAX_SIZE, digest
from .pdf_policy import pdf_tool
from .runtime import ReviewedEvidence

MASS = re.compile(r"(?:какая\s+масса|масса|сколько\s+весит)", re.I)
MODEL = re.compile(r"БКД[-–]ПК[-–]RF\.2", re.I)
ALLOWED_FILLER = {"у", "контроллера", "изделия", "он", "его", "она",
                  "предельная", "предельный", "предел", "значение", "это"}


def reference_review(cache: Path):
    """Use an independently transcribed row only for its reviewed scope and question."""
    def review(question, _candidate, documents, _diagnostics):
        parts = tuple(part.strip() for part in re.split(r"\s+и\s+|[;?]+", question) if part.strip())
        confirmed = {}
        if not documents or {doc["scope"] for doc in documents} != {BKD}:
            return ReviewedEvidence(parts, confirmed)
        sha, pages = PIN[BKD]
        if not any(doc["sha256"] == sha and doc["pages"] == pages for doc in documents):
            return ReviewedEvidence(parts, confirmed)
        matches = [part for part in parts if MASS.search(part)
                   and set(re.findall(r"[\w-]+", MASS.sub("", MODEL.sub("", part)).lower()))
                   <= ALLOWED_FILLER]
        if not matches:
            return ReviewedEvidence(parts, confirmed)
        path = cache / (sha + ".pdf")
        try:
            if path.stat().st_size > MAX_SIZE or digest(path.read_bytes()) != sha:
                return ReviewedEvidence(parts, confirmed)
            text = pdf_tool("pdftotext", "-f", "4", "-l", "4", "-layout", path, "-")
        except (OSError, ValueError, subprocess.SubprocessError):
            return ReviewedEvidence(parts, confirmed)
        if re.search(r"^Масса, кг, не более\s+0,5\s*$", text, re.M):
            for part in matches:
                confirmed[part] = "Масса БКД-ПК-RF.2 — не более 0,5 кг (РЭ ЕСАН.426469.012РЭ, физ. стр. 4)."
        return ReviewedEvidence(parts, confirmed)
    return review
