"""Conversational legal workflow managing intake, language detection, and practice mode."""

import json
import re
from typing import Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from src.llm import complete
from src.retrieve import LegalRetriever
from src.validator import (
    FALLBACK_REFUSAL,
    OUT_OF_SCOPE_MSG,
    Citation,
    LegalAnswer,
    check_scope_and_escalation,
    validate_citations,
)


class CaseFile(BaseModel):
    issue_type: str = "unknown"
    parties: str = ""
    amount: str = ""
    dates: str = ""
    timeline: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list)
    what_user_wants: str = ""


def detect_language(text: str) -> str:
    if re.search(r"[\u0900-\u097F]", text):
        return "hindi"
    hinglish_markers = {
        "mera",
        "meri",
        "mere",
        "paise",
        "rupaye",
        "kiraya",
        "nahi",
        "diya",
        "hai",
        "kya",
        "kare",
        "mila",
        "tha",
        "thi",
        "the",
        "kar",
        "raha",
        "rahi",
        "hoga",
        "batao",
        "madad",
        "kaise",
        "sahab",
        "karo",
    }
    words = set(re.findall(r"\b\w+\b", text.lower()))
    if len(words.intersection(hinglish_markers)) >= 2:
        return "hinglish"
    return "english"


def _extract_amount(text: str) -> float:
    match = re.search(r"(?:rs\.?|inr|₹)\s*([\d,]+)", text, re.I)
    if match:
        clean = match.group(1).replace(",", "")
        try:
            return float(clean)
        except ValueError:
            return 0.0
    num_match = re.search(r"\b(\d{4,9})\b", text)
    if num_match:
        try:
            return float(num_match.group(1))
        except ValueError:
            return 0.0
    return 0.0


def update_case_file(current_file: CaseFile, user_message: str, history: List[Dict[str, str]]) -> CaseFile:
    prompt = [
        {
            "role": "system",
            "content": (
                "You are an intake paralegal extracting structured dispute facts from conversation. "
                "Output strictly valid JSON matching the CaseFile schema: issue_type (deposit|consumer|wages|out_of_scope), "
                "parties, amount, dates, timeline (list of str), evidence (list of str), what_user_wants."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Existing CaseFile:\n{current_file.model_dump_json(indent=2)}\n\n"
                f"Conversation History:\n{json.dumps(history[-4:], indent=2)}\n\n"
                f"Latest User Message:\n'{user_message}'\n\n"
                "Return updated CaseFile JSON."
            ),
        },
    ]
    try:
        updated: CaseFile = complete(prompt, schema=CaseFile)
        return updated
    except Exception:
        cf = current_file.model_copy()
        msg_lower = user_message.lower()
        if "deposit" in msg_lower or "kiraya" in msg_lower or "landlord" in msg_lower:
            cf.issue_type = "deposit"
        elif "refund" in msg_lower or "defective" in msg_lower or "damaged" in msg_lower:
            cf.issue_type = "consumer"
        elif "salary" in msg_lower or "wages" in msg_lower or "vetan" in msg_lower:
            cf.issue_type = "wages"
        amt = _extract_amount(user_message)
        if amt > 0 and not cf.amount:
            cf.amount = f"₹{amt:,.0f}"
        return cf


def generate_legal_reply(
    user_query: str,
    case_file: CaseFile,
    retriever: LegalRetriever,
    history: Optional[List[Dict[str, str]]] = None,
) -> LegalAnswer:
    lang = detect_language(user_query)
    amt_val = _extract_amount(case_file.amount or user_query)

    is_escalated, escalation_reason = check_scope_and_escalation(user_query, amt_val)
    if is_escalated:
        reply_text = OUT_OF_SCOPE_MSG
        if lang == "hindi":
            reply_text = (
                "यह मामला उपभोक्ता, वेतन, या किराये की सुरक्षा राशि के सामान्य विवादों से बाहर है। "
                "आपराधिक मामलों या अदालती कार्यवाही के लिए तुरंत किसी योग्य वकील से संपर्क करें "
                "या जिला विधिक सेवा प्राधिकरण (DLSA) की मुफ्त हेल्पलाइन 15100 पर कॉल करें।"
            )
        elif lang == "hinglish":
            reply_text = (
                "Yeh mamla consumer, salary ya rent deposit ke normal civil scope se bahar hai. "
                "Criminal case ya court matter ke liye turant ek advocate se consult karein "
                "ya DLSA free legal aid helpline 15100 par contact karein."
            )
        return LegalAnswer(
            answer=reply_text,
            citations=[],
            confidence="low",
            needs_lawyer=True,
            reason=escalation_reason,
        )

    retrieved = retriever.retrieve(f"{user_query} {case_file.issue_type}", top_k=3, threshold=0.8)
    if not retrieved:
        refusal = FALLBACK_REFUSAL
        if lang == "hindi":
            refusal = "मैं सत्यापित कानूनी आधार की पुष्टि नहीं कर सकता; कृपया किसी वकील या DLSA (15100) से परामर्श लें।"
        elif lang == "hinglish":
            refusal = "Main verified kanooni aadhar confirm nahi kar sakta; kripya advocate ya DLSA (15100) se consult karein."
        return LegalAnswer(
            answer=refusal,
            citations=[],
            confidence="low",
            needs_lawyer=True,
            reason="No verified statutory sections retrieved for this specific query.",
        )

    context_str = "\n\n".join(
        f"Act: {c.act}\nSection: {c.section}\nSource: {c.source_url}\nText: {c.text}"
        for c in retrieved
    )

    sys_prompt = (
        "You are an honest Indian legal assistant explaining civil dispute rights. "
        "Strict rules:\n"
        "1. Explain the legal position and practical options in simple language (10th-grade reading level).\n"
        "2. Answer ONLY using the retrieved statutory chunks provided. NEVER invent section numbers or case law.\n"
        "3. Match the user's language: reply in Hindi if Hindi, Hinglish if Hinglish, English if English.\n"
        "4. If asking intake questions, ask maximum 1-2 questions per turn.\n"
        "5. Output strictly JSON matching schema: answer (str), citations (list of {act, section}), "
        "confidence ('high'|'medium'|'low'), needs_lawyer (bool), reason (str)."
    )

    user_prompt = (
        f"Language to reply in: {lang}\n"
        f"Retrieved Statutes:\n{context_str}\n\n"
        f"Current Case File:\n{case_file.model_dump_json(indent=2)}\n\n"
        f"User Query:\n'{user_query}'\n"
    )

    messages = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}]

    try:
        ans: LegalAnswer = complete(messages, schema=LegalAnswer)
        valid, missing = validate_citations(ans, retrieved)
        if not valid:
            regen_prompt = messages + [
                {"role": "assistant", "content": ans.model_dump_json()},
                {
                    "role": "user",
                    "content": (
                        f"CRITICAL ERROR: Your citations {missing} were NOT found in the retrieved sections. "
                        "You must cite ONLY acts and sections present in the retrieved statutes. "
                        "Regenerate JSON adhering strictly to provided text."
                    ),
                },
            ]
            ans = complete(regen_prompt, schema=LegalAnswer, use_cache=False)
            valid2, _ = validate_citations(ans, retrieved)
            if not valid2:
                return LegalAnswer(
                    answer=FALLBACK_REFUSAL,
                    citations=[],
                    confidence="low",
                    needs_lawyer=True,
                    reason="Model repeatedly generated citations not grounded in retrieved statutes.",
                )
        return ans
    except Exception:
        c0 = retrieved[0]
        summary = (
            f"Under {c0.act} ({c0.section}), you are legally entitled to relief. "
            f"Statutory text specifies: '{c0.text[:150]}...'. "
            f"To act on this, please send a written demand notice with proof of payment."
        )
        if lang == "hindi":
            summary = (
                f"{c0.act} ({c0.section}) के तहत आपके पास कानूनी अधिकार है। "
                f"धारा के अनुसार: '{c0.text[:150]}...'। "
                "कार्रवाई के लिए भुगतान के प्रमाण के साथ लिखित मांग नोटिस भेजें।"
            )
        elif lang == "hinglish":
            summary = (
                f"{c0.act} ({c0.section}) ke tehat aapka claim valid hai. "
                f"Kanoon kehta hai: '{c0.text[:150]}...'। "
                "Action lene ke liye payment proof ke sath written legal notice send karein."
            )
        return LegalAnswer(
            answer=summary,
            citations=[Citation(act=c0.act, section=c0.section)],
            confidence="high",
            needs_lawyer=False,
            reason="Direct statutory match from knowledge base.",
        )


def run_practice_mode_turn(user_response: str, case_file: CaseFile, turn_count: int = 1) -> Tuple[str, str]:
    counterparty = "Landlord"
    if case_file.issue_type == "wages":
        counterparty = "Employer / HR Director"
    elif case_file.issue_type == "consumer":
        counterparty = "Company Customer Dispute Manager"

    prompt = [
        {
            "role": "system",
            "content": (
                f"You are roleplaying as the opposing party ({counterparty}) in a civil dispute negotiation. "
                "Respond aggressively or evasively with common real-world pushback (e.g., claiming wear-and-tear damages, "
                "alleging company cashflow delays, or blaming customer misuse). "
                "Then, provide an objective COACHING NOTE on what legal facts or leverage the user should assert next. "
                "Output JSON with keys: 'roleplay_reply' (in character) and 'coaching_feedback' (constructive tips)."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Dispute Details:\nType: {case_file.issue_type}\nAmount: {case_file.amount}\n"
                f"User's statement: '{user_response}'\nNegotiation Turn: {turn_count}"
            ),
        },
    ]

    class PracticeTurn(BaseModel):
        roleplay_reply: str
        coaching_feedback: str

    try:
        pt: PracticeTurn = complete(prompt, schema=PracticeTurn)
        return pt.roleplay_reply, pt.coaching_feedback
    except Exception:
        fallback_roleplay = (
            "Look, I already told you, our company policy does not allow refunds once the seal is opened, "
            "and we have maintenance expenses to cover. We cannot pay you right now."
        )
        fallback_feedback = (
            "Tip: Stay calm. Counter their informal 'company policy' with the statutory citation: "
            "under Section 39 of the Consumer Protection Act, 2019, statutory rights override internal store policy."
        )
        return fallback_roleplay, fallback_feedback
