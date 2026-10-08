import * as React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';

import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';
import { Label } from '../../../components/ui/Label';
import { useLogin } from '../hooks/useAuthMutations';
import { resendVerification } from '../api';
import { apiErrorMessage, apiErrorStatus } from '@/lib/errors';
import { UserCredentials } from '../../../types';

const loginSchema = z.object({
  email: z.string().email({ message: 'Endereço de email inválido' }),
  password: z.string().min(1, { message: 'Senha é obrigatória' }),
});

export const LoginForm = () => {
  const { mutate: login, isPending, error } = useLogin();
  const [resent, setResent] = React.useState(false);
  // 403: senha certa, mas o e-mail do cadastro ainda não foi confirmado.
  const unverified = apiErrorStatus(error) === 403;

  const form = useForm<UserCredentials>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
    },
  });

  const onSubmit = (data: UserCredentials) => {
    login(data);
  };

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="email">Email</Label>
        <Input
          id="email"
          type="email"
          placeholder="seu@email.com"
          {...form.register('email')}
          disabled={isPending}
        />
        {form.formState.errors.email && (
          <p className="text-sm text-destructive">{form.formState.errors.email.message}</p>
        )}
      </div>
      <div className="space-y-2">
        <Label htmlFor="password">Senha</Label>
        <Input
          id="password"
          type="password"
          placeholder="Digite sua senha"
          {...form.register('password')}
          disabled={isPending}
        />
        {form.formState.errors.password && (
          <p className="text-sm text-destructive">{form.formState.errors.password.message}</p>
        )}
      </div>
      {unverified && (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-900" role="alert">
          <p>{apiErrorMessage(error, 'Confirme seu e-mail antes de entrar.')}</p>
          <button
            type="button"
            disabled={resent}
            onClick={async () => {
              await resendVerification(form.getValues('email')).catch(() => undefined);
              setResent(true);
            }}
            className="mt-1 font-medium underline-offset-2 hover:underline disabled:no-underline disabled:opacity-70"
          >
            {resent ? 'Link reenviado: confira seu e-mail.' : 'Reenviar o link de confirmação'}
          </button>
        </div>
      )}
      <Button type="submit" className="w-full" disabled={isPending}>
        {isPending ? 'Entrando...' : 'Entrar'}
      </Button>
    </form>
  );
};
