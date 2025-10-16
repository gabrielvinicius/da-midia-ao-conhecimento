
import axios from "axios";
import { User, UserCredentials, UserRegistration } from "../types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const authApi = axios.create({
  baseURL: `${API_URL}/auth`,
});

export const register = async (userData: UserRegistration): Promise<User> => {
  const response = await authApi.post("/register", userData);
  return response.data;
};

export const login = async (credentials: UserCredentials): Promise<{ access_token: string }> => {
  const response = await authApi.post("/token/legacy", {
    username: credentials.email,
    password: credentials.password,
  });
  if (response.data.access_token && response.data.access_token !== "set_in_cookie") {
    localStorage.setItem("token", response.data.access_token);
  }
  return response.data;
};

export const logout = () => {
  localStorage.removeItem("token");
};

export const getCurrentUser = async (): Promise<User> => {
  const token = localStorage.getItem("token");
  const response = await authApi.get("/me", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.data;
};

authApi.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default authApi;
