import * as React from 'react';
import { saveAs } from 'file-saver';
import { useTranscription } from "../hooks/useTranscription";
import { Skeleton } from "@/components/ui/Skeleton";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Download } from "lucide-react";
import { TranscriptionSegment, TranscriptionStatus } from '@/types';
import { EditSpeakersDialog } from './EditSpeakersDialog';
import { cn } from "@/lib/utils";

interface InteractiveTranscriptionPanelProps {
  mediaId: string;
  currentTime: number;
  onSeek?: (time: number) => void;
}

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

export const InteractiveTranscriptionPanel = ({ mediaId, currentTime, onSeek }: InteractiveTranscriptionPanelProps) => {
  const { data: transcription, isLoading, isError } = useTranscription(mediaId);

  const handleSegmentClick = (segment: TranscriptionSegment) => {
    if (onSeek) {
      onSeek(segment.start);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent, segment: TranscriptionSegment) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleSegmentClick(segment);
    }
  };

  const activeSegmentRef = React.useRef<HTMLDivElement>(null);

  // Auto-scroll logic
  React.useEffect(() => {
    if (activeSegmentRef.current) {
      activeSegmentRef.current.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      });
    }
  }, [currentTime]);

  const resolvedText = transcription?.text ?? "";
  const resolvedSegments = React.useMemo(() => transcription?.segments ?? [], [transcription]);
  const isDiarized = resolvedSegments.some((segment) => Boolean(segment.speaker));
  
  const durationSeconds = React.useMemo(() => {
    if (resolvedSegments.length > 0) {
      return resolvedSegments[resolvedSegments.length - 1].end;
    }
    return null;
  }, [resolvedSegments]);

  const formattedDuration = React.useMemo(() => {
    if (!durationSeconds) return null;
    const minutes = Math.floor(durationSeconds / 60);
    const seconds = Math.round(durationSeconds % 60).toString().padStart(2, '0');
    return `${minutes}m${seconds}`;
  }, [durationSeconds]);

  const handleDownload = () => {
    if (transcription && resolvedText) {
      const blob = new Blob([resolvedText], { type: "text/plain;charset=utf-8" });
      saveAs(blob, `transcription-${mediaId}.txt`);
    }
  };

  const canDownload = transcription?.status === TranscriptionStatus.COMPLETED && !!resolvedText;

  const renderContent = () => {
    if (isLoading) {
      return <Skeleton className="h-48 w-full" />;
    }
    if (isError || !transcription) {
      return <p className="text-muted-foreground">Transcription not available.</p>;
    }

    return (
      <div className="space-y-4">
        {formattedDuration && (
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <span>Duração</span>
            <span className="font-medium">{formattedDuration}</span>
          </div>
        )}
        <div 
          className="h-96 overflow-y-auto space-y-2 rounded-md border p-4 bg-muted/20 focus-within:ring-2 focus-within:ring-primary/20 transition-all"
          role="region"
          aria-label="Transcrição interativa"
        >
          {resolvedSegments.length > 0 ? (
            resolvedSegments.map((segment, index) => {
              const isActive = currentTime >= segment.start && currentTime < segment.end;
              const speakerId = segment.speaker || 'UNKNOWN';
              const speakerLabel = transcription.speaker_aliases?.[speakerId] || speakerId;
              const speakerColor = isDiarized ? getSpeakerColor(speakerId) : 'text-foreground';

              return (
                <div
                  key={index}
                  ref={isActive ? activeSegmentRef : null}
                  onClick={() => handleSegmentClick(segment)}
                  onKeyDown={(e) => handleKeyDown(e, segment)}
                  role="button"
                  tabIndex={0}
                  aria-pressed={isActive}
                  aria-label={`Locutor ${speakerLabel} em ${segment.start.toFixed(1)} segundos`}
                  className={cn(
                    "cursor-pointer rounded-md p-2 transition-all outline-none focus-visible:ring-2 focus-visible:ring-primary",
                    isActive 
                      ? "bg-primary/20 shadow-sm border border-primary/10 font-medium" 
                      : "hover:bg-accent border border-transparent"
                  )}
                >
                  {isDiarized ? (
                    <p><span className={cn("font-bold", speakerColor)}>{speakerLabel}:</span> {segment.text}</p>
                  ) : (
                    <p>{segment.text}</p>
                  )}
                </div>
              );
            })
          ) : (
            <div className="p-2 text-sm leading-relaxed text-slate-700 whitespace-pre-wrap italic">
              {resolvedText || "Transcrição disponível apenas em formato bruto."}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex justify-between items-center">
          <span>Transcrição</span>
          <div className="flex items-center gap-2">
            {isDiarized && <EditSpeakersDialog transcription={transcription!} />}
            <Button variant="outline" size="icon" onClick={handleDownload} disabled={!canDownload}>
              <Download className="h-4 w-4" />
              <span className="sr-only">Baixar transcrição</span>
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
