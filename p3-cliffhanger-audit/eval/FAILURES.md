# P3 Failure Taxonomy & Real-Run Analysis

This document catalogs observed failure modes in script-stage cliffhanger evaluation, root causes, and corrective defenses.

## 1. False Positive Scene Resolution
- **Definition:** The model marks an ending as `weak` believing the scene was settled, when in fact an ironical or subtextual menace was present.
- **Root Cause:** Surface lexical matching flags phrases like "he smiled and said goodbye" without registering the character was holding a concealed weapon.
- **Defense:** `src/features.py` pairs action events and object detection (gun, blood, letter) alongside dialogue sentiment.

## 2. Premature Payoff in Next Episode
- **Definition:** Episode N ends on high suspense (e.g. gun aimed at character), but Episode N+1 jumps to an unrelated B-plot scene or flashback.
- **Root Cause:** Script writers resetting scene energy to delay the confrontation.
- **Defense:** `audit.py` cross-checks the first 15 seconds of Episode N+1 against Episode N's ending. If `next_ep_payoff` is False, the script doctor flags a continuity violation.

## 3. Passive Dialogue Drift
- **Definition:** An episode ending consists of two characters talking about events that happened offscreen rather than active conflict on-screen.
- **Root Cause:** Exposition-heavy writing in mid-season transition episodes.
- **Defense:** `stakes` scoring strictly penalizes passive verbal exposition and rewards physical choices and irreversible decisions.

## 4. Abrupt Arbitrary Cuts
- **Definition:** The episode cuts mid-word or mid-sentence without creating a cognitive question, causing viewer annoyance rather than suspense.
- **Defense:** Parser validates event boundaries and feature extractor checks whether the ending landed on a dramatic beat rather than an accidental time cut.
