import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuth } from './AuthContext';
import { Notification, Media } from '@/types';
import { toast } from 'react-toastify';
import authService from '@/services/auth.service';
import { buildWsUrl } from '@/lib/api';

export type ConnectionStatus = 'CONNECTING' | 'OPEN' | 'CLOSING' | 'CLOSED' | 'RECONNECTING';

interface WebSocketContextType {
  notifications: Notification[];
  unreadCount: number;
  connectionStatus: ConnectionStatus;
  markAsRead: (notificationId: string) => Promise<void>;
  markAllAsRead: () => Promise<void>;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

export const WebSocketProvider = ({ children }: { children: ReactNode }) => {
  const { user, isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('CLOSED');
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const shouldReconnectRef = useRef(true);

  const connect = useCallback(() => {
    if (socketRef.current || !isAuthenticated || !user) return;

    const token = authService.getToken();
    const baseUrl = buildWsUrl("/ws/notifications");
    const wsUrl = token ? `${baseUrl}?token=${encodeURIComponent(token)}` : baseUrl;
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => {
      setConnectionStatus('OPEN');
    };

    ws.onclose = (event) => {
      setConnectionStatus('CLOSED');
      socketRef.current = null;

      // Se o token expirou ou foi rejeitado, evite loop infinito de reconexão
      if (event?.code === 1008) {
        shouldReconnectRef.current = false;
        return;
      }

      // Attempt to reconnect if user is still authenticated
      if (isAuthenticated && shouldReconnectRef.current) {
        setConnectionStatus('RECONNECTING');
        if (reconnectTimerRef.current) {
          clearTimeout(reconnectTimerRef.current);
        }
        reconnectTimerRef.current = setTimeout(() => {
          connect();
        }, 5000); // Reconnect after 5 seconds
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        const baseType: string | undefined = message.kind ?? message.type;
        const payload = message.payload ?? message;
        
        switch (baseType) {
          case 'new_notification':
            if (!payload) break;
            try {
              const newNotification: Notification = {
                id: String(payload.id),
                user_id: String(payload.user_id ?? ''),
                type: payload.type ?? 'INFO',
                content: payload.content ?? '',
                priority: payload.priority ?? 'NORMAL',
                status: payload.status ?? 'NEW',
                template_name: payload.template_name ?? null,
                variables: payload.variables ?? {},
                error_message: payload.error_message ?? null,
                sent_at: payload.sent_at ?? null,
                delivered_at: payload.delivered_at ?? null,
                opened_at: payload.opened_at ?? null,
                created_at: payload.created_at ?? new Date().toISOString(),
                updated_at: payload.updated_at ?? payload.created_at ?? null,
                retries: payload.retries ?? 0,
                max_retries: payload.max_retries ?? 3,
                read: Boolean(payload.read ?? false),
              };
              setNotifications(prev => [newNotification, ...prev]);
              queryClient.setQueryData(['notifications'], (old: Notification[] | undefined) =>
                old ? [newNotification, ...old] : [newNotification]
              );
              toast.info(`Nova notificação: ${newNotification.content}`);
            } catch (err) {
              console.warn('Falha ao normalizar notificação WS', err);
            }
            break;
          case 'MEDIA_STATUS': {
            const mediaId = payload.media_id || payload.mediaId;
            if (mediaId) {
              queryClient.setQueryData(['media', mediaId], (oldData: Media | undefined) =>
                oldData
                  ? {
                      ...oldData,
                      status: payload.status ?? oldData.status,
                      error_message: payload.error ?? (oldData as any)?.error_message ?? null,
                    }
                  : oldData
              );
              queryClient.invalidateQueries({ queryKey: ['media', mediaId] });
              queryClient.invalidateQueries({ queryKey: ['media-list'] });
            }
            break;
          }
          
          case 'entity_update': {
            const { entity } = message;
            const entityPayload = message.payload;
            if (!entity || !entityPayload) {
              break;
            }

            const normalized = String(entity).toLowerCase();
            const mediaId = entityPayload.media_id || entityPayload.mediaId;

            if (normalized === 'topic-modeling' || normalized === 'topic_modeling') {
              if (mediaId) {
                queryClient.invalidateQueries({ queryKey: ['text-analysis', mediaId] });
              }
              break;
            }

            if (normalized === 'summary' || normalized === 'summaries') {
              if (mediaId) {
                queryClient.invalidateQueries({ queryKey: ['text-analysis', mediaId] });
              }
              break;
            }

            if (normalized === 'sentiment-analysis' || normalized === 'sentiment_analysis' || normalized === 'sentiment') {
              if (mediaId) {
                queryClient.invalidateQueries({ queryKey: ['text-analysis', mediaId] });
              }
              break;
            }

            if (entityPayload?.id) {
              queryClient.setQueryData([entity, entityPayload.id], entityPayload);
            }

            if (normalized === 'media') {
              queryClient.invalidateQueries({ queryKey: ['media-list'] });
            }
            break;
          }
            
          case 'transcription_update':
          case 'summary_update':
          case 'processing_complete': {
            const { media_id, status, result } = payload;
            if (media_id) {
              queryClient.setQueryData(['media', media_id], (oldData: Media | undefined) =>
                oldData
                  ? {
                      ...oldData,
                      status: status ?? oldData.status,
                      ...(result ? { result } : {}),
                    }
                  : oldData
              );
              queryClient.invalidateQueries({ queryKey: ['media', media_id] });
              queryClient.invalidateQueries({ queryKey: ['transcription', media_id] });
              queryClient.invalidateQueries({ queryKey: ['text-analysis', media_id] });
            }
            break;
          }
            
          default:
            console.warn('Received unknown WebSocket message type:', baseType);
        }
      } catch (parseError) {
        console.error('Failed to parse WebSocket message:', parseError);
      }
    };
  }, [isAuthenticated, user, queryClient]);

  // Effect to manage WebSocket connection lifecycle
  useEffect(() => {
    if (isAuthenticated && user) {
      shouldReconnectRef.current = true;
      connect();
    } else {
      // Close connection if user is no longer authenticated
      if (socketRef.current) {
        setConnectionStatus('CLOSING');
        shouldReconnectRef.current = false;
        socketRef.current.close();
        socketRef.current = null;
      }
      
      // Clear any pending reconnection attempts
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = null;
      }
    }

    // Cleanup on unmount
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
    try {
      // In a real implementation, this would make an API call to mark as read
      setNotifications(prev =>
        prev.map(notif => 
          notif.id === notificationId ? { ...notif, read: true } : notif
        )
      );
      
      // Update in query cache
      queryClient.setQueryData(['notifications'], (old: Notification[] | undefined) => 
        old?.map(notif => 
          notif.id === notificationId ? { ...notif, read: true } : notif
        )
      );
    } catch (error) {
      console.error("Failed to mark notification as read:", error);
    }
  }, [queryClient]);

  const markAllAsRead = useCallback(async () => {
    try {
      setNotifications(prev => 
        prev.map(notif => ({ ...notif, read: true }))
      );
      
      // Update in query cache
      queryClient.setQueryData(['notifications'], (old: Notification[] | undefined) => 
        old?.map(notif => ({ ...notif, read: true }))
      );
    } catch (error) {
      console.error("Failed to mark all notifications as read:", error);
    }
  }, [queryClient]);

  const unreadCount = notifications.filter(notif => !notif.read).length;

  const value = {
    notifications,
    unreadCount,
    connectionStatus,
    markAsRead,
    markAllAsRead
  };

  return (
    <WebSocketContext.Provider value={value}>
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
