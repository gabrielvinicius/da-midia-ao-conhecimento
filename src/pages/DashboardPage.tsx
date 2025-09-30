import { Link } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Skeleton } from "../components/ui/Skeleton"; // I will create this component next
import { MediaCard } from "../features/media/components/MediaCard";
import { useMediaList } from "../features/media/hooks/useMedia";
import { Upload } from "lucide-react";

const DashboardPage = () => {
  const { data: media, isLoading, isError, error } = useMediaList();

  const renderContent = () => {
    if (isLoading) {
      return (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      );
    }

    if (isError) {
      return (
        <div className="text-center text-destructive">
          <p>Error loading media: {error.message}</p>
        </div>
      );
    }

    if (!media || media.length === 0) {
      return (
        <div className="text-center py-16 border-2 border-dashed rounded-lg">
          <h3 className="text-xl font-semibold">No media found</h3>
          <p className="text-muted-foreground mt-2 mb-4">Upload your first media file to get started.</p>
          <Button asChild>
            <Link to="/upload">
              <Upload className="mr-2 h-4 w-4" /> Upload Media
            </Link>
          </Button>
        </div>
      );
    }

    return (
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
        {media.map((item) => (
          <MediaCard key={item.id} media={item} />
        ))}
      </div>
    );
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
      </div>
      {renderContent()}
    </div>
  );
};

export default DashboardPage;
