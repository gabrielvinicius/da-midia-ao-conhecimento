import { ColumnDef } from "@tanstack/react-table";
import { User } from "@/types";
import { useAllUsers } from "../hooks/useAdminQueries";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";

// Define the columns for the user table
export const columns: ColumnDef<User>[] = [
  {
    accessorKey: "id",
    header: "User ID",
  },
  {
    accessorKey: "email",
    header: "Email",
  },
  {
    accessorKey: "role",
    header: "Role",
    cell: ({ row }) => {
      const role = row.original.role;
      return <Badge variant={role === "ADMIN" ? "default" : "secondary"}>{role}</Badge>;
    },
  },
];

export const AdminUsersPage = () => {
  const { data: users, isLoading, isError } = useAllUsers();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-1/4" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (isError) {
    return <p className="text-destructive">Error loading users.</p>;
  }

  return (
    <div>
      <h1 className="text-3xl font-bold tracking-tight mb-6">Users</h1>
      <DataTable columns={columns} data={users ?? []} />
    </div>
  );
};
