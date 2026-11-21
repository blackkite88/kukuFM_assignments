# P3: Microdrama Cliffhanger Audit

Pre-production automated script doctor and interactive Streamlit application to audit episode endings, verify next-episode continuity payoffs, and generate high-retention 3-line rewrites for microdrama screenplays.

## What It Does
- **Targeted Slice Extraction:** Automatically extracts the final 25 seconds of each episode (the decisive cliffhanger window) and the first 15 seconds of the subsequent episode.
- **Structural Feature Extraction:** Evaluates suspense keywords (`who`, `why`, `kill`, `secret`, `gun`, `heir`), mid-action interrupts (`...`, `--`), speaker transitions, and scene resolution flags.
- **Multi-Factor LLM Audit:** Rates stakes (1-10) and surprise/twist factor (1-10), classifies cliffhanger type (`reveal`, `threat`, `betrayal`, `decision`, `question`, `none`), and issues an overall verdict (`strong`, `ok`, `weak`).
- **Next-Episode Continuity Check:** Explicitly verifies whether Episode N+1's opening 15 seconds immediately addresses Episode N's cliffhanger, preventing unearned narrative resets.
- **Actionable 3-Line Rewrites:** Automatically identifies the 5 weakest endings across the season and drafts high-stakes 3-line rewrites marked `[SUGGESTION]`.
- **Interactive UI:** Streamlit interface with seasonal Plotly strength charts, color-coded rosters, per-episode diagnostic drill-downs, and CSV/JSON downloads.

## Scope & Limitations
- **Scope:** Pre-production text-based screenplay analysis for microdrama seasons (typically 50-80 episodes of 1-2 minutes each).
- **Limitations:** Focuses on screenplay text; does not evaluate actor facial performances or audio sound mix.

## Assumptions
- Screenplay files contain timestamp annotations (`[HH:MM:SS]` or `MM:SS`).
- The final 25 seconds determine retention and next-episode unlock rates.
- The confidential screenplay pack is stored locally in `data/` (gitignored).

## Setup & Quickstart

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env and supply your GEMINI_API_KEY (or other LLM key)

# 4. Run automated test suite
pytest

# 5. Compile documentation PDFs
python -m src.docs

# 6. Run CLI audit pipeline
python -m src.run --input data/ --out outputs/

# 7. Start Streamlit dashboard
streamlit run app.py
```

## Environment Variables & Model Swap
Model selection is completely decoupled from code via the `MODEL` environment variable:
- Default: `MODEL=gemini/gemini-2.0-flash` (requires `GEMINI_API_KEY`)
- OpenAI: `MODEL=openai/gpt-4o-mini` (requires `OPENAI_API_KEY`)
- Anthropic: `MODEL=anthropic/claude-3-5-haiku` (requires `ANTHROPIC_API_KEY`)

To swap models, update `.env` or export in your shell:
```bash
export MODEL="openai/gpt-4o"
export OPENAI_API_KEY="your-key"
```

## Streamlit Community Cloud Deployment
1. Push to GitHub (`data/`, `.env`, and `logs/` are strictly gitignored).
2. Create a new app on [Streamlit Community Cloud](https://share.streamlit.io).
3. Under App Settings -> Secrets, provide your API keys:
```toml
MODEL = "gemini/gemini-2.0-flash"
GEMINI_API_KEY = "your-api-key"
```
4. Screenplay files can be uploaded directly via the sidebar file uploader.

## Folder Map
```
p3-cliffhanger-audit/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── app.py
├── data/
│   └── README.txt
├── docs/
│   ├── METRICS.md
│   ├── PROBLEM.md
│   ├── solution.md
│   ├── solution.pdf
│   ├── walkthrough.md
│   ├── walkthrough.pdf
│   └── video_script.md
├── eval/
│   ├── FAILURES.md
│   ├── eval_agreement.py
│   └── manual_labels.csv
├── logs/
│   └── .gitkeep
├── outputs/
│   └── README.txt
├── src/
│   ├── __init__.py
│   ├── audit.py
│   ├── docs.py
│   ├── export.py
│   ├── features.py
│   ├── llm.py
│   ├── parse.py
│   └── run.py
└── tests/
    ├── __init__.py
    ├── fixtures/
    │   ├── ep01.txt
    │   ├── ep02.txt
    │   └── ep03.txt
    └── test_audit.py
```
