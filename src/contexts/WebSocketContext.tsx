import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuth } from './AuthContext';
import { Notification } from '../types';
import { toast } from 'react-toastify';
import authService from '../services/auth.service';
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
      console.log('WebSocket connected');
      setConnectionStatus('OPEN');
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setConnectionStatus('CLOSED');
      socketRef.current = null;
      
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
        
        switch (message.type) {
          case 'new_notification':
            const newNotification = message.payload as Notification;
            setNotifications(prev => [newNotification, ...prev]);
            toast.info(`New notification: ${newNotification.content}`);
            break;
            
          case 'entity_update':
            const { entity, payload } = message;
            // Update the specific entity in the query cache
            queryClient.setQueryData([entity, payload.id], payload);
            
            // Invalidate related queries to trigger refetch
            if (entity === 'media') {
              queryClient.invalidateQueries({ queryKey: ['media-list'] });
            } else {
              queryClient.invalidateQueries({ queryKey: [entity] });
            }
            break;
            
          case 'transcription_update':
          case 'summary_update':
          case 'processing_complete':
            // Handle specific media processing updates
            const { media_id, status, result } = message;
            if (media_id) {
              queryClient.setQueryData(['media', media_id], (oldData: any) => ({
                ...oldData,
                status: status,
                ...(result && { result: result })
              }));
              
              queryClient.invalidateQueries({ queryKey: ['media', media_id] });
            }
            break;
            
          default:
            console.warn('Received unknown WebSocket message type:', message.type);
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
