import { Link } from "react-router-dom";
import { BrandHeader } from "@/components/Brand";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { LoginForm } from "../features/authentication/components/LoginForm";
import { useAuthOptions } from "../features/authentication/hooks/useAuthOptions";

const LoginPage = () => {
  const { data: options } = useAuthOptions();
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-white px-4 py-12">
      <BrandHeader />
      <Card className="w-full max-w-md border border-[#ede4d5] bg-white">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Entrar</CardTitle>
          <CardDescription>Digite seu email abaixo para acessar sua conta</CardDescription>
        </CardHeader>
        <CardContent>
          <LoginForm />
          {options?.email_enabled && (
            <p className="mt-3 text-center text-sm">
              <Link to="/esqueci-a-senha" className="text-slate-600 underline-offset-2 hover:underline">
                Esqueci minha senha
              </Link>
            </p>
          )}
          <div className="mt-4 text-center text-sm">
            Não tem uma conta?{" "}
            <Link to="/register" className="underline">
              Cadastre-se
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
};

export default LoginPage;
