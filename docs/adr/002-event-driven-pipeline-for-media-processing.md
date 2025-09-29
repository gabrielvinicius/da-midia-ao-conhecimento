# 2. Event-Driven Pipeline for Media Processing

**Date**: 2024-08-01

**Status**: Accepted

## Context

Initially, the application was tightly coupled to the concept of "video" processing. The workflow was linear and rigid: upload video -> process video -> transcribe -> summarize. This created several limitations:

-   **Lack of Flexibility**: It was difficult to introduce new media types (e.g., audio, text/PDF) without significant changes to the existing video-centric modules.
-   **Tight Coupling**: Modules were directly calling each other or relying on specific data structures from upstream, making changes propagate across the system.
-   **Scalability Challenges**: Asynchronous processing was present, but the orchestration was still somewhat centralized, making it harder to scale individual processing steps independently.

## Decision

We decided to refactor the core processing workflow into a **generic, event-driven pipeline** based on the following principles:

1.  **Generic Media Abstraction**: Introduced a `Media` entity and `media_management` module as the unified entry point for all media types (VIDEO, AUDIO, TEXT).
2.  **Specialized Processors**: Created dedicated, single-responsibility modules (`video_processing`, `text_processing`, `transcription`) that listen for specific events and perform a single, well-defined task.
3.  **Event-Driven Communication**: Modules communicate exclusively through domain events published to an `EventBus` (Redis/Celery). A module publishes an event upon completing its task, and other modules subscribe to events relevant to their responsibilities.
4.  **Content-Centric Events**: Introduced generic events like `AudioExtracted` and `TextContentReady` to represent the output of processing steps, allowing downstream modules to consume content without knowing its origin.

**Example Flow:**
-   `POST /media` (upload video) -> `MediaUploaded(type=VIDEO)` event
-   `video_processing` module consumes `MediaUploaded(type=VIDEO)` -> extracts audio -> publishes `AudioExtracted` event
-   `transcription` module consumes `AudioExtracted` -> transcribes audio -> publishes `TextContentReady` event
-   `summarization` module consumes `TextContentReady` -> summarizes text -> completes pipeline

## Consequences

### Positive

-   **High Flexibility and Extensibility**: Easily add new media types (e.g., images) or new processing steps without modifying existing modules.
-   **Loose Coupling**: Modules are highly independent, communicating via abstract events. Changes in one module are less likely to affect others.
-   **Improved Scalability**: Individual processing steps (e.g., video processing, transcription) can be scaled independently based on demand.
-   **Clearer Responsibilities**: Each module and handler has a very specific and limited scope.

### Negative

-   **Increased Complexity in Orchestration**: The overall flow is harder to visualize initially due to asynchronous, event-driven nature.
-   **Debugging Challenges**: Following a single request through multiple asynchronous steps and events requires robust observability tools (like OpenTelemetry tracing).
-   **More Files/Boilerplate**: Introduces more event classes, handlers, and tasks.

Despite the increased initial complexity, the long-term benefits in flexibility, scalability, and maintainability for a media processing platform were deemed critical.
