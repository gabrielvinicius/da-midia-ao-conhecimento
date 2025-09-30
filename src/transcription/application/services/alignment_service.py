# src/transcription/application/services/alignment_service.py
from typing import List, Dict, Any
import structlog

logger = structlog.get_logger(__name__)

class AlignmentService:
    """Aligns speaker diarization results with transcription segments."""

    def align(self, transcription_result: Dict[str, Any], diarization_result: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Merges transcription segments with speaker labels from diarization.

        This is a complex task. The quality of the alignment depends heavily on the
        accuracy of the timestamps from both the transcription and diarization models.
        This implementation uses a straightforward approach of assigning a speaker to a
        transcription segment based on time overlap.
        """
        logger.info("alignment.service.started")

        transcription_segments = transcription_result.get("segments", [])
        if not transcription_segments:
            logger.warning("alignment.service.no_transcription_segments")
            return []

        aligned_segments = []
        for seg in transcription_segments:
            seg_start = seg.get('start')
            seg_end = seg.get('end')
            seg_text = seg.get('text', '').strip()

            if seg_start is None or seg_end is None or not seg_text:
                continue

            # Find the speaker with the most overlap with the current segment
            speaker_overlaps = {}
            for turn in diarization_result:
                turn_start = turn['start']
                turn_end = turn['end']
                speaker = turn['speaker']

                overlap = max(0, min(seg_end, turn_end) - max(seg_start, turn_start))
                if overlap > 0:
                    speaker_overlaps[speaker] = speaker_overlaps.get(speaker, 0) + overlap

            if not speaker_overlaps:
                # If no speaker overlap, assign a default or skip
                assigned_speaker = "UNKNOWN"
            else:
                # Assign the speaker with the maximum overlap
                assigned_speaker = max(speaker_overlaps, key=speaker_overlaps.get)

            aligned_segments.append({
                "start": seg_start,
                "end": seg_end,
                "text": seg_text,
                "speaker": assigned_speaker,
            })

        # Post-processing: Merge consecutive segments from the same speaker
        if not aligned_segments:
            return []

        merged_segments = []
        current_segment = aligned_segments[0].copy()

        for i in range(1, len(aligned_segments)):
            next_segment = aligned_segments[i]
            if current_segment["speaker"] == next_segment["speaker"]:
                # Merge text and update end time
                current_segment["text"] += " " + next_segment["text"]
                current_segment["end"] = next_segment["end"]
            else:
                # Speaker changed, save the current segment and start a new one
                merged_segments.append(current_segment)
                current_segment = next_segment.copy()
        
        # Add the last segment
        merged_segments.append(current_segment)

        logger.info("alignment.service.completed", total_segments=len(merged_segments))
        return merged_segments
