
import axios from "axios";
import { Summary } from "../types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const summaryApi = axios.create({
  baseURL: `${API_URL}/summaries`,
});

summaryApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const getSummaryByMediaId = async (mediaId: string): Promise<Summary> => {
  const response = await summaryApi.get(`/?media_id=${mediaId}`);
  return response.data;
};

export default summaryApi;
