import type { QueryClient, QueryKey } from '@tanstack/react-query';
import type { Paginated } from '@/types';

export type ListSnapshot = Array<[QueryKey, unknown]>;

/**
 * Tira o item de todas as páginas em cache cuja chave começa com `prefix`
 * (ex.: ['media-list'] cobre ['media-list', 1, 10, 'desc', '']) e devolve o
 * estado anterior, para desfazer se a exclusão falhar.
 */
export function removeFromCachedPages(
  queryClient: QueryClient,
  prefix: QueryKey,
  id: string,
): ListSnapshot {
  const snapshot = queryClient.getQueriesData<Paginated<{ id: string }>>({ queryKey: prefix });
  for (const [key, page] of snapshot) {
    if (!page || !Array.isArray(page.items)) continue;
    const items = page.items.filter((item) => item.id !== id);
    if (items.length === page.items.length) continue;
    queryClient.setQueryData(key, { ...page, items, total: Math.max(0, page.total - 1) });
  }
  return snapshot;
}

export function restoreCachedPages(queryClient: QueryClient, snapshot: ListSnapshot | undefined) {
  for (const [key, page] of snapshot ?? []) queryClient.setQueryData(key, page);
}
