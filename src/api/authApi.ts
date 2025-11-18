import api from "@/lib/api";
import { User, UserCredentials, UserRegistration } from "../types";

export const register = async (userData: UserRegistration): Promise<User> => {
  const response = await api.post("/auth/register", userData);
  return response.data;
};

export const login = async (credentials: UserCredentials): Promise<{ message: string }> => {
  const payload = new URLSearchParams();
  payload.append('username', credentials.email);
  payload.append('password', credentials.password);

  const response = await api.post("/auth/token", payload, {
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
  const response = await api.get("/auth/me");
  return response.data;
};

export default { register, login, logout, getCurrentUser };
