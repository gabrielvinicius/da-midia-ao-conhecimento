import api from "@/lib/api";
import { User, Media, PaginatedResponse, UserRole } from "@/types";

export interface SystemStats {
  total_users: number;
  total_media: number;
  processing_media: number;
}

export interface GetPaginatedDataParams {
  page?: number;
  limit?: number;
  search?: string;
}

export interface UserUpdatePayload {
  role?: UserRole;
}

export const getSystemStats = async (): Promise<SystemStats> => {
  const response = await api.get<SystemStats>("/admin/stats");
  return response.data;
};

export const getAllUsers = async ({ page = 1, limit = 10, search = '' }: GetPaginatedDataParams): Promise<PaginatedResponse<User>> => {
  const response = await api.get<PaginatedResponse<User>>("/admin/users", {
    params: { page, limit, search },
  });
  return response.data;
};

export const getAllMedia = async ({ page = 1, limit = 10, search = '' }: GetPaginatedDataParams): Promise<PaginatedResponse<Media>> => {
  const response = await api.get<PaginatedResponse<Media>>("/admin/media", {
    params: { page, limit, search },
  });
  return response.data;
};

export const deleteUser = async (userId: string): Promise<void> => {
  await api.delete(`/admin/users/${userId}`);
};

export const deleteMedia = async (mediaId: string): Promise<void> => {
  await api.delete(`/admin/media/${mediaId}`);
};

export const updateUser = async (userId: string, payload: UserUpdatePayload): Promise<User> => {
  const response = await api.put<User>(`/admin/users/${userId}`, payload);
  return response.data;
};

export const reprocessMedia = async (mediaId: string): Promise<{ message: string }> => {
  const response = await api.post(`/admin/media/${mediaId}/reprocess`);
  return response.data;
};
