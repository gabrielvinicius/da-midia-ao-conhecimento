// src/pages/Login.tsx
import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import InputField from '../components/InputField';
import Button from '../components/Button';
import AuthFormContainer from '../components/AuthFormContainer';

const login = async ({ email, password }: { email: string; password: string }) => {
    const response = await api.post('/auth/login', { email, password });
    return response.data;
};

export default function Login() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const navigate = useNavigate();

    const { mutate, isPending, error } = useMutation({
        mutationFn: login,
        onSuccess: (data) => {
            localStorage.setItem('token', data.access_token);
            navigate('/user');
        },
        onError: () => {
            alert('Credenciais inválidas.');
        },
    });

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        mutate({ email, password });
    };

    return (
        <AuthFormContainer title="Login">
            <form onSubmit={handleSubmit} className="space-y-6">
                <InputField
                    label="Email"
                    type="email"
                    value={email}
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
                {error && <p className="text-red-500 text-sm">Falha na autenticação.</p>}
                <Button type="submit" fullWidth disabled={isPending}>
                    {isPending ? 'Entrando...' : 'Entrar'}
                </Button>
                <div className="text-center text-sm text-gray-500">
                    Não tem conta?{' '}
                    <Link to="/register" className="text-blue-600 hover:underline">
                        Registre-se
                    </Link>
                </div>
            </form>
        </AuthFormContainer>
    );
}