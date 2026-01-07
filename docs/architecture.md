# Architecture Deep Dive (Level 7.0 Precursor - January 2026)

This document provides a technical overview of the Video Summarizer platform, now operating at **Maturity Level 7.0 Precursor (Sovereign Knowledge Base)**.

## 1. Core Principles

### 1.1 Pure Dependency Injection (Composition Root)
Dependencies are composed manually at the entry point (`main.py`) via `bootstrap.py` factories, ensuring absolute decoupling and testability.

### 1.2 Modular Monolith & DDD
Strict Bounded Contexts ensure that modules can evolve independently. The system is ready to be split into microservices at any time.

### 1.3 Hexagonal Architecture (Ports & Adapters)
Infrastructure is a detail. The core business logic interacts with external systems (DB, S3, LLMs) through stable, typed Interfaces (Ports).

## 2. Intelligence & Autonomy (Level 6.0 & 7.0)

### 2.1 Multimodal Video Insight (Level 7.0)
The system integrates **Moondream 2** within the analysis pipeline.
- **Visual Description**: Extracts keyframes via FFmpeg and generates textual descriptions of visual events.
- **Cognitive Link**: These descriptions complement the transcript, providing the LLM (Llama 3) with a full audio-visual context for summarization.

### 2.2 Global Semantic Knowledge Base (Level 7.0)
Powered by **pgvector**, the system transforms processed media into a searchable vector space.
- **Knowledge Indexing**: Every text chunk and its visual context are vectorized and stored.
- **Semantic Search**: Natural language queries find relevant content across the entire library based on semantic similarity (Cosine Distance).

### 2.3 Human-in-the-loop Feedback (Level 7.0)
The system learns from its users.
- **Correction Loop**: Users can rate and edit AI-generated summaries.
- **Dataset Generation**: Original AI outputs and human corrections are stored side-by-side, creating a ground-truth dataset for future fine-tuning.

### 2.4 Hardware-Aware Self-Healing (Level 6.0)
The `HardwareAdvisor` and `ResourcePredictor` manage system health.
- **Predictive Mitigation**: Adjusts chunking and model strategies pro-actively to prevent OOM errors.
- **Active Redundancy**: Automatically falls back to lighter models or heuristic summaries if GPU resources are exhausted.

## 3. Persistent Data & Evolution

### 3.1 Zero-Downtime Schema Evolution
Uses a "Schema-on-Read" strategy with JSONB upcasters, allowing for non-breaking database updates.

## 4. Frontend Intelligence (Adaptive UI)

- **Adaptive UI**: The `SystemHealthBanner` reflects real-time server load.
- **Predictive Pre-fetching**: Anticipates user navigation via hover-triggers.
- **Explainable UI**: The `ProcessingTrace` provides full transparency on hardware and AI strategy usage.

---
The Video Summarizer is a resilient, self-governing media intelligence platform designed for the next generation of knowledge management. 💎🚀

