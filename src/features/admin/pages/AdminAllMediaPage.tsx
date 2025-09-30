import * as React from "react";
import { ColumnDef, PaginationState } from "@tanstack/react-table";
import { Media, MediaStatus } from "@/types";
import { useAllMedia } from "../hooks/useAdminQueries";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { format } from "date-fns";

// Define the columns for the media table
export const columns: ColumnDef<Media>[] = [
  {
    accessorKey: "id",
    header: "Media ID",
  },
  {
    accessorKey: "user_id",
    header: "User ID",
  },
  {
    accessorKey: "original_file_path",
    header: "File Path",
  },
  {
    accessorKey: "media_type",
    header: "Type",
    cell: ({ row }) => <Badge variant="outline">{row.original.media_type}</Badge>,
  },
  {
    accessorKey: "status",
    header: "Status",
    cell: ({ row }) => {
      const status = row.original.status;
      let variant: "default" | "secondary" | "destructive" = "secondary";
      if (status === MediaStatus.COMPLETED) variant = "default";
      if (status === MediaStatus.FAILED) variant = "destructive";
      return <Badge variant={variant}>{status}</Badge>;
    },
  },
  {
    accessorKey: "created_at",
    header: "Created At",
    cell: ({ row }) => format(new Date(row.original.created_at), "PPP p"),
  },
];

export const AdminAllMediaPage = () => {
  const [{ pageIndex, pageSize }, setPagination] = React.useState<PaginationState>({
    pageIndex: 0,
    pageSize: 10,
  });
  const [search, setSearch] = React.useState('');

  const { data, isLoading, isError } = useAllMedia({
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
    return <p className="text-destructive">Error loading media.</p>;
  }

  return (
    <div>
      <h1 className="text-3xl font-bold tracking-tight mb-6">All Media</h1>
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
