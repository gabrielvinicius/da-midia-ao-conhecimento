import * as React from 'react';
import { MediaType } from '@/types';

interface MediaPlayerProps {
  src: string;
  mediaType: MediaType.AUDIO | MediaType.VIDEO;
  onTimeUpdate: (time: number) => void;
  playerRef: React.RefObject<HTMLMediaElement | null>;
  /** Segundo em que a reprodução deve começar (ex.: trecho achado na busca). */
  startAt?: number;
}

export const MediaPlayer = ({ src, mediaType, onTimeUpdate, playerRef, startAt }: MediaPlayerProps) => {
  // Posiciona quando os metadados chegam: antes disso o navegador ignora a
  // mudança de tempo. Não inicia a reprodução, que os navegadores bloqueiam
  // sem um clique do usuário.
  const handleLoadedMetadata = (e: React.SyntheticEvent<HTMLMediaElement>) => {
    const { duration } = e.currentTarget;
    if (startAt && startAt > 0 && (!Number.isFinite(duration) || startAt < duration)) {
      e.currentTarget.currentTime = startAt;
    }
  };

  const handleTimeUpdate = (e: React.SyntheticEvent<HTMLMediaElement>) => {
    onTimeUpdate(e.currentTarget.currentTime);
  };

  if (mediaType === MediaType.VIDEO) {
    return (
      <video
        ref={playerRef as React.RefObject<HTMLVideoElement>}
        src={src}
        controls
        preload="metadata"
        className="aspect-video w-full bg-black"
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
      />
    );
  }

  if (mediaType === MediaType.AUDIO) {
    return (
      <audio
        ref={playerRef as React.RefObject<HTMLAudioElement>}
        src={src}
        controls
        preload="metadata"
        className="w-full p-3"
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
      />
    );
  }

  return null;
};
