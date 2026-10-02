import { QueryClient } from '@tanstack/react-query';
import { describe, expect, it, vi } from 'vitest';
import { refreshForNotification } from './realtime';

const invalidatedKeys = (client: QueryClient) =>
  vi.mocked(client.invalidateQueries).mock.calls.map(([filters]) => filters?.queryKey);

describe('refreshForNotification', () => {
  it('recarrega mídia, transcrição e análise quando o aviso cita uma mídia', () => {
    const client = new QueryClient();
    vi.spyOn(client, 'invalidateQueries');

    refreshForNotification(client, { media_id: 'm1', evento: 'TextAnalysisCompleted' });

    expect(invalidatedKeys(client)).toEqual(
      expect.arrayContaining([
        ['media', 'm1'],
        ['transcription', 'm1'],
        ['text-analysis', 'm1'],
        ['media-list'],
        ['admin-all-media'],
        ['admin-stats'],
      ]),
    );
  });

  it('não recarrega nada quando o aviso não cita mídia', () => {
    const client = new QueryClient();
    vi.spyOn(client, 'invalidateQueries');

    refreshForNotification(client, {});
    refreshForNotification(client, undefined);

    expect(client.invalidateQueries).not.toHaveBeenCalled();
  });
});
