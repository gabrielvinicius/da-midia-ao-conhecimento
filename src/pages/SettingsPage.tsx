import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { ChangePasswordForm } from "@/features/authentication/components/ChangePasswordForm";

const SettingsPage = () => {
  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold tracking-tight">Configurações</h1>
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <CardTitle>Trocar senha</CardTitle>
          <CardDescription>
            Depois da troca, por segurança, será preciso entrar de novo com a nova senha.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ChangePasswordForm />
        </CardContent>
      </Card>
    </div>
  );
};

export default SettingsPage;
