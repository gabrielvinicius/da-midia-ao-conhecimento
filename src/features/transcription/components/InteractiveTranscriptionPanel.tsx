import * as React from 'react';
import { useTranscription } from "../hooks/useTranscription";
import { MediaPlayer } from '@/features/media/components/MediaPlayer';
import { Skeleton } from "@/components/ui/Skeleton";
import { TranscriptionSegment, MediaType } from '@/types';

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
        <div className="h-96 overflow-y-auto space-y-2 rounded-md border p-4">
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

  return <div>{renderContent()}</div>;
};
