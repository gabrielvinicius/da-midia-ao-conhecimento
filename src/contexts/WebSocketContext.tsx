import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuth } from './AuthContext';
import { Notification, Media, Transcription, Summary } from '../types';
import { toast } from 'react-toastify';

// This context will now handle both notifications and real-time entity updates.
interface WebSocketContextType {
  notifications: Notification[];
  unreadCount: number;
  markAsRead: (notificationId: string) => void;
  markAllAsRead: () => void;
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined);

const WS_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/^http/, 'ws');

export const WebSocketProvider = ({ children }: { children: ReactNode }) => {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [socket, setSocket] = useState<WebSocket | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      if (socket) {
        socket.close();
        setSocket(null);
      }
      return;
    }

    const token = localStorage.getItem('token');
    if (!token) return;

    const ws = new WebSocket(`${WS_URL}/notifications/ws?token=${token}`);

    ws.onopen = () => console.log('WebSocket connected');
    ws.onclose = () => console.log('WebSocket disconnected');
    ws.onerror = (error) => console.error('WebSocket error:', error);

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      // Message Dispatcher
      switch (message.type) {
        case 'new_notification':
          const newNotification = message.payload as Notification;
          setNotifications((prev) => [newNotification, ...prev]);
          toast.info(`New notification: ${newNotification.content}`);
          break;

        case 'entity_update':
          const { entity, payload } = message;
          console.log(`Received update for ${entity}:`, payload);
          // Update the React Query cache directly
          switch (entity) {
            case 'media':
              const updatedMedia = payload as Media;
              queryClient.setQueryData(['mediaDetail', updatedMedia.id], updatedMedia);
              queryClient.setQueryData<Media[]>(['mediaList'], (oldData) => 
                oldData?.map((item) => item.id === updatedMedia.id ? updatedMedia : item)
              );
              break;
            case 'transcription':
              const updatedTranscription = payload as Transcription;
              queryClient.setQueryData(['transcription', updatedTranscription.media_id], updatedTranscription);
              break;
            case 'summary':
              const updatedSummary = payload as Summary;
              queryClient.setQueryData(['summary', updatedSummary.media_id], updatedSummary);
              break;
          }
          break;

        default:
          console.warn('Received unknown WebSocket message type:', message.type);
      }
    };

    setSocket(ws);

    return () => ws.close();
  }, [isAuthenticated, queryClient]);

  const markAsRead = useCallback((notificationId: string) => {
    setNotifications((prev) => prev.map((n) => (n.id === notificationId ? { ...n, read: true } : n)));
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <WebSocketContext.Provider value={{ notifications, unreadCount, markAsRead, markAllAsRead }}>
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
