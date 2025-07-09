import { VideoList } from "@/components/dashboard/video-list";

export default function DashboardPage() {
    return (
        <main className="p-6">
            <h1 className="text-2xl font-bold mb-4">Seus Vídeos</h1>
            <VideoList />
        </main>
    );
}
