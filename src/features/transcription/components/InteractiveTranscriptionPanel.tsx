import * as React from 'react';
import { saveAs } from 'file-saver';
import { useTranscription } from "../hooks/useTranscription";
import { MediaPlayer } from '@/features/media/components/MediaPlayer';
import { Skeleton } from "@/components/ui/Skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Download } from "lucide-react";
import { TranscriptionSegment, MediaType, TranscriptionStatus } from '@/types';

interface InteractiveTranscriptionPanelProps {
  mediaId: string;
  mediaType: MediaType.AUDIO | MediaType.VIDEO;
}

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

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
        <div className="h-96 overflow-y-auto space-y-2 rounded-md border p-4 bg-muted/20">
          {transcription.result.segments.map((segment) => {
            const isActive = currentTime >= segment.start && currentTime < segment.end;
            return (
              <p
                key={segment.id}
                onClick={() => handleSegmentClick(segment)}
                className={`cursor-pointer rounded-md p-2 transition-colors ${isActive ? 'bg-primary/20' : 'hover:bg-accent'}`}>
                <span className="font-semibold text-primary/80">[{new Date(segment.start * 1000).toISOString().substr(14, 5)}]</span>{" "}
                {segment.text}
              </p>
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
          <Button variant="outline" size="icon" onClick={handleDownload} disabled={!canDownload}>
            <Download className="h-4 w-4" />
            <span className="sr-only">Download Transcription</span>
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {renderContent()}
      </CardContent>
    </Card>
  );
};
