import { createContext, useContext, useState, useEffect, ReactNode, useCallback, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useAuth } from './AuthContext';
import { Notification } from '@/types';
import { toast } from 'react-toastify';
import { requestScopedToken } from '@/features/authentication/api/scopedToken';
import { buildWsUrl } from '@/lib/api';
import { createNoticeBatcher, refreshForNotification } from '@/lib/realtime';
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
const RECONNECT_DELAY_MS = 5000;

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
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Se a conexão ainda é desejada: falso após o logout, ao desmontar ou
  // quando o servidor recusa o token (código 1008).
  const wantedRef = useRef(false);
  // Muda a cada sessão que pede a conexão: um token que chega atrasado, de
  // um usuário que já saiu, não abre o socket do usuário seguinte.
  const generationRef = useRef(0);
  const noticesRef = useRef(createNoticeBatcher((message) => toast.info(message)));

  // Os avisos ficam gravados no servidor: ao abrir a página aparecem também
  // os que chegaram com ela fechada.
  const { data: notifications = [] } = useQuery({
    queryKey: NOTIFICATIONS_KEY,
    queryFn: () => listNotifications(),
    enabled: isAuthenticated,
    staleTime: 60_000,
  });

  const setCached = useCallback(
    (update: (old: Notification[]) => Notification[]) =>
      queryClient.setQueryData<Notification[]>(NOTIFICATIONS_KEY, (old) => update(old ?? [])),
    [queryClient],
  );

  const scheduleReconnect = useCallback((reconnect: () => void) => {
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
    reconnectTimerRef.current = setTimeout(() => {
      reconnectTimerRef.current = null;
      if (wantedRef.current) reconnect();
    }, RECONNECT_DELAY_MS);
  }, []);

  const connect = useCallback(async () => {
    if (socketRef.current || !wantedRef.current) return;
    const generation = generationRef.current;

    // Token de abertura, válido por 2 min: o token de acesso não vai na URL.
    let token: string;
    try {
      token = await requestScopedToken("notifications");
    } catch {
      scheduleReconnect(connect);
      return;
    }
    // Durante a espera do token o usuário pode ter saído (ou outro ter
    // entrado): sem esta checagem, o socket abria depois do logout.
    if (socketRef.current || !wantedRef.current || generation !== generationRef.current) return;
    const ws = new WebSocket(`${buildWsUrl("/ws/notifications")}?token=${encodeURIComponent(token)}`);
    socketRef.current = ws;
    setConnectionStatus('CONNECTING');

    ws.onopen = () => {
      setConnectionStatus('OPEN');
      noticesRef.current.open();
      // Recupera o que mudou enquanto a conexão estava fechada.
      queryClient.invalidateQueries({ queryKey: NOTIFICATIONS_KEY });
      queryClient.invalidateQueries({ queryKey: ['media-list'] });
      queryClient.invalidateQueries({ queryKey: ['media-stats'] });
      queryClient.invalidateQueries({ queryKey: ['system-status'] });
    };

    ws.onclose = (event) => {
      if (socketRef.current !== ws) return; // fechada por disconnect()
      socketRef.current = null;
      setConnectionStatus('CLOSED');

      // Token expirado ou recusado: não insiste em reconectar.
      if (event?.code === 1008) {
        wantedRef.current = false;
        return;
      }
      if (wantedRef.current) {
        setConnectionStatus('RECONNECTING');
        scheduleReconnect(connect);
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
        noticesRef.current.push(notification.content);
      } catch (parseError) {
        console.error('Failed to parse WebSocket message:', parseError);
      }
    };
  }, [queryClient, setCached, scheduleReconnect]);

  const disconnect = useCallback(() => {
    wantedRef.current = false;
    noticesRef.current.cancel();
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    const ws = socketRef.current;
    socketRef.current = null;
    if (ws) {
      setConnectionStatus('CLOSING');
      ws.close();
    }
    setConnectionStatus('CLOSED');
  }, []);

  const userId = user?.id;
  useEffect(() => {
    if (!isAuthenticated || !userId) return undefined;
    generationRef.current += 1;
    wantedRef.current = true;
    connect();
    return disconnect;
  }, [isAuthenticated, userId, connect, disconnect]);

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
