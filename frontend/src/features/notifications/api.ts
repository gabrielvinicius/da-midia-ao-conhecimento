import api from "@/lib/api";
import type { Notification } from "@/types";

// Mesmo formato das mensagens do WebSocket ({ kind, payload }.payload).
export const listNotifications = async (options: { limit?: number; unread?: boolean } = {}): Promise<Notification[]> =>
  (await api.get<Notification[]>("/notifications/", { params: { limit: options.limit, unread: options.unread || undefined } })).data;

export const markNotificationAsRead = async (id: string): Promise<void> => {
  await api.post(`/notifications/${id}/read`);
};

export const markAllNotificationsAsRead = async (): Promise<void> => {
  await api.post("/notifications/read-all");
};
