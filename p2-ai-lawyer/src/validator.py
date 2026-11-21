"""Honesty layer validating citations against retrieved chunks and assessing escalation."""

import re
from typing import List, Tuple

from pydantic import BaseModel

from src.retrieve import LegalChunk


class Citation(BaseModel):
    act: str
    section: str


class LegalAnswer(BaseModel):
    answer: str
    citations: List[Citation]
    confidence: str
    needs_lawyer: bool
    reason: str


FALLBACK_REFUSAL = (
    "I can't confirm the legal basis; please consult a lawyer or your local "
    "District Legal Services Authority (DLSA) at free legal aid helpline 15100."
)

CRIMINAL_KEYWORDS = {
    "fir",
    "police",
    "arrest",
    "bail",
    "jail",
    "criminal",
    "ipc",
    "assault",
    "theft",
    "murder",
    "threaten to kill",
    "mar pit",
    "maar peet",
    "dowry",
    "divorce",
    "custody",
    "lock the landlord",
    "lock inside",
    "hostage",
    "confinement",
    "illegal",
    "physical force",
}

OUT_OF_SCOPE_MSG = (
    "This issue falls outside everyday consumer, wage, or rental deposit civil claims. "
    "For criminal matters, family disputes, or formal litigation, please consult a licensed advocate "
    "or call the District Legal Services Authority (DLSA) at toll-free helpline 15100."
)


def check_scope_and_escalation(query: str, amount_inr: float = 0.0) -> Tuple[bool, str]:
    q_lower = query.lower()
    for kw in CRIMINAL_KEYWORDS:
        if re.search(r"\b" + re.escape(kw) + r"\b", q_lower):
            return True, f"Criminal or family law issue detected ({kw}). Immediate advocate consultation required."

    if any(term in q_lower for term in ("court tomorrow", "hearing scheduled", "court date", "judge", "summons")):
        return True, "Active court proceedings or formal court summons require immediate advocate representation."

    if any(term in q_lower for term in ("thrown out", "locked out tonight", "eviction today", "threw my luggage")):
        return True, "Imminent physical eviction requires urgent local legal aid or police intervention."

    if amount_inr > 2000000.0:
        return True, f"High claim amount (₹{amount_inr:,.0f}) exceeds summary dispute threshold."

    return False, ""


def validate_citations(answer: LegalAnswer, retrieved_chunks: List[LegalChunk]) -> Tuple[bool, List[str]]:
    if not answer.citations:
        return True, []

    chunk_keys = {
        (c.act.strip().lower(), c.section.strip().lower())
        for c in retrieved_chunks
    }

    invalid_citations = []
    for cit in answer.citations:
        c_act = cit.act.strip().lower()
        c_sec = cit.section.strip().lower()

        matched = False
        for act_key, sec_key in chunk_keys:
            if (act_key in c_act or c_act in act_key) and (sec_key in c_sec or c_sec in sec_key):
                matched = True
                break
        if not matched:
            invalid_citations.append(f"{cit.act} - {cit.section}")

    return (len(invalid_citations) == 0), invalid_citations
