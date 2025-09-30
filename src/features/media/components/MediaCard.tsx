import { Link } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/Card";
import { Badge } from "../../../components/ui/Badge"; // I will create this component next
import { Media, MediaStatus } from "../../../types";
import { File, Clock, CheckCircle, XCircle, Loader } from "lucide-react";

interface MediaCardProps {
  media: Media;
}

const statusConfig = {
  [MediaStatus.PENDING]: { icon: <Clock className="h-4 w-4" />, color: "bg-yellow-500" },
  [MediaStatus.PROCESSING]: { icon: <Loader className="h-4 w-4 animate-spin" />, color: "bg-blue-500" },
  [MediaStatus.COMPLETED]: { icon: <CheckCircle className="h-4 w-4" />, color: "bg-green-500" },
  [MediaStatus.FAILED]: { icon: <XCircle className="h-4 w-4" />, color: "bg-red-500" },
};

export const MediaCard = ({ media }: MediaCardProps) => {
  const { icon, color } = statusConfig[media.status] || statusConfig[MediaStatus.PENDING];

  return (
    <Link to={`/media/${media.id}`}>
      <Card className="hover:shadow-lg transition-shadow duration-200">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg truncate">
            <File className="h-5 w-5 flex-shrink-0" />
            <span className="truncate">{media.original_file_path}</span>
          </CardTitle>
        </CardHeader>
        <CardContent className="flex justify-between items-center">
          <Badge variant="secondary">{media.media_type}</Badge>
          <div className="flex items-center gap-2">
            <div className={`h-2 w-2 rounded-full ${color}`} />
            <span className="text-sm text-muted-foreground capitalize">{media.status.toLowerCase()}</span>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
};
