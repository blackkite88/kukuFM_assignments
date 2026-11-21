# P1: Microdrama Promo Finder

Autonomous pipeline and interactive Streamlit application to discover, score, stitch, and rank high-converting 20-60s promos from microdrama screenplays.

## What It Does
- **Parses Screenplays:** Ingests screenplay text files, validating timestamps for monotonicity and structured event boundaries (scenes, actions, dialogues).
- **Candidate Generation:** Generates 20-60s candidate windows using drama heuristics (slap/reveal/threat keywords, punctuation density, speaker-change rates, unresolved endings).
- **Grounded LLM Scoring:** Evaluates candidate windows in batched calls per episode, rating the 0-3s hook, cliffhanger ending, and cold-audience standalone comprehension (1-10).
- **Context Stitching:** Automatically repairs low-standalone promos (<6/10) by prepending a 5-15s setup beat from earlier in the episode.
- **Deduplication & Ranking:** Applies temporal IoU deduplication (0.35 threshold), caps episode dominance (max 2 per episode in top 10), and weights scores (0.35 hook + 0.35 cliffhanger + 0.30 standalone).
- **Interactive UI:** Streamlit interface to filter promos, inspect screenplay segments, view distribution rationale, and download CSV/JSON outputs.

## Scope & Limitations
- **Scope:** Text-based screenplay analysis for microdrama episodes (1-2 minutes each).
- **Limitations:** Does not inspect raw video/audio tracks (visual cuts or music cues). Screenplay formatting must include timestamp markers.

## Assumptions
- Screenplays have timestamp annotations (`[HH:MM:SS]` or `MM:SS`).
- A viral promo window is strictly 20.0 to 60.0 seconds long.
- Cold audience comprehension can be improved by adding a short earlier context segment.
- The input pack is confidential and kept locally in `data/` (gitignored).

## Setup & Quickstart

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env
# Edit .env and supply GEMINI_API_KEY (or other LLM key)

# 4. Run automated tests
pytest

# 5. Compile documentation PDFs
python -m src.docs

# 6. Run CLI on local data
python -m src.run --input data/ --out outputs/

# 7. Launch Streamlit UI
streamlit run app.py
```

## Environment Variables & Model Swap
Model selection is completely decoupled from code via the `MODEL` environment variable:
- Default: `MODEL=gemini/gemini-2.0-flash` (requires `GEMINI_API_KEY`)
- OpenAI: `MODEL=openai/gpt-4o-mini` (requires `OPENAI_API_KEY`)
- Anthropic: `MODEL=anthropic/claude-3-5-haiku` (requires `ANTHROPIC_API_KEY`)

To swap models, update `.env` or export in your shell:
```bash
export MODEL="openai/gpt-4o-mini"
export OPENAI_API_KEY="your-key"
```

## Streamlit Community Cloud Deployment
1. Push this repository to GitHub (ensure `data/`, `.env`, and `logs/` are NOT committed; `.gitignore` is pre-configured).
2. Create a new app on [Streamlit Community Cloud](https://share.streamlit.io).
3. Under App Settings -> Secrets, add your API keys:
```toml
MODEL = "gemini/gemini-2.0-flash"
GEMINI_API_KEY = "your-api-key"
```
4. Screenplay files can be uploaded directly via the sidebar file uploader.

## Folder Map
```
p1-promo-finder/
├── .env.example
├── .gitignore
├── README.md
├── requirements.txt
├── app.py
├── data/
│   └── README.txt
├── docs/
│   ├── PROBLEM.md
│   ├── solution.md
│   ├── solution.pdf
│   ├── walkthrough.md
│   ├── walkthrough.pdf
│   └── video_script.md
├── eval/
│   ├── FAILURES.md
│   ├── eval_agreement.py
│   └── manual_review.csv
├── logs/
│   └── .gitkeep
├── outputs/
│   └── README.txt
├── src/
│   ├── __init__.py
│   ├── candidates.py
│   ├── docs.py
│   ├── export.py
│   ├── llm.py
│   ├── parse.py
│   ├── rank.py
│   ├── run.py
│   ├── score.py
│   └── stitch.py
└── tests/
    ├── __init__.py
    ├── fixtures/
    │   ├── ep01.txt
    │   ├── ep02.txt
    │   └── ep03.txt
    └── test_pipeline.py
```
