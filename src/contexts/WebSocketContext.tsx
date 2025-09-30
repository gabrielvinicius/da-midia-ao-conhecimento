import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuth } from './AuthContext';
import { Notification, Media, Transcription, Summary } from '../types';
import { toast } from 'react-toastify';
import { getNotifications, markNotificationAsRead } from '../features/notifications/api';

export type ConnectionStatus = 'CONNECTING' | 'OPEN' | 'CLOSING' | 'CLOSED' | 'RECONNECTING';

interface WebSocketContextType {
  notifications: Notification[];
  unreadCount: number;
  connectionStatus: ConnectionStatus;
  markAsRead: (notificationId: string) => void;
  markAllAsRead: () => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

const WS_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/^http/, 'ws';

export const WebSocketProvider = ({ children }: { children: ReactNode }) => {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('CLOSED');
  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connect = useCallback(() => {
    if (socketRef.current || !isAuthenticated) return;

    const token = localStorage.getItem('token');
    if (!token) return;

    setConnectionStatus('CONNECTING');
    const ws = new WebSocket(`${WS_URL}/notifications/ws?token=${token}`);
    socketRef.current = ws;

    ws.onopen = async () => {
      console.log('WebSocket connected');
      setConnectionStatus('OPEN');
      // Fetch initial notifications state
      try {
        const initialNotifications = await getNotifications();
        setNotifications(initialNotifications);
      } catch (error) {
        console.error("Failed to fetch initial notifications:", error);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setConnectionStatus('CLOSED');
      if (isAuthenticated) {
        setConnectionStatus('RECONNECTING');
        reconnectTimeoutRef.current = setTimeout(connect, 5000);
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      ws.close();
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      switch (message.type) {
        case 'new_notification':
          const newNotification = message.payload as Notification;
          setNotifications((prev) => [newNotification, ...prev]);
          toast.info(`New notification: ${newNotification.content}`);
          break;
        case 'entity_update':
          const { entity, payload } = message;
          queryClient.setQueryData([entity, payload.id], payload);
          if (entity === 'media') {
            queryClient.setQueryData<Media[]>(['mediaList'], (old) => old?.map((m) => m.id === payload.id ? payload : m));
          } else {
            queryClient.invalidateQueries({ queryKey: [entity, payload.media_id] });
          }
          break;
        default:
          console.warn('Received unknown WebSocket message type:', message.type);
      }
    };
  }, [isAuthenticated, queryClient]);

  useEffect(() => {
    if (isAuthenticated) {
      connect();
    } else {
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    }
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
        socketRef.current = null;
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [isAuthenticated, connect]);

  const markAsRead = useCallback(async (notificationId: string) => {
    try {
      const updatedNotification = await markNotificationAsRead(notificationId);
      setNotifications((prev) =>
        prev.map((n) => (n.id === updatedNotification.id ? updatedNotification : n))
      );
    } catch (error) {
      console.error("Failed to mark notification as read:", error);
    }
  }, []);

  const markAllAsRead = useCallback(async () => {
    // In a real app, you'd have a dedicated backend endpoint for this.
    // For now, we'll mark them as read one by one.
    try {
      const unread = notifications.filter(n => !n.read);
      await Promise.all(unread.map(n => markNotificationAsRead(n.id)));
      setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    } catch (error) {
      console.error("Failed to mark all notifications as read:", error);
    }
  }, [notifications]);

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
