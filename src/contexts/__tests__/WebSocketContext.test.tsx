import { act, render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { beforeEach, describe, expect, it, vi } from 'vitest';

const auth = { user: { id: 'u1' } as { id: string } | null, isAuthenticated: true };
let resolveToken: (token: string) => void = () => {};

vi.mock('../AuthContext', () => ({ useAuth: () => auth }));
vi.mock('@/features/authentication/api/scopedToken', () => ({
  requestScopedToken: vi.fn(() => new Promise<string>((resolve) => { resolveToken = resolve; })),
}));
vi.mock('@/features/notifications/api', () => ({
  listNotifications: vi.fn(async () => []),
  markAllNotificationsAsRead: vi.fn(),
  markNotificationAsRead: vi.fn(),
}));
vi.mock('@/lib/api', () => ({ buildWsUrl: (path: string) => `ws://test${path}` }));

import { WebSocketProvider } from '../WebSocketContext';

class FakeSocket {
  static created: FakeSocket[] = [];
  onopen: (() => void) | null = null;
  onclose: ((event: { code: number }) => void) | null = null;
  onerror: ((error: unknown) => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  constructor(public url: string) { FakeSocket.created.push(this); }
  close = vi.fn();
}

const renderProvider = () => {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <WebSocketProvider><div /></WebSocketProvider>
    </QueryClientProvider>,
  );
};

describe('WebSocketProvider', () => {
  beforeEach(() => {
    FakeSocket.created = [];
    vi.stubGlobal('WebSocket', FakeSocket);
    auth.user = { id: 'u1' };
    auth.isAuthenticated = true;
  });

  it('abre a conexão quando o token de abertura chega', async () => {
    renderProvider();
    await act(async () => resolveToken('tok'));
    expect(FakeSocket.created).toHaveLength(1);
    expect(FakeSocket.created[0].url).toBe('ws://test/ws/notifications?token=tok');
  });

  it('não abre a conexão se o usuário saiu enquanto o token era pedido', async () => {
    const view = renderProvider();
    auth.user = null;
    auth.isAuthenticated = false;
    view.rerender(
      <QueryClientProvider client={new QueryClient()}>
        <WebSocketProvider><div /></WebSocketProvider>
      </QueryClientProvider>,
    );
    await act(async () => resolveToken('tok'));
    expect(FakeSocket.created).toHaveLength(0);
  });
});
