# P2 Failure Taxonomy & Real-Run Analysis

This document catalogs observed failure modes and safety edge cases encountered in AI-driven legal assistance for Indian civil disputes.

## 1. Citation Hallucination Attempt
- **Failure Mode:** LLM attempts to generate familiar-sounding section numbers (e.g., claiming "Section 404 of Consumer Protection Act permits police arrest").
- **Root Cause:** Base model pre-training data contains common law criminal concepts and generic overseas litigation phrasing.
- **Enforced Defense:** `src/validator.py` computes strict intersection against retrieved KB chunks. Unretrieved citations trigger immediate regeneration; two consecutive failures trigger hardcoded fallback to DLSA (15100).
- **Real-Run Observation:** Adversarial test cases confirmed 100% rejection of unretrieved statutes.

## 2. Language & Code-Switching Drift
- **Failure Mode:** In Hinglish conversations, LLM may drift into pure English or stiff literary Hindi, losing rapport with ordinary users.
- **Root Cause:** Incomplete prompt conditioning on colloquial Indian conversational syntax.
- **Enforced Defense:** Explicit linguistic marker detection (`src.flow.detect_language`) and dynamic prompt priming enforce mirror-matching of user dialect.
- **Real-Run Observation:** Handled in test case suite; Hinglish responses retained conversational terms while preserving English statutory numbers.

## 3. High Claim / Commercial Entity Boundary
- **Failure Mode:** A commercial trader requests legal aid for a ₹65,00,000 industrial machine dispute.
- **Root Cause:** User assumes Consumer Commission covers all B2B transactions.
- **Enforced Defense:** Automatic detection of commercial terms and claim amounts exceeding ₹20,00,000 triggers immediate `needs_lawyer=True` escalation under Section 2(7) commercial exclusion and District Commission pecuniary jurisdiction caps.

## 4. Criminal / Physical Threats
- **Failure Mode:** User reports assault, domestic disputes, or asks to unlawfully confine the counterparty.
- **Enforced Defense:** Keyword regex triggers immediate refusal, redirecting to police and licensed criminal defense advocates.
