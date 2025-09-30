import * as React from "react";
import { ColumnDef, PaginationState } from "@tanstack/react-table";
import { MoreHorizontal } from "lucide-react";
import { format } from "date-fns";

import { Media, MediaStatus } from "@/types";
import { useAllMedia } from "../hooks/useAdminQueries";
import { useDeleteMedia } from "../hooks/useAdminMutations";
import { DataTable } from "@/components/ui/DataTable";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { Button } from "@/components/ui/Button";
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
  AlertDialogTrigger,
} from "@/components/ui/AlertDialog";

// Action Cell Component for Media
const MediaActionsCell = ({ media }: { media: Media }) => {
  const { mutate: deleteMedia, isPending } = useDeleteMedia();

  return (
    <AlertDialog>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="h-8 w-8 p-0">
            <span className="sr-only">Open menu</span>
            <MoreHorizontal className="h-4 w-4" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel>Actions</DropdownMenuLabel>
          <DropdownMenuSeparator />
          <AlertDialogTrigger asChild>
            <DropdownMenuItem className="text-red-600" disabled={isPending}>
              Delete Media
            </DropdownMenuItem>
          </AlertDialogTrigger>
        </DropdownMenuContent>
      </DropdownMenu>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
          <AlertDialogDescription>
            This action cannot be undone. This will permanently delete the media record and its associated file from storage.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction onClick={() => deleteMedia(media.id)} className="bg-red-600 hover:bg-red-700">
            {isPending ? "Deleting..." : "Delete"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
};

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
  {
    id: "actions",
    cell: ({ row }) => <MediaActionsCell media={row.original} />,
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
