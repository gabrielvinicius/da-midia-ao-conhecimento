
import axios from "axios";
import { Media } from "../types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const mediaApi = axios.create({
  baseURL: `${API_URL}/media`,
});

mediaApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const uploadMedia = async (file: File, storageProvider: string): Promise<Media> => {
  const formData = new FormData();
  formData.append("file", file);

  const response = await mediaApi.post(`/?storage_provider=${storageProvider}`, formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export const listMedia = async (): Promise<Media[]> => {
  const response = await mediaApi.get("/");
  return response.data;
};

export const getMediaById = async (id: string): Promise<Media> => {
  const response = await mediaApi.get(`/${id}`);
  return response.data;
};

export default mediaApi;
