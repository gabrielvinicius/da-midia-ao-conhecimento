import * as React from 'react';
import { MediaType } from '@/types';

interface MediaPlayerProps {
  src: string;
  mediaType: MediaType.AUDIO | MediaType.VIDEO;
  onTimeUpdate: (time: number) => void;
  playerRef: React.RefObject<HTMLMediaElement>;
}

export const MediaPlayer = ({ src, mediaType, onTimeUpdate, playerRef }: MediaPlayerProps) => {
  const handleTimeUpdate = (e: React.SyntheticEvent<HTMLMediaElement>) => {
    onTimeUpdate(e.currentTarget.currentTime);
  };

  if (mediaType === MediaType.VIDEO) {
    return (
      <video
        ref={playerRef as React.RefObject<HTMLVideoElement>}
        src={src}
        controls
        className="w-full rounded-lg bg-black"
        onTimeUpdate={handleTimeUpdate}
      />
    );
  }

  if (mediaType === MediaType.AUDIO) {
    return (
      <audio
        ref={playerRef as React.RefObject<HTMLAudioElement>}
        src={src}
        controls
        className="w-full"
        onTimeUpdate={handleTimeUpdate}
      />
    );
  }

  return null;
};
