import api from "../../../lib/api";
import { Notification } from "../../../types";

export const getNotifications = async (): Promise<Notification[]> => {
  const response = await api.get<Notification[]>("/notifications/");
  return response.data;
};

export const markNotificationAsRead = async (notificationId: string): Promise<Notification> => {
  const response = await api.post<Notification>(`/notifications/${notificationId}/read`);
  return response.data;
};
