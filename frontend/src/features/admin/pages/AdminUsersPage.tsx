import * as React from "react";
import { ColumnDef, PaginationState } from "@tanstack/react-table";
import { MoreHorizontal } from "lucide-react";

import { User, UserRole } from "@/types";
import { useAllUsers } from "../hooks/useAdminQueries";
import { useDeleteUser, useSetUserActive } from "../hooks/useAdminMutations";
import { useAuth } from "@/contexts/AuthContext";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import ErrorState from "@/components/ui/ErrorState";
import { Button } from "@/components/ui/Button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/DropdownMenu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/AlertDialog";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/Dialog";
import { EditUserForm } from "../components/EditUserForm";

// Action Cell Component
const UserActionsCell = ({ user }: { user: User }) => {
  const { mutate: deleteUser, isPending: isDeleting } = useDeleteUser();
  const { mutate: setActive, isPending: isSwitching } = useSetUserActive();
  const { user: me } = useAuth();
  const isMe = me?.id === user.id;
  const [isEditOpen, setIsEditOpen] = React.useState(false);
  const [isDeleteOpen, setIsDeleteOpen] = React.useState(false);

  return (
    <>
      <Dialog open={isEditOpen} onOpenChange={setIsEditOpen}>
        <AlertDialog open={isDeleteOpen} onOpenChange={setIsDeleteOpen}>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="h-8 w-8 p-0">
                <span className="sr-only">Abrir menu</span>
                <MoreHorizontal className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>Ações</DropdownMenuLabel>
              <DialogTrigger asChild>
                <DropdownMenuItem>Alterar papel</DropdownMenuItem>
              </DialogTrigger>
              {/* Ninguém desativa nem remove a própria conta por aqui. */}
              <DropdownMenuItem
                disabled={isMe || isSwitching}
                onSelect={() => setActive({ userId: user.id, active: !user.is_active })}
              >
                {user.is_active ? "Desativar conta" : "Reativar conta"}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem className="text-red-600" onSelect={() => setIsDeleteOpen(true)} disabled={isMe || isDeleting}>
                Excluir conta
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Edit Dialog */}
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Papel de {user.email}</DialogTitle>
            </DialogHeader>
            <EditUserForm user={user} onFinished={() => setIsEditOpen(false)} />
          </DialogContent>

          {/* Delete Alert Dialog */}
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Excluir a conta {user.email}?</AlertDialogTitle>
              <AlertDialogDescription>
                A conta é apagada junto com todas as mídias dela, com transcrições, resumos e análises. Não é possível
                desfazer. Para só impedir o acesso, desative a conta.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction onClick={() => deleteUser(user.id)} className="bg-red-600 hover:bg-red-700">
                {isDeleting ? "Removendo..." : "Excluir"}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </Dialog>
    </>
  );
};

// Antes: o id (UUID) ocupava a primeira coluna e o papel aparecia cru ("ADMIN").
export const columns: ColumnDef<User>[] = [
  {
    accessorKey: "email",
    header: "E-mail",
    cell: ({ row }) => <span className="wrap-anywhere">{row.original.email}</span>,
  },
  {
    accessorKey: "role",
    header: "Papel",
    cell: ({ row }) => {
      const admin = row.original.role === UserRole.ADMIN;
      return <Badge variant={admin ? "default" : "secondary"}>{admin ? "Administrador" : "Usuário"}</Badge>;
    },
  },
  {
    accessorKey: "is_active",
    header: "Situação",
    cell: ({ row }) =>
      row.original.is_active === false ? (
        <span className="text-sm font-medium text-rose-700">Desativada</span>
      ) : (
        <span className="text-sm text-emerald-700">Ativa</span>
      ),
  },
  {
    id: "actions",
    cell: ({ row }) => <UserActionsCell user={row.original} />,
  },
];

export const AdminUsersPage = () => {
  const [{ pageIndex, pageSize }, setPagination] = React.useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  });
  const [search, setSearch] = React.useState('');

  const { data, isLoading, isError, refetch } = useAllUsers({
    page: pageIndex + 1, // API is 1-indexed
    limit: pageSize,
    search,
  });

  const defaultData = React.useMemo(() => [], []);

  const pagination = React.useMemo(
    () => ({ pageIndex, pageSize }),
    [pageIndex, pageSize]
  );

  if (isError) {
    return (
      <ErrorState
        title="Erro ao carregar usuários"
        message="Tente novamente em instantes."
        onRetry={() => refetch()}
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Usuários</h1>
        <p className="text-sm text-muted-foreground">Papéis, contas desativadas e exclusão de contas.</p>
      </div>
      {isLoading && !data ? (
        <div className="space-y-4">
          <Skeleton className="h-12 w-1/3" />
          <Skeleton className="h-48 w-full" />
        </div>
      ) : (
        <Card className="border border-[#ede4d5] bg-white">
          <CardHeader>
            <CardTitle className="text-base font-semibold">Lista de usuários</CardTitle>
            <CardDescription>Busque pelo e-mail.</CardDescription>
          </CardHeader>
          <CardContent>
            <DataTable
              columns={columns}
              data={data?.items ?? defaultData}
              pageCount={data?.pages ?? 0}
              pagination={pagination}
              onPaginationChange={setPagination}
              onSearchChange={setSearch}
            />
          </CardContent>
        </Card>
      )}
    </div>
  );
};
