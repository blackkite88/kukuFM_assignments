# P2: AI Lawyer (India)

Grounded conversational legal assistant for ordinary citizens in India dealing with everyday civil disputes, backed by a strict statutory Honesty Layer, multi-lingual intake (Hindi, English, Hinglish), voice STT, negotiation practice mode, and automated document drafting.

## What It Does
- **Restricted Civil Scope:** Solves three high-frequency everyday civil issues:
  1. Tenancy security deposits not returned (Model Tenancy Act, 2021)
  2. Consumer refunds & defective goods (Consumer Protection Act, 2019 / e-Daakhil)
  3. Unpaid wages & arbitrary salary deductions (Payment of Wages Act, 1936 / Code on Wages, 2019)
- **Deterministic Honesty Layer:** Answers are generated **only** from retrieved government statutory chunks. Citations are verified via code-level set intersection. Any hallucinated citation is rejected, regenerated, or defaulted to the District Legal Services Authority (DLSA Helpline 15100).
- **Mandatory Escalation:** Out-of-scope issues (criminal law, police FIRs, assault, divorce, active court summons, or claims > ₹20 Lakhs) automatically set `needs_lawyer=True` and redirect to licensed advocates.
- **Multi-lingual Conversational Intake:** Automatically detects Hindi (Devanagari), Hinglish, or English, responds in the user's dialect, and builds a structured `CaseFile` asking max 1-2 clarifying questions per turn.
- **Negotiation Practice Mode:** AI assumes the persona of the counterparty (evasive landlord, difficult employer, or merchant) to let users practice asserting their rights, followed by coaching feedback.
- **Automated Document Drafting:** Generates formal demand notices and consumer complaints in `.docx` format with missing fact placeholders (`[MISSING: ...]`) and red draft warning banners.
- **Voice Support:** Speech-to-text transcription via Groq Whisper (`st.audio_input`) and optional speech synthesis (`gTTS`).

## Assumptions & Boundaries
- Tenancy laws are acknowledged as state subjects; Model Tenancy Act 2021 serves as a baseline framework.
- No PII is persisted beyond the active Streamlit session memory.
- The system is an educational assistance tool, NOT a licensed advocate.

## Setup & Quickstart

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env to add your GEMINI_API_KEY and GROQ_API_KEY (optional, for Whisper STT)

# 4. Run automated test suite
pytest

# 5. Run the 12 canonical test cases
python -m tests.run_cases

# 6. Compile documentation PDFs
python -m src.docs

# 7. Start Streamlit application
streamlit run app.py
```

## Environment Variables & Model Swap
Model selection is completely decoupled from code via the `MODEL` environment variable:
- Default: `MODEL=gemini/gemini-2.0-flash` (requires `GEMINI_API_KEY`)
- OpenAI: `MODEL=openai/gpt-4o-mini` (requires `OPENAI_API_KEY`)
- Anthropic: `MODEL=anthropic/claude-3-5-haiku` (requires `ANTHROPIC_API_KEY`)
- Voice STT: `GROQ_API_KEY` (optional, for Whisper voice input)

## Streamlit Community Cloud Deployment
1. Push to GitHub (`data/`, `.env`, and `logs/` are strictly gitignored).
2. Deploy on [Streamlit Community Cloud](https://share.streamlit.io).
3. Under App Settings -> Secrets, provide:
```toml
MODEL = "gemini/gemini-2.0-flash"
GEMINI_API_KEY = "your-api-key"
GROQ_API_KEY = "your-groq-key"
```

## Folder Map
```
p2-ai-lawyer/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── app.py
├── docs/
│   ├── solution.md
│   ├── solution.pdf
│   ├── walkthrough.md
│   ├── walkthrough.pdf
│   └── video_script.md
├── eval/
│   └── FAILURES.md
├── kb/
│   ├── consumer_protection_act_2019.json
│   ├── limitation_act_1963.json
│   ├── model_tenancy_act_2021.json
│   ├── payment_of_wages_act_1936.json
│   └── MISSING.md
├── logs/
│   └── .gitkeep
├── outputs/
│   ├── README.txt
│   ├── case_check_table.md
│   └── case_results.json
├── src/
│   ├── __init__.py
│   ├── audio.py
│   ├── docs.py
│   ├── draft.py
│   ├── flow.py
│   ├── llm.py
│   ├── retrieve.py
│   └── validator.py
└── tests/
    ├── __init__.py
    ├── cases.md
    ├── run_cases.py
    └── test_lawyer.py
```
