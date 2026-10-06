import { QueryClient } from '@tanstack/react-query';
import { describe, expect, it, vi } from 'vitest';
import { createNoticeBatcher, refreshForNotification } from './realtime';

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

describe('createNoticeBatcher', () => {
  it('junta num só aviso o que chega logo após a conexão abrir', () => {
    vi.useFakeTimers();
    const show = vi.fn();
    const batcher = createNoticeBatcher(show, 1000);

    batcher.open();
    for (let i = 0; i < 30; i += 1) batcher.push(`aviso ${i}`);
    expect(show).not.toHaveBeenCalled();

    vi.advanceTimersByTime(1000);
    expect(show).toHaveBeenCalledTimes(1);
    expect(show).toHaveBeenCalledWith('Você tem 30 avisos novos.');

    batcher.push('depois');
    expect(show).toHaveBeenLastCalledWith('depois');
    vi.useRealTimers();
  });

  it('mostra o texto quando só um aviso chega na janela, e nada após cancelar', () => {
    vi.useFakeTimers();
    const show = vi.fn();
    const batcher = createNoticeBatcher(show, 1000);

    batcher.open();
    batcher.push('único');
    vi.advanceTimersByTime(1000);
    expect(show).toHaveBeenCalledWith('único');

    batcher.open();
    batcher.push('descartado');
    batcher.cancel();
    vi.advanceTimersByTime(1000);
    expect(show).toHaveBeenCalledTimes(1);
    vi.useRealTimers();
  });
});
