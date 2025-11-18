
import axios from "axios";
import { User, UserCredentials, UserRegistration } from "../types";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const authApi = axios.create({
  baseURL: `${API_URL}/auth`,
  withCredentials: true,
});

export const register = async (userData: UserRegistration): Promise<User> => {
  const response = await authApi.post("/register", userData);
  return response.data;
};

export const login = async (credentials: UserCredentials): Promise<{ message: string }> => {
  const payload = new URLSearchParams();
  payload.append('username', credentials.email);
  payload.append('password', credentials.password);

  const response = await authApi.post("/token", payload, {
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
  });

  return response.data;
};

export const logout = () => {
  // Sessão é controlada por cookies httpOnly; não há token local para limpar
};

export const getCurrentUser = async (): Promise<User> => {
  const response = await authApi.get("/me");
  return response.data;
};

export default authApi;
