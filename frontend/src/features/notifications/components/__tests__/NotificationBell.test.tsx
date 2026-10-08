import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { render, screen } from '@/test/test-utils';
import { NotificationBell } from '../NotificationBell';

const markAsRead = vi.fn();
const markAllAsRead = vi.fn();
let notifications: Array<Record<string, unknown>> = [];

vi.mock('@/contexts/WebSocketContext', () => ({
  useWebSocket: () => ({
    notifications,
    unreadCount: notifications.filter((n) => !n.read).length,
    markAsRead,
    markAllAsRead,
  }),
}));

const aviso = (id: string, read: boolean) => ({
  id, user_id: 'u', type: 'websocket', content: `Aviso ${id}`, priority: 'normal',
  status: 'delivered', created_at: new Date().toISOString(), read,
});

describe('NotificationBell', () => {
  beforeEach(() => { markAsRead.mockReset(); markAllAsRead.mockReset(); });

  it('mostra os avisos em português e marca um como lido ao clicar', async () => {
    notifications = [aviso('a', false), aviso('b', true)];
    render(<NotificationBell />);
    await userEvent.click(screen.getByRole('button', { name: /Avisos \(1 não lidos\)/ }));

    expect(screen.getByText('Avisos')).toBeInTheDocument();
    await userEvent.click(screen.getByText('Aviso a'));
    expect(markAsRead).toHaveBeenCalledWith('a');
  });

  it('marca todos como lidos', async () => {
    notifications = [aviso('a', false)];
    render(<NotificationBell />);
    await userEvent.click(screen.getByRole('button', { name: /Avisos/ }));
    await userEvent.click(screen.getByText('Marcar todos como lidos'));
    expect(markAllAsRead).toHaveBeenCalled();
  });

  it('sem avisos, diz isso', async () => {
    notifications = [];
    render(<NotificationBell />);
    await userEvent.click(screen.getByRole('button', { name: 'Avisos' }));
    expect(screen.getByText('Nenhum aviso ainda.')).toBeInTheDocument();
  });
});
