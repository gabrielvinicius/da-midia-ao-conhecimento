import { QueryClient } from '@tanstack/react-query';
import { describe, expect, it } from 'vitest';
import { removeFromCachedPages, restoreCachedPages } from './optimistic';

const page = (ids: string[]) => ({ items: ids.map((id) => ({ id })), total: ids.length, page: 1, pages: 1, limit: 10 });

describe('removeFromCachedPages', () => {
  it('remove o item de todas as páginas em cache, com qualquer filtro', () => {
    const client = new QueryClient();
    client.setQueryData(['media-list', 1, 10, 'desc', ''], page(['a', 'b']));
    client.setQueryData(['media-list', 1, 10, 'desc', 'aula'], page(['b']));
    client.setQueryData(['media', 'b'], { id: 'b' });

    const snapshot = removeFromCachedPages(client, ['media-list'], 'b');

    expect(client.getQueryData(['media-list', 1, 10, 'desc', ''])).toMatchObject({ items: [{ id: 'a' }], total: 1 });
    expect(client.getQueryData(['media-list', 1, 10, 'desc', 'aula'])).toMatchObject({ items: [], total: 0 });
    expect(client.getQueryData(['media', 'b'])).toEqual({ id: 'b' }); // fora do prefixo

    restoreCachedPages(client, snapshot);
    expect(client.getQueryData(['media-list', 1, 10, 'desc', ''])).toMatchObject({ total: 2 });
  });
});
