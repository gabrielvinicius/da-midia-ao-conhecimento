import api from "./api";
import { Notification } from "../types";

export const getUserNotifications = async (): Promise<Notification[]> => {
    const response = await api.get("/notifications/me");
    return response.data;
};

export const markAsRead = async (id: string): Promise<Notification> => {
    const response = await api.patch(`/notifications/${id}/read`);
    return response.data;
};

export const deleteNotification = async (id: string): Promise<boolean> => {
    const response = await api.delete(`/notifications/${id}`);
    return response.status === 204;
};