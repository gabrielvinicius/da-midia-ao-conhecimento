"use client";

import { useState } from "react";
import { api } from "@/lib/api";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function UploadPage() {
    const [file, setFile] = useState<File | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const router = useRouter();

    const handleUpload = async () => {
        if (!file) return;

        setLoading(true);
        setError("");

        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await api.post("/videos/", formData, {
                headers: {
                    "Content-Type": "multipart/form-data",
                },
            });

            router.push("/dashboard"); // ou `/videos/${response.data.id}` se quiser redirecionar direto
        } catch (err) {
            console.error("Erro no upload", err);
            setError("Erro ao enviar o vídeo. Tente novamente.");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="max-w-md mx-auto py-12">
            <h1 className="text-2xl font-bold mb-6">Enviar novo vídeo</h1>

            <div className="space-y-4">
                <div>
                    <Label htmlFor="file">Arquivo de vídeo</Label>
                    <Input
                        id="file"
                        type="file"
                        accept="video/*"
                        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                    />
                </div>

                {error && <p className="text-red-600">{error}</p>}

                <Button onClick={handleUpload} disabled={!file || loading}>
                    {loading ? "Enviando..." : "Enviar vídeo"}
                </Button>
            </div>
        </div>
    );
}
