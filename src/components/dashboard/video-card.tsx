import { format } from "date-fns";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import Link from "next/link";

type Props = {
    video: {
        id: string;
        title: string;
        created_at: string;
        status: "processing" | "completed" | "failed";
    };
};

const statusColorMap = {
    processing: "bg-yellow-200 text-yellow-800",
    completed: "bg-green-200 text-green-800",
    failed: "bg-red-200 text-red-800",
};

export function VideoCard({ video }: Props) {
    const statusStyle = statusColorMap[video.status] || "bg-gray-200 text-gray-800";

    return (
        <div className="rounded-2xl border p-4 shadow-sm space-y-2">
            <h2 className="text-lg font-semibold">{video.title}</h2>
            <p className="text-sm text-gray-500">
                Enviado em {format(new Date(video.created_at), "dd/MM/yyyy")}
            </p>
            <Badge className={statusStyle}>{video.status}</Badge>
            <div>
                <Link href={`/videos/${video.id}`}>
                    <Button variant="outline" size="sm">
                        Ver detalhes
                    </Button>
                </Link>
            </div>
        </div>
    );
}
