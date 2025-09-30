import api from "../../../lib/api";
import { Media } from "../../../types";

export const listMedia = async (): Promise<Media[]> => {
  const response = await api.get<Media[]>("/media/");
  return response.data;
};

export const getMediaById = async (id: string): Promise<Media> => {
  const response = await api.get<Media>(`/media/${id}`);
  return response.data;
};

export const uploadMedia = async (file: File, storageProvider: string): Promise<Media> => {
  const formData = new FormData();
  formData.append("file", file);

  // The backend endpoint for upload is POST /media/?storage_provider=...
  const response = await api.post<Media>(`/media/?storage_provider=${storageProvider}`, formData, {
    headers: {
      // Axios will automatically set the correct Content-Type for FormData
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};
