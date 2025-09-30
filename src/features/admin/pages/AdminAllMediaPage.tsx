import { ColumnDef } from "@tanstack/react-table";
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
  const { data: media, isLoading, isError } = useAllMedia();

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-1/4" />
        <Skeleton className="h-48 w-full" />
      </div>
    );
  }

  if (isError) {
    return <p className="text-destructive">Error loading media.</p>;
  }

  return (
    <div>
      <h1 className="text-3xl font-bold tracking-tight mb-6">All Media</h1>
      <DataTable columns={columns} data={media ?? []} />
    </div>
  );
};
