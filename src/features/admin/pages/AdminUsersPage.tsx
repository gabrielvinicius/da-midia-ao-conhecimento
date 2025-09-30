import * as React from "react";
import { ColumnDef, PaginationState } from "@tanstack/react-table";
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
  const [{ pageIndex, pageSize }, setPagination] = React.useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  });
  const [search, setSearch] = React.useState('');

  const { data, isLoading, isError } = useAllUsers({
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
    return <p className="text-destructive">Error loading users.</p>;
  }

  return (
    <div>
      <h1 className="text-3xl font-bold tracking-tight mb-6">Users</h1>
      {isLoading && !data ? (
        <div className="space-y-4">
          <Skeleton className="h-12 w-1/3" />
          <Skeleton className="h-48 w-full" />
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={data?.items ?? defaultData}
          pageCount={data?.total_pages ?? 0}
          pagination={pagination}
          onPaginationChange={setPagination}
          onSearchChange={setSearch}
        />
      )}
    </div>
  );
};
