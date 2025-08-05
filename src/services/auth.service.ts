// src/services/auth.service.ts
import api from "./api";

interface LoginData {
    email: string;
    password: string;
}

interface RegisterData {
    email: string;
    password: string;
}

export const login = async ( data: LoginData) => {
    const response = await api.post("/auth/login", data);
    return response.data;
};

export const register = async ( data: RegisterData) => {
    const response = await api.post("/auth/register", data);
    return response.data;
};

export const getCurrentUser = async () => {
    const response = await api.get("/auth/me");
    return response.data;
};

export const logout = async () => {
    await api.post("/auth/logout");
    return true;
};