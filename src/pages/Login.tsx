// src/pages/Login.tsx
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import InputField from "../components/InputField";
import Button from "../components/Button";
import AuthFormContainer from "../components/AuthFormContainer";
import { login } from "@/services/auth.service";

export default function Login() {
    const [username, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const data = await login({ username, password });
            localStorage.setItem("token", data.access_token);
            navigate("/user");
        } catch (error) {
            console.error(error);
            alert("Credenciais inválidas ou erro de conexão.");
        }
    };

    return (
        <AuthFormContainer title="Login">
            <form onSubmit={handleSubmit} className="space-y-6">
                <InputField
                    label="Email"
                    type="email"
                    value={username}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                />
                <InputField
                    label="Senha"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                />
                <Button type="submit" fullWidth>
                    Entrar
                </Button>
                <div className="text-center text-sm text-gray-500">
                    Não tem conta?{" "}
                    <Link to="/register" className="text-blue-600 hover:underline">
                        Registre-se
                    </Link>
                </div>
            </form>
        </AuthFormContainer>
    );
}