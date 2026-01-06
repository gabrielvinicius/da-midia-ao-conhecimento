# Architecture Deep Dive (Level 6.0 - January 2026)

This document provides a technical overview of the Video Summarizer platform, now operating at **Maturity Level 6.0 (Autonomous & Adaptive)**.

## 1. Core Principles

### 1.1 Pure Dependency Injection (Composition Root)
The system rejects global singletons and "magic" frameworks. All dependencies are composed manually at the application entry point (`main.py`).
- **Bootstrap Pattern:** Each module has a `bootstrap.py` file that contains a `build_module_components` factory.
- **Explicit Binding:** The `main.py` orchestrates these factories, passing shared resources (Database, Event Bus, Storage Factory) and registering them with FastAPI's `dependency_overrides`.

### 1.2 Modular Monolith & DDD
The codebase is strictly divided into Bounded Contexts.
- **media_management:** Owner of the Media aggregate and state machine.
- **user_management:** Security, Auth, and RBAC.
- **media_processing:** Worker-focused domain for Whisper/FFmpeg.
- **text_analysis:** NLP pipeline (Summarization, Topics, Sentiment).
- **storage:** Abstracted persistence layer.
- **notifications:** Real-time feedback loop.

### 1.3 Hexagonal Architecture (Ports & Adapters)
Dependencies always point inward. The application layer defines **Ports** (Protocols), and the infrastructure layer provides **Adapters**. For example, the `Admin` module interacts with `Media` through a `MediaAdminPort`, ensuring that changes in Media internal implementation never break the Admin interface.

## 2. Level 6.0 Intelligence Components

### 2.1 Hardware Advisor & Intelligent Orchestration
Located in `src/shared/infrastructure/monitoring/hardware_advisor.py`, this component makes the system "hardware-conscious".
- **Real-time Monitoring:** Tracks VRAM usage and CPU pressure.
- **Dynamic Failover:** If the GPU is saturated, the system automatically redirects tasks to fallback providers or simpler models (e.g., swapping Llama 3 for a heuristic summary) to maintain availability.
- **Circuit Breaker:** Automatically "quarantines" AI providers that fail consecutively, preventing system-wide degradation.

### 2.2 Granular Analysis Pipeline
The `text_analysis` service has been refactored from a monolithic function into a **Granular Pipeline** (`src/text_analysis/application/pipeline`).
- **Step Isolation:** Each stage (Chunking, Sentiment, Topics, Summary) is an independent object.
- **Partial Persistence:** Results are saved to the database after each successful stage. If the final LLM summarization fails, the user still receives sentiment and topic data.
- **Self-Healing Retries:** If a pipeline fails due to context limits, the system adapts (e.g., reduces chunk size) and auto-retries the task.

### 2.3 Predictive Observability
The `ResourcePredictor` (`src/shared/infrastructure/monitoring/resource_predictor.py`) quantifies the "cost" of a task before execution.
- **Cost Estimation:** Predicts VRAM needs and duration based on media length.
- **Proactive Mitigation:** If a task is predicted to cause an OOM (Out Of Memory) error, the system proactively adjusts parameters (e.g., forces high-compression quantization) before starting.

## 3. Persistent Data & Evolution

### 3.1 Zero-Downtime Schema Evolution
We use a "Schema-on-Read" strategy for complex payloads.
- **Versioning:** Payloads include a `schema_version`.
- **Upcasters:** The `SqlAlchemyAnalysisRepository` contains logic to transform legacy JSON structures into the current domain model at runtime. This allows seamless updates without blocking the database for migrations.

## 4. Frontend Intelligence (Adaptive UI)

The frontend is a fully reactive observer of the system's state.
- **Adaptive UI:** The `SystemHealthBanner` informs users of server load, adjusting the interface behavior based on the `HardwareAdvisor` reports.
- **Predictive Pre-fetching:** Hovering over items triggers background data loading, making navigation feel instantaneous.
- **Accessible Design:** Full WCAG compliance with keyboard-navigable interactive transcriptions and ARIA-compliant status reporting.

---
This architecture ensures that the Video Summarizer is not just a tool, but a resilient, self-governing media intelligence platform. 💎🚀
