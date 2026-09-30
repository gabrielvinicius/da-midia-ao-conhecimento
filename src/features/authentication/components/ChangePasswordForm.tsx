import * as React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { useChangePassword } from '../hooks/useAuthMutations';

const changePasswordSchema = z.object({
  old_password: z.string().min(1, { message: 'Informe a senha atual' }),
  new_password: z.string().min(8, { message: 'A nova senha precisa ter pelo menos 8 caracteres' }),
  confirm_password: z.string(),
}).refine((data) => data.new_password === data.confirm_password, {
  message: 'As senhas não coincidem',
  path: ["confirm_password"], // Set the error on the confirmation field
});

type ChangePasswordFormValues = z.infer<typeof changePasswordSchema>;

export const ChangePasswordForm = () => {
  const { mutate: changePassword, isPending } = useChangePassword();

  const form = useForm<ChangePasswordFormValues>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: {
      old_password: '',
      new_password: '',
      confirm_password: '',
    },
  });

  const onSubmit = (data: ChangePasswordFormValues) => {
    changePassword({ old_password: data.old_password, new_password: data.new_password });
  };

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="old_password">Senha atual</Label>
        <Input id="old_password" type="password" {...form.register('old_password')} disabled={isPending} />
        {form.formState.errors.old_password && <p className="text-sm text-destructive">{form.formState.errors.old_password.message}</p>}
      </div>
      <div className="space-y-2">
        <Label htmlFor="new_password">Nova senha</Label>
        <Input id="new_password" type="password" {...form.register('new_password')} disabled={isPending} />
        {form.formState.errors.new_password && <p className="text-sm text-destructive">{form.formState.errors.new_password.message}</p>}
      </div>
      <div className="space-y-2">
        <Label htmlFor="confirm_password">Confirme a nova senha</Label>
        <Input id="confirm_password" type="password" {...form.register('confirm_password')} disabled={isPending} />
        {form.formState.errors.confirm_password && <p className="text-sm text-destructive">{form.formState.errors.confirm_password.message}</p>}
      </div>
      <Button type="submit" className="w-full" disabled={isPending}>
        {isPending ? 'Salvando...' : 'Trocar senha'}
      </Button>
    </form>
  );
};
