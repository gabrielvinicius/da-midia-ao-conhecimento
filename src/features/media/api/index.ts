import api from "@/lib/api";
import { Media } from "@/types";

export interface UploadMediaParams {
  file: File;
  storageProvider: string;
  transcriptionProvider?: string;
  summarizationProvider?: string;
}

export const listMedia = async (): Promise<Media[]> => {
  const response = await api.get<Media[]>("/media/");
  return response.data;
};

export const getMediaById = async (id: string): Promise<Media> => {
  const response = await api.get<Media>(`/media/${id}`);
  return response.data;
};

export const uploadMedia = async (params: UploadMediaParams): Promise<Media> => {
  const { file, ...queryParams } = params;
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post<Media>("/media/", formData, {
    params: queryParams,
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};
