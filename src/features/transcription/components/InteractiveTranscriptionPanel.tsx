import * as React from 'react';
import { saveAs } from 'file-saver';
import { useTranscription } from "../hooks/useTranscription";
import { MediaPlayer } from '@/features/media/components/MediaPlayer';
import { Skeleton } from "@/components/ui/Skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Download } from "lucide-react";
import { TranscriptionSegment, MediaType, TranscriptionStatus } from '@/types';
import { EditSpeakersDialog } from './EditSpeakersDialog'; // Import the new dialog

interface InteractiveTranscriptionPanelProps {
  mediaId: string;
  mediaType: MediaType.AUDIO | MediaType.VIDEO;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Helper to get a consistent color for each speaker
const speakerColors: { [key: string]: string } = {};
const colorPalette = [
  'text-sky-500', 'text-emerald-500', 'text-amber-500', 
  'text-indigo-500', 'text-rose-500', 'text-cyan-500'
];
let colorIndex = 0;

const getSpeakerColor = (speaker: string) => {
  if (!speakerColors[speaker]) {
    speakerColors[speaker] = colorPalette[colorIndex % colorPalette.length];
    colorIndex++;
  }
  return speakerColors[speaker];
};

export const InteractiveTranscriptionPanel = ({ mediaId, mediaType }: InteractiveTranscriptionPanelProps) => {
  const { data: transcription, isLoading, isError } = useTranscription(mediaId);
  const [currentTime, setCurrentTime] = React.useState(0);
  const playerRef = React.useRef<HTMLMediaElement>(null);

  const handleSegmentClick = (segment: TranscriptionSegment) => {
    if (playerRef.current) {
      playerRef.current.currentTime = segment.start;
      playerRef.current.play();
    }
  };

  const handleDownload = () => {
    if (transcription && transcription.result?.text) {
      const blob = new Blob([transcription.result.text], { type: "text/plain;charset=utf-8" });
      saveAs(blob, `transcription-${mediaId}.txt`);
    }
  };

  const canDownload = transcription?.status === TranscriptionStatus.COMPLETED && !!transcription.result?.text;
  const isDiarized = transcription?.result?.diarized === true;

  const renderContent = () => {
    if (isLoading) {
      return <Skeleton className="h-48 w-full" />;
    }
    if (isError || !transcription || !transcription.result) {
      return <p className="text-muted-foreground">Transcription not available.</p>;
    }

    return (
      <div className="space-y-4">
        <MediaPlayer
          src={`${API_URL}/media/${mediaId}/stream`}
          mediaType={mediaType}
          playerRef={playerRef}
          onTimeUpdate={setCurrentTime}
        />
        {!isDiarized && transcription.status === TranscriptionStatus.COMPLETED && (
          <div className="text-center text-sm text-muted-foreground p-2">Identifying speakers...</div>
        )}
        <div className="h-96 overflow-y-auto space-y-2 rounded-md border p-4 bg-muted/20">
          {transcription.result.segments.map((segment, index) => {
            const isActive = currentTime >= segment.start && currentTime < segment.end;
            const speakerId = segment.speaker || 'UNKNOWN';
            // Use the alias if it exists, otherwise fall back to the speaker ID
            const speakerLabel = transcription.speaker_aliases?.[speakerId] || speakerId;
            const speakerColor = isDiarized ? getSpeakerColor(speakerId) : 'text-foreground';

            return (
              <div
                key={index}
                onClick={() => handleSegmentClick(segment)}
                className={`cursor-pointer rounded-md p-2 transition-colors ${isActive ? 'bg-primary/20' : 'hover:bg-accent'}`}>
                {isDiarized ? (
                  <p><span className={`font-bold ${speakerColor}`}>{speakerLabel}:</span> {segment.text}</p>
                ) : (
                  <p>{segment.text}</p>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex justify-between items-center">
          <span>Interactive Transcription</span>
          <div className="flex items-center gap-2">
            {isDiarized && <EditSpeakersDialog transcription={transcription!} />}
            <Button variant="outline" size="icon" onClick={handleDownload} disabled={!canDownload}>
              <Download className="h-4 w-4" />
              <span className="sr-only">Download Transcription</span>
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {renderContent()}
      </CardContent>
    </Card>
  );
};
