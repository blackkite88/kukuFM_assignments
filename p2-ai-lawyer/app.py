"""Streamlit application for AI Lawyer civil claims assistance in India."""

import os
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from src.audio import synthesize_speech, transcribe_audio
from src.draft import generate_document
from src.flow import (
    CaseFile,
    generate_legal_reply,
    run_practice_mode_turn,
    update_case_file,
)
from src.retrieve import LegalRetriever

load_dotenv()

st.set_page_config(page_title="P2: AI Lawyer (India)", layout="wide")

st.error(
    "**STATUTORY NOTICE: THIS SYSTEM IS AN AI ASSISTANT, NOT A LICENSED LAWYER.**\n\n"
    "Information provided is for educational and self-advocacy purposes. It does not constitute legal representation. "
    "For complex litigation, criminal matters, or formal representation, consult a licensed advocate or contact "
    "the District Legal Services Authority (DLSA) at free legal aid helpline **15100**."
)

st.info(
    "**COVERED CIVIL SCOPE:**\n"
    "1. **Security Deposit Not Returned** (Model Tenancy Act / Rent Disputes)\n"
    "2. **Consumer Refund / Defective Product** (Consumer Protection Act, 2019 / e-Daakhil)\n"
    "3. **Unpaid Wages / Arbitrary Deductions** (Payment of Wages Act, 1936 / Code on Wages, 2019)\n\n"
    "*All criminal matters, family disputes, and property title litigations are out of scope.*"
)

active_model = os.getenv("MODEL", "gemini/gemini-2.0-flash")
st.sidebar.header("System Settings")
st.sidebar.text(f"Model: {active_model}")

has_api_key = bool(
    os.getenv("GEMINI_API_KEY")
    or os.getenv("OPENAI_API_KEY")
    or os.getenv("ANTHROPIC_API_KEY")
    or os.getenv("GROQ_API_KEY")
)
if not has_api_key:
    st.sidebar.warning("No live API key found. Operating in grounded fallback mode.")

practice_mode = st.sidebar.toggle("Negotiation Practice Mode (AI plays other side)")

if "retriever" not in st.session_state:
    st.session_state.retriever = LegalRetriever()

if "case_file" not in st.session_state:
    st.session_state.case_file = CaseFile()

if "messages" not in st.session_state:
    st.session_state.messages = []

st.sidebar.header("Live Case File (Editable)")
cf = st.session_state.case_file
issue_idx = ["deposit", "consumer", "wages", "out_of_scope"].index(
    cf.issue_type if cf.issue_type in ["deposit", "consumer", "wages", "out_of_scope"] else "deposit"
)
cf.issue_type = st.sidebar.selectbox("Issue Type", ["deposit", "consumer", "wages", "out_of_scope"], index=issue_idx)
cf.parties = st.sidebar.text_input("Opposing Party", value=cf.parties)
cf.amount = st.sidebar.text_input("Disputed Amount (INR)", value=cf.amount)
cf.dates = st.sidebar.text_input("Incident / Contract Dates", value=cf.dates)
cf.what_user_wants = st.sidebar.text_input("Desired Remedy", value=cf.what_user_wants)

st.sidebar.subheader("Document Drafting")
if st.sidebar.button("Generate Legal Document (.docx)"):
    draft_path = Path("outputs/legal_draft.docx")
    out_file = generate_document(cf, draft_path)
    with open(out_file, "rb") as f:
        st.sidebar.download_button(
            "Download Draft Document (.docx)",
            f.read(),
            file_name=f"{cf.issue_type}_notice_draft.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

voice_bytes = st.audio_input("Dictate Voice Input (Whisper STT)")
voice_text = ""
if voice_bytes:
    with st.spinner("Transcribing speech..."):
        voice_text = transcribe_audio(voice_bytes.read())
        if voice_text and not voice_text.startswith("Audio transcription unavailable"):
            st.success(f"Transcribed: {voice_text}")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if "citations" in msg and msg["citations"]:
            with st.expander("Statutory Citations & Verification", expanded=False):
                for cit in msg["citations"]:
                    st.markdown(f"- **{cit['act']}** ({cit['section']})")
        if "confidence" in msg:
            st.caption(f"Honesty Confidence: **{msg['confidence'].upper()}**")
        if msg.get("needs_lawyer"):
            st.warning("Advocate Consultation Advised: Contact DLSA free legal aid at helpline 15100.")

prompt_input = st.chat_input("Describe your issue (in English, Hindi, or Hinglish)...")
user_query = voice_text or prompt_input

if user_query:
    st.session_state.messages.append({"role": "user", "content": user_query})
    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        with st.spinner("Checking Indian statutes and casefile..."):
            st.session_state.case_file = update_case_file(
                st.session_state.case_file, user_query, st.session_state.messages
            )

            if practice_mode:
                reply, feedback = run_practice_mode_turn(
                    user_query, st.session_state.case_file, len(st.session_state.messages)
                )
                full_reply = f"**[Counterparty Roleplay]:**\n\n{reply}\n\n---\n\n**[Legal Strategy Tip]:**\n\n{feedback}"
                st.markdown(full_reply)
                st.session_state.messages.append({"role": "assistant", "content": full_reply})
            else:
                legal_ans = generate_legal_reply(
                    user_query,
                    st.session_state.case_file,
                    st.session_state.retriever,
                    st.session_state.messages,
                )
                st.markdown(legal_ans.answer)
                if legal_ans.citations:
                    with st.expander("Statutory Citations & Verification", expanded=True):
                        for cit in legal_ans.citations:
                            st.markdown(f"- **{cit.act}** ({cit.section})")
                st.caption(f"Honesty Confidence: **{legal_ans.confidence.upper()}**")
                if legal_ans.needs_lawyer:
                    st.warning(
                        f"Advocate Escalation Required ({legal_ans.reason}). Call DLSA Helpline: 15100."
                    )

                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": legal_ans.answer,
                        "citations": [c.model_dump() for c in legal_ans.citations],
                        "confidence": legal_ans.confidence,
                        "needs_lawyer": legal_ans.needs_lawyer,
                    }
                )

                if st.button("Listen to Audio Response"):
                    audio_out = synthesize_speech(legal_ans.answer, "/tmp/lawyer_voice.mp3")
                    if audio_out and Path(audio_out).exists():
                        st.audio(audio_out)
