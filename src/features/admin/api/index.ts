import api from "../../../lib/api";
import { User, Media } from "../../../types";

// Placeholder for stats response type
export interface SystemStats {
  total_users: number;
  total_media: number;
  processing_media: number;
}

export const getSystemStats = async (): Promise<SystemStats> => {
  const response = await api.get<SystemStats>("/admin/stats");
  return response.data;
};

export const getAllUsers = async (): Promise<User[]> => {
  const response = await api.get<User[]>("/admin/users");
  return response.data;
};

export const getAllMedia = async (): Promise<Media[]> => {
  const response = await api.get<Media[]>("/admin/media");
  return response.data;
};
