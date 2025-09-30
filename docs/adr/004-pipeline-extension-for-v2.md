# 4. Pipeline Extension for v2 Features (Diarization and Sentiment Analysis)

**Date**: 2024-08-01

**Status**: Proposed

## Context

The v1 architecture establishes a stable, linear pipeline for media processing: `Media -> Audio -> Text -> Summary`. To enhance the platform's capabilities, advanced features such as speaker diarization ("who spoke when") and sentiment analysis are required. Implementing these features naively would break the simplicity and decoupled nature of the v1 pipeline.

Diarization, in particular, must run in parallel with transcription, and their results must be aggregated and aligned before further processing can occur. This introduces the need for a more complex, graph-based workflow rather than a simple linear chain.

## Decision

We will extend the event-driven architecture to support parallel processing and result aggregation. The v2 pipeline will be implemented as follows:

1.  **Parallel Fan-Out**: The `AudioExtracted` event (or `MediaUploaded(type=AUDIO)`) will be consumed by two separate handlers in parallel:
    -   `Transcription Event Handler`: Triggers the transcription task.
    -   `Diarization Event Handler`: Triggers the diarization task.

2.  **Intermediate Event Publication**: Each parallel task will publish a distinct event upon completion:
    -   The transcription task will publish `TranscriptionWithTimestampsReady`, containing the full structured transcription result (including word-level timestamps).
    -   The diarization task will publish `DiarizationCompleted`, containing the list of speaker turns and their timestamps.

3.  **Stateful Aggregation**: A new, stateful component, the `AlignDiarizationCommandHandler`, will be introduced in the `transcription` module. Its responsibility is to aggregate the results:
    -   It will subscribe to both `TranscriptionWithTimestampsReady` and `DiarizationCompleted`.
    -   Upon receiving the first event for a given `media_id`, it will store the partial result (e.g., in a new `JSON` column on the `Media` entity or in a dedicated cache like Redis).
    -   Upon receiving the second event for the same `media_id`, it will fetch the previously stored partial result, execute the alignment logic to combine the transcription text with speaker labels, and produce a final, enriched text.

4.  **Final Event Publication**: After successful alignment, the `AlignDiarizationCommandHandler` will publish a new, generic event: `FullTextReadyForAnalysis`. This event will contain the final, enriched text content.

5.  **Downstream Consumers**: The `summarization` and the new `sentiment_analysis` modules will be refactored to be consumers of the `FullTextReadyForAnalysis` event. This keeps them decoupled from the complexities of transcription and diarization.

## Consequences

### Positive

-   **Extensibility**: This pattern allows for the addition of more parallel processing steps in the future (e.g., object detection in video) without altering the core pipeline logic.
-   **Separation of Concerns**: The complex aggregation logic is isolated within a single, dedicated handler (`AlignDiarizationCommandHandler`).
-   **Efficiency**: Transcription and diarization can run in parallel, potentially reducing the total processing time.

### Negative

-   **Increased State Management**: The system must now manage the state of incomplete, parallel tasks. This adds complexity to the persistence layer (new columns or tables) and to the logic of the aggregator.
-   **Increased Debugging Complexity**: Tracing a single request across parallel, asynchronous branches requires robust observability tools.

This design provides a clear and scalable path forward for implementing advanced v2 features while building upon the solid, event-driven foundation of the v1 architecture.
