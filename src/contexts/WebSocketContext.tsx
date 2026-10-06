import { createContext, useContext, useState, useEffect, ReactNode, useCallback, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from './AuthContext';
import { Notification } from '@/types';
import { toast } from 'react-toastify';
import { requestScopedToken } from '@/api/scopedToken';
import { buildWsUrl } from '@/lib/api';
import { refreshForNotification } from '@/lib/realtime';
import {
  listNotifications,
  markAllNotificationsAsRead,
  markNotificationAsRead,
} from '@/features/notifications/api';

export type ConnectionStatus = 'CONNECTING' | 'OPEN' | 'CLOSING' | 'CLOSED' | 'RECONNECTING';

interface WebSocketContextType {
  notifications: Notification[];
  unreadCount: number;
  connectionStatus: ConnectionStatus;
  markAsRead: (notificationId: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

const NOTIFICATIONS_KEY = ['notifications'];

/** Aviso recebido pelo WebSocket, no formato da lista da API. */
export const notificationFromMessage = (payload: Record<string, unknown>): Notification => ({
  id: String(payload.id),
  user_id: String(payload.user_id ?? ''),
  type: String(payload.type ?? 'websocket'),
  content: String(payload.content ?? ''),
  priority: String(payload.priority ?? 'normal'),
  status: String(payload.status ?? 'pending'),
  created_at: String(payload.created_at ?? new Date().toISOString()),
  read: Boolean(payload.read ?? false),
  variables: (payload.variables as Record<string, unknown>) ?? {},
});

export const WebSocketProvider = ({ children }: { children: ReactNode }) => {
  const { user, isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('CLOSED');
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnectRef = useRef(true);

  // Os avisos ficam gravados no servidor: ao abrir a página aparecem também
  // os que chegaram com ela fechada.
  const { data: notifications = [] } = useQuery({
    queryKey: NOTIFICATIONS_KEY,
    queryFn: listNotifications,
    enabled: isAuthenticated,
    staleTime: 60_000,
  });

  const setCached = useCallback(
    (update: (old: Notification[]) => Notification[]) =>
      queryClient.setQueryData<Notification[]>(NOTIFICATIONS_KEY, (old) => update(old ?? [])),
    [queryClient],
  );

  const connect = useCallback(async () => {
    if (socketRef.current || !isAuthenticated || !user) return;

    // Token de abertura, válido por 2 min: o token de acesso não vai na URL.
    let token: string;
    try {
      token = await requestScopedToken("notifications");
    } catch {
      reconnectTimerRef.current = setTimeout(() => connect(), 5000);
      return;
    }
    if (socketRef.current) return;
    const ws = new WebSocket(`${buildWsUrl("/ws/notifications")}?token=${encodeURIComponent(token)}`);
    socketRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus('OPEN');
      shouldReconnectRef.current = true;
      // Recupera o que mudou enquanto a conexão estava fechada.
      queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_KEY });
      queryClient.invalidateQueries({ queryKey: ['media-list'] });
      queryClient.invalidateQueries({ queryKey: ['media-stats'] });
      queryClient.invalidateQueries({ queryKey: ['system-status'] });
    };

    ws.onclose = (event) => {
      setConnectionStatus('CLOSED');
      socketRef.current = null;

      // Token expirado ou recusado: não insiste em reconectar.
      if (event?.code === 1008) {
        shouldReconnectRef.current = false;
        return;
      }

      if (isAuthenticated && shouldReconnectRef.current) {
        setConnectionStatus('RECONNECTING');
        if (reconnectTimerRef.current) {
          clearTimeout(reconnectTimerRef.current);
        }
        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, 5000);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        const kind: string | undefined = message.kind ?? message.type;
        const payload = message.payload ?? message;
        if (kind !== 'new_notification' || !payload) return;

        const notification = notificationFromMessage(payload);
        setCached((old) => [notification, ...old.filter((n) => n.id !== notification.id)]);
        refreshForNotification(queryClient, notification.variables);
        toast.info(notification.content);
      } catch (parseError) {
        console.error('Failed to parse WebSocket message:', parseError);
      }
    };
  }, [isAuthenticated, user, queryClient, setCached]);

  useEffect(() => {
    if (isAuthenticated && user) {
      shouldReconnectRef.current = true;
      connect();
    } else {
      if (socketRef.current) {
        setConnectionStatus('CLOSING');
        shouldReconnectRef.current = false;
        socketRef.current.close();
        socketRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    }

    return () => {
      if (socketRef.current) {
        shouldReconnectRef.current = false;
        socketRef.current.close();
        socketRef.current = null;
      }
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    };
  }, [isAuthenticated, user, connect]);

  const markAsRead = useCallback(async (notificationId: string) => {
    setCached((old) => old.map((n) => (n.id === notificationId ? { ...n, read: true } : n)));
    try {
      await markNotificationAsRead(notificationId);
    } catch (error) {
      console.error("Failed to mark notification as read:", error);
      queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_KEY });
    }
  }, [queryClient, setCached]);

  const markAllAsRead = useCallback(async () => {
    setCached((old) => old.map((n) => ({ ...n, read: true })));
    try {
      await markAllNotificationsAsRead();
    } catch (error) {
      console.error("Failed to mark all notifications as read:", error);
      queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_KEY });
    }
  }, [queryClient, setCached]);

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <WebSocketContext.Provider value={{ notifications, unreadCount, connectionStatus, markAsRead, markAllAsRead }}>
      {children}
    </WebSocketContext.Provider>
  );
};

export const useWebSocket = () => {
  const context = useContext(WebSocketContext);
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider');
  }
  return context;
};
