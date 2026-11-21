"""Streamlit dashboard for screenplay cliffhanger auditing and retention analysis."""

import json
import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from src.audit import audit_episode
from src.export import export_audit_results
from src.features import extract_ending_features
from src.parse import (
    extract_episode_slice,
    parse_screenplay_file,
    parse_screenplay_text,
)

load_dotenv()

st.set_page_config(page_title="P3: Cliffhanger Audit", layout="wide")
st.title("Microdrama Cliffhanger Audit")
st.write(
    "Pre-production script doctor for 1-2 minute microdrama screenplays. "
    "Audits the final 25s of each episode and verifies whether the next episode's first 15s pays it off."
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
    st.sidebar.warning("No API key detected in .env. Running in heuristic fallback mode.")

input_source = st.sidebar.radio("Data Source", ["Use local data/", "Upload Files"])
uploaded_files = []
if input_source == "Upload Files":
    uploaded_files = st.sidebar.file_uploader(
        "Upload screenplay files (e.g. ep01.txt..)",
        type=["txt", "md", "screenplay"],
        accept_multiple_files=True,
    )

run_button = st.sidebar.button("Run Cliffhanger Audit")

out_dir = Path("outputs")
csv_path = out_dir / "audit.csv"
json_path = out_dir / "audit.json"
rewrites_path = out_dir / "weakest_rewrites.md"

if run_button:
    with st.spinner("Extracting final 25s beats, running LLM audit, and verifying continuity..."):
        slices = []
        if input_source == "Upload Files":
            if not uploaded_files:
                st.error("Please upload at least one screenplay file.")
                st.stop()
            ep_idx = 1
            for up in sorted(uploaded_files, key=lambda x: x.name):
                content = up.read().decode("utf-8")
                events = parse_screenplay_text(content, ep=ep_idx, filename=up.name)
                if events:
                    slices.append(extract_episode_slice(events))
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
                st.error("No screenplay files found in data/. Drop pack files or use Upload Files.")
                st.stop()

            for fpath in files:
                events = parse_screenplay_file(fpath)
                if events:
                    slices.append(extract_episode_slice(events))

        if not slices:
            st.error("No valid screenplay episodes could be parsed.")
            st.stop()

        features_list = []
        audits = []
        for idx, curr_slice in enumerate(slices):
            feats = extract_ending_features(curr_slice.ep, curr_slice.ending_events)
            features_list.append(feats)
            next_slice = slices[idx + 1] if idx + 1 < len(slices) else None
            aud = audit_episode(curr_slice, feats, next_slice)
            audits.append(aud)

        export_audit_results(audits, slices, features_list, out_dir)
        st.success(f"Audit completed! Evaluated {len(audits)} episodes.")

if csv_path.exists() and json_path.exists():
    df = pd.read_csv(csv_path)
    with open(json_path, "r", encoding="utf-8") as f:
        audits_data = json.load(f)

    strong_n = len(df[df["verdict"] == "strong"])
    ok_n = len(df[df["verdict"] == "ok"])
    weak_n = len(df[df["verdict"] == "weak"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Episodes Audited", len(df))
    c2.metric("Strong Endings", strong_n)
    c3.metric("OK Endings", ok_n)
    c4.metric("Weak Endings (Rewrite)", weak_n)

    st.subheader("Ending Strength by Episode")
    color_map = {"strong": "#2ca02c", "ok": "#ff7f0e", "weak": "#d62728"}
    bar_colors = [color_map.get(v, "#1f77b4") for v in df["verdict"]]

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=df["episode"],
            y=df["total_strength"],
            marker_color=bar_colors,
            name="Total Strength (Stakes + Surprise)",
            hovertemplate="Episode %{x}<br>Strength: %{y}<br>Verdict: %{text}<extra></extra>",
            text=df["verdict"].str.upper(),
        )
    )
    fig.add_shape(
        type="line",
        x0=df["episode"].min() - 0.5,
        x1=df["episode"].max() + 0.5,
        y0=14.0,
        y1=14.0,
        line=dict(color="green", width=1.5, dash="dash"),
    )
    fig.add_shape(
        type="line",
        x0=df["episode"].min() - 0.5,
        x1=df["episode"].max() + 0.5,
        y0=10.0,
        y1=10.0,
        line=dict(color="red", width=1.5, dash="dash"),
    )
    fig.update_layout(
        xaxis_title="Episode Number",
        yaxis_title="Cliffhanger Score (out of 20)",
        margin=dict(l=20, r=20, t=30, b=20),
        height=320,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Audited Episodes Roster")

    def highlight_verdict(val):
        if val == "strong":
            return "background-color: #d4edda; color: #155724; font-weight: bold;"
        elif val == "ok":
            return "background-color: #fff3cd; color: #856404;"
        elif val == "weak":
            return "background-color: #f8d7da; color: #721c24; font-weight: bold;"
        return ""

    styled_df = df.style.map(highlight_verdict, subset=["verdict"])
    st.dataframe(styled_df, use_container_width=True)

    st.subheader("Per-Episode Diagnostic Drill-Down")
    sel_ep = st.selectbox("Select Episode to Inspect", df["episode"].tolist())
    ep_record = next(a for a in audits_data if a["episode"] == sel_ep)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Verdict", ep_record["verdict"].upper())
    m2.metric("Cliffhanger Type", ep_record["cliffhanger_type"].title())
    m3.metric("Stakes", f"{ep_record['stakes']:.1f}/10")
    m4.metric("Surprise / Twist", f"{ep_record['surprise']:.1f}/10")

    st.markdown(f"**Burning Unresolved Question:** `{ep_record['unresolved_question']}`")
    st.markdown(f"**Actionable Script Fix:** `{ep_record['one_line_fix']}`")
    st.markdown(
        f"**Next Episode Continuity:** "
        f"{'Pays off in first 15s' if ep_record['next_ep_payoff'] else 'Missing immediate payoff in next episode opening.'}"
    )

    if rewrites_path.exists():
        with st.expander("Top 5 Weakest Endings & Suggested 3-Line Rewrites", expanded=False):
            with open(rewrites_path, "r", encoding="utf-8") as f:
                st.markdown(f.read())

    st.subheader("Export Audit Reports")
    d1, d2 = st.columns(2)
    with d1:
        with open(csv_path, "r", encoding="utf-8") as f:
            st.download_button(
                "Download audit.csv",
                f.read(),
                file_name="audit.csv",
                mime="text/csv",
            )
    with d2:
        with open(json_path, "r", encoding="utf-8") as f:
            st.download_button(
                "Download audit.json",
                f.read(),
                file_name="audit.json",
                mime="application/json",
            )
else:
    st.info("No audit reports found. Add screenplay files to data/ or upload files above, then click 'Run Cliffhanger Audit'.")
