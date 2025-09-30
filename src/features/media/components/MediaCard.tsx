import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/Card";
import { Badge } from "../../../components/ui/Badge";
import { Media, MediaStatus } from "../../../types";
import { FileText, CheckCircle, XCircle, Loader2, Clock } from "lucide-react";

interface MediaCardProps {
  media: Media;
}

// Status configuration for visual feedback
const statusConfig: Record<MediaStatus, { icon: React.ReactNode; color: string; label: string }> = {
  [MediaStatus.PENDING]: { icon: <Clock className="h-4 w-4" />, color: "text-yellow-500", label: "Pending" },
  [MediaStatus.PROCESSING]: { icon: <Loader2 className="h-4 w-4 animate-spin" />, color: "text-blue-500", label: "Processing" },
  [MediaStatus.COMPLETED]: { icon: <CheckCircle className="h-4 w-4" />, color: "text-green-500", label: "Completed" },
  [MediaStatus.FAILED]: { icon: <XCircle className="h-4 w-4" />, color: "text-red-500", label: "Failed" },
};

export const MediaCard = ({ media }: MediaCardProps) => {
  const { icon, color, label } = statusConfig[media.status] || statusConfig[MediaStatus.PENDING];

  return (
    <Link to={`/media/${media.id}`} className="block">
      <Card className="hover:border-primary/50 hover:shadow-md transition-all duration-200 h-full">
        <CardHeader>
          <CardTitle className="flex items-start gap-3 text-lg">
            <FileText className="h-5 w-5 flex-shrink-0 translate-y-0.5" />
            <span className="truncate flex-1">{media.original_file_path}</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex justify-between items-center">
          <Badge variant="secondary">{media.media_type}</Badge>
          <div className={`flex items-center gap-2 font-medium ${color}`}>
            {icon}
            <span className="text-sm capitalize">{label}</span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
};
