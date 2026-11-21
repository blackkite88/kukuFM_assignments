"""Streamlit application for microdrama promo discovery and evaluation."""

import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.candidates import generate_candidates
from src.export import export_results
from src.parse import parse_screenplay_file, parse_screenplay_text
from src.rank import rank_promos
from src.score import score_candidates
from src.stitch import stitch_window

load_dotenv()

st.set_page_config(page_title="P1: Microdrama Promo Finder", layout="wide")
st.title("Microdrama Promo Finder")
st.write(
    "Automated discovery of high-converting 20-60s promos from microdrama screenplays. "
    "Scores opening 3-second hooks, unresolved cliffhangers, and standalone coherence."
)

active_model = os.getenv("MODEL", "gemini/gemini-2.0-flash")
st.sidebar.header("Configuration")
st.sidebar.text(f"Model: {active_model}")

has_api_key = bool(
    os.getenv("GEMINI_API_KEY")
    or os.getenv("OPENAI_API_KEY")
    or os.getenv("ANTHROPIC_API_KEY")
    or os.getenv("GROQ_API_KEY")
)
if not has_api_key:
    st.sidebar.warning(
        "No API key detected in environment (.env). Pipeline will run in heuristic fallback mode."
    )

input_source = st.sidebar.radio("Data Source", ["Use local data/", "Upload Files"])
uploaded_files = []
if input_source == "Upload Files":
    uploaded_files = st.sidebar.file_uploader(
        "Upload screenplay text files",
        type=["txt", "md", "screenplay"],
        accept_multiple_files=True,
    )

run_button = st.sidebar.button("Run Promo Finder")

out_dir = Path("outputs")
json_path = out_dir / "promos.json"
csv_path = out_dir / "promos.csv"
rationale_path = out_dir / "top10_rationale.md"

if run_button:
    with st.spinner("Parsing screenplays, scoring candidates with LLM, and ranking promos..."):
        all_stitched = []
        recent_summaries = []

        if input_source == "Upload Files":
            if not uploaded_files:
                st.error("Please upload at least one screenplay file.")
                st.stop()
            ep_idx = 1
            for up in sorted(uploaded_files, key=lambda x: x.name):
                content = up.read().decode("utf-8")
                events = parse_screenplay_text(content, ep=ep_idx, filename=up.name)
                if not events:
                    continue
                cands = generate_candidates(events, top_n=15)
                scores = score_candidates(ep_idx, cands, recent_summaries)
                for c, sc in zip(cands, scores):
                    all_stitched.append(stitch_window(c, sc, events))
                recent_summaries.append(f"Ep {ep_idx}: Screenplay uploaded from {up.name}")
                if len(recent_summaries) > 2:
                    recent_summaries.pop(0)
                ep_idx += 1
        else:
            data_dir = Path("data")
            files = sorted(
                [
                    p
                    for p in data_dir.glob("*")
                    if p.is_file()
                    and p.name != "README.txt"
                    and not p.name.startswith(".")
                    and p.suffix.lower() in (".txt", ".md", ".screenplay")
                ]
            )
            if not files:
                st.error("No screenplay files found in data/. Drop files or use Upload Files.")
                st.stop()

            for fpath in files:
                events = parse_screenplay_file(fpath)
                if not events:
                    continue
                ep = events[0].ep
                cands = generate_candidates(events, top_n=15)
                scores = score_candidates(ep, cands, recent_summaries)
                for c, sc in zip(cands, scores):
                    all_stitched.append(stitch_window(c, sc, events))
                recent_summaries.append(f"Ep {ep}: Episode {fpath.name}")
                if len(recent_summaries) > 2:
                    recent_summaries.pop(0)

        if not all_stitched:
            st.error("No valid 20-60s candidate windows could be extracted.")
            st.stop()

        ranked, rationale = rank_promos(all_stitched)
        export_results(ranked, rationale, out_dir)
        st.success(f"Pipeline completed! Discovered and ranked {len(ranked)} candidate promos.")

if json_path.exists() and csv_path.exists():
    with open(json_path, "r", encoding="utf-8") as f:
        promos_data = json.load(f)

    df = pd.read_csv(csv_path)

    col1, col2 = st.columns([1, 1])
    with col1:
        ep_options = ["All"] + sorted(list(set(df["ep"].astype(str))))
        selected_ep = st.selectbox("Filter by Episode", ep_options)
    with col2:
        min_score = st.slider("Minimum Composite Score", 1.0, 10.0, 5.0, 0.5)

    filtered_df = df[df["total_score"] >= min_score]
    if selected_ep != "All":
        filtered_df = filtered_df[filtered_df["ep"].astype(str) == selected_ep]

    st.subheader(f"Ranked Promos ({len(filtered_df)} matched)")
    st.dataframe(
        filtered_df[
            [
                "rank",
                "promo_id",
                "ep",
                "duration_s",
                "hook_score",
                "cliffhanger_score",
                "standalone_score",
                "total_score",
                "why",
            ]
        ],
        use_container_width=True,
    )

    promo_options = filtered_df["promo_id"].tolist()
    if promo_options:
        st.subheader("Promo Detailed Breakdown")
        sel_promo_id = st.selectbox("Select Promo to Inspect", promo_options)
        selected_record = next(p for p in promos_data if p["promo_id"] == sel_promo_id)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Composite Score", f"{selected_record['total_score']:.2f}")
        m2.metric("Hook (0-3s)", f"{selected_record['hook_score']:.1f}/10")
        m3.metric("Cliffhanger", f"{selected_record['cliffhanger_score']:.1f}/10")
        m4.metric("Standalone", f"{selected_record['standalone_score']:.1f}/10")

        st.markdown(f"**Editorial Rationale:** {selected_record['why']}")
        st.markdown(f"**Hook Line (First 3s):** `{selected_record['hook_text']}`")
        st.markdown(f"**Cliffhanger Moment:** `{selected_record['cliffhanger_text']}`")

        st.write("### Segments Timeline")
        for seg in selected_record["segments"]:
            st.info(
                f"Episode {seg['ep']}: {seg['start_s']:.1f}s to {seg['end_s']:.1f}s "
                f"(Duration: {seg['end_s'] - seg['start_s']:.1f}s)"
            )

    if rationale_path.exists():
        with st.expander("Top 10 Editorial Rationale & Distribution Strategy", expanded=False):
            with open(rationale_path, "r", encoding="utf-8") as f:
                st.markdown(f.read())

    st.subheader("Export Outputs")
    d1, d2 = st.columns(2)
    with d1:
        with open(csv_path, "r", encoding="utf-8") as f:
            st.download_button(
                "Download promos.csv",
                f.read(),
                file_name="promos.csv",
                mime="text/csv",
            )
    with d2:
        with open(json_path, "r", encoding="utf-8") as f:
            st.download_button(
                "Download promos.json",
                f.read(),
                file_name="promos.json",
                mime="application/json",
            )
else:
    st.info(
        "No outputs generated yet. Add screenplay files to data/ or upload files above, "
        "then click 'Run Promo Finder'."
    )
