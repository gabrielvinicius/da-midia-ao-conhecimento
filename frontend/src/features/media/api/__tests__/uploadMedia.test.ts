import { AxiosError, AxiosHeaders } from 'axios';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const api = vi.hoisted(() => ({ post: vi.fn(), put: vi.fn(), get: vi.fn(), delete: vi.fn() }));
vi.mock('@/lib/api', () => ({ default: api }));

import { uploadMedia } from '../index';

const httpError = (status?: number) =>
  new AxiosError('falha', 'ERR', undefined, undefined, status
    ? { status, data: {}, statusText: '', headers: {}, config: { headers: new AxiosHeaders() } }
    : undefined);

const file = (size: number) => new File([new Uint8Array(size)], 'aula.mp4', { type: 'video/mp4' });

describe('uploadMedia (em partes)', () => {
  beforeEach(() => {
    vi.useRealTimers();
    Object.values(api).forEach((fn) => fn.mockReset());
    api.post.mockImplementation(async (url: string) =>
      url === '/media/uploads'
        ? { data: { upload_id: 'u1', offset: 0, size_bytes: 25, part_max_bytes: 10 } }
        : { data: { id: 'm1' } },
    );
    api.delete.mockResolvedValue({});
  });

  it('manda o arquivo em partes do tamanho aceito e conclui', async () => {
    api.put.mockImplementation(async (_url: string, blob: Blob, config: { params: { offset: number } }) => ({
      data: { offset: config.params.offset + blob.size },
    }));
    const progress: number[] = [];

    const media = await uploadMedia({ file: file(25), storageProvider: 'local' }, { onProgress: (p) => progress.push(p) });

    expect(media).toEqual({ id: 'm1' });
    expect(api.put.mock.calls.map(([, blob, config]) => [config.params.offset, blob.size])).toEqual([
      [0, 10],
      [10, 10],
      [20, 5],
    ]);
    expect(api.post).toHaveBeenLastCalledWith('/media/uploads/u1/complete', null, expect.anything());
    expect(api.post.mock.calls[0][1]).toMatchObject({ filename: 'aula.mp4', size_bytes: 25 });
  });

  it('repete uma parte que falhou a partir do ponto confirmado pelo servidor', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    api.put
      .mockResolvedValueOnce({ data: { offset: 10 } })
      .mockRejectedValueOnce(httpError())
      .mockResolvedValueOnce({ data: { offset: 20 } })
      .mockResolvedValueOnce({ data: { offset: 25 } });
    api.get.mockResolvedValue({ data: { offset: 10 } });

    await uploadMedia({ file: file(25), storageProvider: 'local' });

    expect(api.put.mock.calls.map(([, , config]) => config.params.offset)).toEqual([0, 10, 10, 20]);
  });

  it('não repete um arquivo recusado e libera o envio no servidor', async () => {
    api.put.mockRejectedValue(httpError(400));

    await expect(uploadMedia({ file: file(25), storageProvider: 'local' })).rejects.toBeInstanceOf(AxiosError);
    expect(api.put).toHaveBeenCalledTimes(1);
    expect(api.delete).toHaveBeenCalledWith('/media/uploads/u1');
  });
});
