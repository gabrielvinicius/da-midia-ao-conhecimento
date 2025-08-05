import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import InputField from "../components/InputField";
import Button from "../components/Button";
import AuthFormContainer from "../components/AuthFormContainer";

export default function Login() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            const response = await fetch("/auth/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, password }),
            });
            if (response.ok) {
                const data = await response.json();
                localStorage.setItem("token", data.access_token);
                navigate("/user");
            } else {
                alert("Credenciais inválidas.");
            }
        } catch (error) {
            console.error(error);
            alert("Erro ao conectar ao servidor.");
        }
    };

    return (
        <AuthFormContainer title="Login">
            <form onSubmit={handleSubmit} className="space-y-6">
                <InputField label="Email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
                <InputField label="Senha" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
                <Button type="submit" fullWidth>Entrar</Button>
                <div className="text-center text-sm text-gray-500">
                    Não tem conta? <Link to="/register" className="text-blue-600 hover:underline">Registre-se</Link>
                </div>
            </form>
        </AuthFormContainer>
    );
}