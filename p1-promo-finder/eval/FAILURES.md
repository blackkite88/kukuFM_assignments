# P1 Failure Taxonomy & Real-Run Analysis

This document catalogs known failure modes in automated microdrama promo generation, their root causes, and evaluation guidelines.

## 1. Quiet Hook
- **Definition:** The opening 3 seconds contain low-energy dialogue or slow scene setup (e.g., footsteps, pleasant greetings) rather than an instant emotional arrest (slap, accusation, revelation).
- **Root Cause:** Event boundary parser starts on an ambient action event rather than the primary confrontation beat.
- **Real-Run Observation:** not measured (pending run on full 50-episode pack).
- **Mitigation:** Candidate generator rewards opening lines containing confrontation keywords and high question/exclamation density.

## 2. Resolved Ending
- **Definition:** The clip ends after tension is discharged (e.g., "The police have arrived and handcuffed him") rather than during peak suspense.
- **Root Cause:** Fixed 20-60s window boundaries landing past the climax of a scene.
- **Real-Run Observation:** not measured.
- **Mitigation:** Candidate heuristic penalizes closed declarative sentences and rewards interrupted actions (`--`, `...`, `?`).

## 3. Needs Earlier Context
- **Definition:** A high-drama scene makes no sense to a cold viewer because key character relationships or terms are opaque (e.g., "Why is Kabir holding a red envelope?").
- **Root Cause:** Scene-level emotional peak is detached from narrative setup.
- **Real-Run Observation:** not measured.
- **Mitigation:** Standalone score < 6 triggers `stitch.py` to prepend a 5-15s setup beat earlier in the episode.

## 4. Overlapping Duplicates
- **Definition:** Two promos in the top 10 cover the exact same scene with only a 3-5 second offset.
- **Root Cause:** Sliding window generates multiple valid cuts over the same dramatic peak.
- **Real-Run Observation:** not measured.
- **Mitigation:** IoU interval deduplication with a 35% overlap threshold and a strict cap of max 2 promos per episode in the top 10.

## 5. Timestamp Issues
- **Definition:** Negative duration, non-monotonic timestamps, or drift between spoken audio and screenplay event boundaries.
- **Root Cause:** Inconsistencies in screenplay formatting or OCR/export glitches in source documents.
- **Real-Run Observation:** not measured.
- **Mitigation:** `src/parse.py` enforces monotonicity checks and explicit line-level parsing error messages.
