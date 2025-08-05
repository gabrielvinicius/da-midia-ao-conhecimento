// src/services/auth.service.ts
import api from "./api";

interface LoginData {
    username: string;
    password: string;
}

interface RegisterData {
    email: string;
    password: string;
}

export const login = async ( data: LoginData) => {
    const params = new URLSearchParams();
    params.append("username", data.username);
    params.append("password", data.password);
    const response = await api.post("/auth/login", params, {
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
    });
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