"""Preprocessor for legal questions dataset.

Cleans raw HTML enunciados, unescapes entities, normalizes whitespace,
extracts legal citations (articles, laws, súmulas), and structures data.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class Question:
    id: str
    enunciado_html: str
    comando: str
    alternativas: Dict[str, str]
    disciplina_origem: str
    assunto_origem: str

    clean_enunciado: str = ""
    clean_comando: str = ""
    clean_alternativas: Dict[str, str] = field(default_factory=dict)
    full_text: str = ""
    legal_citations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "disciplina_origem": self.disciplina_origem,
            "assunto_origem": self.assunto_origem,
            "clean_enunciado": self.clean_enunciado,
            "clean_comando": self.clean_comando,
            "clean_alternativas": self.clean_alternativas,
            "full_text": self.full_text,
            "legal_citations": self.legal_citations,
        }


class QuestionPreprocessor:
    """Cleans and standardizes raw question data."""

    TAG_RE = re.compile(r"<[^>]+>")
    CITATION_PATTERNS = [
        re.compile(r"\barts?\.?\s*\d+[\wºª\-\.\,\s]*?(?:do\s+(?:CP|CPP|CPC|CTB|CDC|ECA|Estatuto\s+do\s+Idoso)|da\s+(?:CF|Constituição|LEP|LICC|LINDB))", re.IGNORECASE),
        re.compile(r"\blei\s*(?:n[ºo\.]?\s*)?\d+[\.\d]*(?:/\d{2,4})?", re.IGNORECASE),
        re.compile(r"\bsúmula(?:\s+vinculante)?\s*(?:n[ºo\.]?\s*)?\d+(?:\s+do\s+(?:STF|STJ|TST))?", re.IGNORECASE),
        re.compile(r"\b(?:código\s+penal|código\s+de\s+processo\s+penal|constituição\s+federal|lei\s+de\s+execução\s+penal)", re.IGNORECASE),
    ]

    @classmethod
    def clean_html_text(cls, text: Optional[str]) -> str:
        if not text:
            return ""
        # Unescape HTML entities
        text = html.unescape(text)
        # Replace line-breaking HTML tags with spaces
        text = re.sub(r"<(?:br|p|div|li|tr|h\d)[^>]*>", "\n", text, flags=re.IGNORECASE)
        # Strip all other tags
        text = cls.TAG_RE.sub(" ", text)
        # Normalize non-breaking spaces and whitespace
        text = text.replace("\xa0", " ")
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]
        return "\n".join(l for l in lines if l).strip()

    @classmethod
    def extract_citations(cls, text: str) -> List[str]:
        citations: List[str] = []
        for pattern in cls.CITATION_PATTERNS:
            matches = pattern.findall(text)
            for m in matches:
                clean_m = re.sub(r"\s+", " ", m).strip()
                if clean_m and clean_m not in citations:
                    citations.append(clean_m)
        return citations

    @classmethod
    def process(cls, raw: Dict) -> Question:
        q_id = str(raw.get("id", "")).strip()
        enun_raw = str(raw.get("enunciado_html") or "")
        cmd_raw = str(raw.get("comando") or "")
        alts_raw = raw.get("alternativas") or {}

        clean_enun = cls.clean_html_text(enun_raw)
        clean_cmd = cls.clean_html_text(cmd_raw)

        clean_alts: Dict[str, str] = {}
        if isinstance(alts_raw, dict):
            for k, v in alts_raw.items():
                clean_alts[str(k).strip()] = cls.clean_html_text(str(v or ""))
        elif isinstance(alts_raw, list):
            for i, v in enumerate(alts_raw):
                clean_alts[chr(ord("A") + i)] = cls.clean_html_text(str(v or ""))

        # Compose full text
        alt_str = " ".join(f"[{k}] {v}" for k, v in clean_alts.items())
        parts = [p for p in [clean_enun, clean_cmd, alt_str] if p]
        full_text = " \n".join(parts)

        citations = cls.extract_citations(full_text)

        return Question(
            id=q_id,
            enunciado_html=enun_raw,
            comando=cmd_raw,
            alternativas=alts_raw,
            disciplina_origem=str(raw.get("disciplina_origem") or "").strip(),
            assunto_origem=str(raw.get("assunto_origem") or "").strip(),
            clean_enunciado=clean_enun,
            clean_comando=clean_cmd,
            clean_alternativas=clean_alts,
            full_text=full_text,
            legal_citations=citations,
        )

    @classmethod
    def load_dataset(cls, jsonl_path: str | Path | None = None) -> List[Question]:
        if jsonl_path is None:
            for candidate in ["data/questoes.jsonl", "anexos-case-ia/anexos/questoes.jsonl", "../data/questoes.jsonl"]:
                if Path(candidate).exists():
                    jsonl_path = candidate
                    break
        if jsonl_path is None:
            jsonl_path = "data/questoes.jsonl"
        path = Path(jsonl_path)
        if not path.exists():
            raise FileNotFoundError(f"Arquivo de questões não encontrado: {path}")

        questions: List[Question] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                questions.append(cls.process(data))
        return questions


# Funções de conveniência
def clean_html(text: Optional[str]) -> str:
    return QuestionPreprocessor.clean_html_text(text)


def extract_canonical_question(raw: Dict) -> Dict:
    q = QuestionPreprocessor.process(raw)
    return {
        "id": q.id,
        "enunciado": q.clean_enunciado,
        "comando": q.clean_comando,
        "alternativas": " ".join(f"[{k}] {v}" for k, v in q.clean_alternativas.items()),
        "alternativas_dict": q.clean_alternativas,
        "disciplina_origem": q.disciplina_origem,
        "assunto_origem": q.assunto_origem,
        "full_text": q.full_text,
        "legal_mentions": q.legal_citations,
    }
