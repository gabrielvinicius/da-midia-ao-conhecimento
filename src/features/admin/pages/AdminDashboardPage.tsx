import { Users, FolderKanban, Loader2 } from "lucide-react";
import { StatCard } from "../components/StatCard";
import { useSystemStats } from "../hooks/useAdminQueries";

export const AdminDashboardPage = () => {
  const { data: stats, isLoading } = useSystemStats();

  return (
    <div>
      <h1 className="text-3xl font-bold tracking-tight mb-6">Admin Dashboard</h1>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <StatCard
          title="Total Users"
          value={stats?.total_users ?? 0}
          icon={<Users className="h-4 w-4 text-muted-foreground" />}
          isLoading={isLoading}
        />
        <StatCard
          title="Total Media Files"
          value={stats?.total_media ?? 0}
          icon={<FolderKanban className="h-4 w-4 text-muted-foreground" />}
          isLoading={isLoading}
        />
        <StatCard
          title="Currently Processing"
          value={stats?.processing_media ?? 0}
          icon={<Loader2 className="h-4 w-4 text-muted-foreground" />}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
};
