// src/pages/Register.tsx
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import InputField from "../components/InputField";
import Button from "../components/Button";
import AuthFormContainer from "../components/AuthFormContainer";
import { register } from "../services/auth.service";

export default function Register() {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (password !== confirmPassword) {
            alert("As senhas não coincidem");
            return;
        }
        setLoading(true);
        try {
            await register({ email, password });
            alert("Registro realizado com sucesso!");
            navigate("/login");
        } catch (error) {
            console.error(error);
            alert("Falha no registro. Tente novamente.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <AuthFormContainer title="Criar Conta">
            <form onSubmit={handleSubmit} className="space-y-6">
                <InputField
                    label="Email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    required
                    autoFocus
                />
                <InputField
                    label="Senha"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    minLength={6}
                />
                <InputField
                    label="Confirmar Senha"
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    required
                    minLength={6}
                />
                <Button type="submit" disabled={loading} fullWidth>
                    {loading ? "Registrando..." : "Registrar"}
                </Button>
                <div className="text-center text-sm text-gray-500">
                    Já tem uma conta?{" "}
                    <Link to="/login" className="text-blue-600 hover:underline">
                        Faça login
                    </Link>
                </div>
            </form>
        </AuthFormContainer>
    );
}