import * as React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';

import { Button } from "@/components/ui/Button";
import { Label } from "@/components/ui/Label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";
import { useUpdateUser } from '../hooks/useAdminMutations';
import { User, UserRole } from '@/types';

const updateUserSchema = z.object({
  role: z.nativeEnum(UserRole),
});

type UpdateUserFormValues = z.infer<typeof updateUserSchema>;

interface EditUserFormProps {
  user: User;
  onFinished: () => void; // Callback to close the dialog on success
}

export const EditUserForm = ({ user, onFinished }: EditUserFormProps) => {
  const { mutate: updateUser, isPending } = useUpdateUser();

  const form = useForm<UpdateUserFormValues>({
    resolver: zodResolver(updateUserSchema),
    defaultValues: {
      role: user.role,
    },
  });

  const onSubmit = (data: UpdateUserFormValues) => {
    updateUser({ userId: user.id, payload: data }, {
      onSuccess: () => {
        onFinished(); // Close the dialog
      }
    });
  };

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="role">Perfil</Label>
        <Select
          defaultValue={user.role}
          onValueChange={(value) => form.setValue('role', value as UserRole)}
          disabled={isPending}
        >
          <SelectTrigger id="role">
            <SelectValue placeholder="Escolha o perfil" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={UserRole.USER}>Usuário</SelectItem>
            <SelectItem value={UserRole.ADMIN}>Administrador</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <Button type="submit" className="w-full" disabled={isPending}>
        {isPending ? 'Salvando...' : 'Salvar'}
      </Button>
    </form>
  );
};
