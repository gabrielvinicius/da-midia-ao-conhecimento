import React, { createContext, useContext, useState, useEffect, ReactNode, useCallback } from 'react';
import { useAuth } from '../../../contexts/AuthContext';
import { Notification } from '../../../types';
import { toast } from 'react-toastify';
import { buildWsUrl } from '@/lib/api';

interface NotificationContextType {
  notifications: Notification[];
  unreadCount: number;
  markAsRead: (notificationId: string) => void;
  markAllAsRead: () => void;
}

const NotificationContext = createContext<NotificationContextType | undefined>(undefined);

export const NotificationProvider = ({ children }: { children: ReactNode }) => {
  const { isAuthenticated } = useAuth();
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

    const ws = new WebSocket(buildWsUrl('/notifications/ws'));

    ws.onopen = () => {
      console.log('Notifications WebSocket connected');
    };

    ws.onmessage = (event) => {
      const newNotification = JSON.parse(event.data) as Notification;
      setNotifications((prev) => [newNotification, ...prev]);
      toast.info(`New notification: ${newNotification.content}`);
    };

    ws.onclose = () => {
      console.log('Notifications WebSocket disconnected');
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    setSocket(ws);

    return () => {
      ws.close();
    };
  }, [isAuthenticated]);

  const markAsRead = useCallback((notificationId: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === notificationId ? { ...n, read: true } : n))
    );
    // Here you would also call an API endpoint to mark it as read in the backend
  }, []);

  const markAllAsRead = useCallback(() => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
    // API call to mark all as read
  }, []);

  const unreadCount = notifications.filter((n) => !n.read).length;

  return (
    <NotificationContext.Provider value={{ notifications, unreadCount, markAsRead, markAllAsRead }}>
      {children}
    </NotificationContext.Provider>
  );
};

export const useNotifications = () => {
  const context = useContext(NotificationContext);
  if (context === undefined) {
    throw new Error('useNotifications must be used within a NotificationProvider');
  }
  return context;
};
