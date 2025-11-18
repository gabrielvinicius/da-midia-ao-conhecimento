import api from "@/lib/api";
import { Media } from "../types";

export const uploadMedia = async (file: File, storageProvider: string): Promise<Media> => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post(`/media/?storage_provider=${storageProvider}`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export const listMedia = async (): Promise<Media[]> => {
  const response = await api.get("/media/");
  return response.data;
};

export const getMediaById = async (id: string): Promise<Media> => {
  const response = await api.get(`/media/${id}`);
  return response.data;
};

export const reprocessMedia = async (id: string): Promise<{ message: string }> => {
  const response = await api.post(`/media/${id}/reprocess`);
  return response.data;
};

export default { uploadMedia, listMedia, getMediaById, reprocessMedia };
