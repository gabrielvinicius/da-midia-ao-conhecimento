// src/app/videos/[id]/page.tsx
import { notFound } from "next/navigation";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import { Download, Loader2 } from "lucide-react";
import { cookies } from "next/headers";

interface VideoDetailsProps {
    params: { id: string };
}

const statusMap: Record<string, string> = {
    processing: "Processando",
    completed: "Concluído",
    failed: "Falhou",
    pending: "Pendente",
};

export default async function VideoDetailsPage({ params }: VideoDetailsProps) {
    const videoId = params.id;

    let video;
    try {
        // Usando fetch diretamente com autenticação via cookies
        const baseUrl = process.env.NEXT_PUBLIC_API_URL;
        const token = cookies().get('token')?.value;

        const response = await fetch(`${baseUrl}/videos/${videoId}`, {
            headers: {
                ...(token ? { Authorization: `Bearer ${token}` } : {}),
            },
            cache: 'no-store'
        });

        if (!response.ok) {
            if (response.status === 404) {
                return notFound();
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        video = await response.json();
    } catch (err) {
        console.error("Erro ao carregar detalhes do vídeo:", err);
        return notFound();
    }

    const {
        title,
        status,
        transcription,
        summary,
        audio_url,
        transcription_url,
        summary_url,
    } = video;

    const statusText = statusMap[status] || status;

    return (
        <div className="max-w-4xl mx-auto py-8 px-4 space-y-8">
            <div className="flex flex-col sm:flex-row justify-between items-start gap-4">
                <div>
                    <h1 className="text-2xl md:text-3xl font-bold break-words">{title}</h1>
                    <div className="flex flex-wrap gap-2 mt-2">
            <span className="px-3 py-1 bg-muted rounded-full text-xs">
              Status: {statusText}
            </span>

                        {status === "processing" && (
                            <span className="flex items-center gap-1 px-3 py-1 bg-yellow-500/20 rounded-full text-xs">
                <Loader2 className="h-3 w-3 animate-spin" />
                Processando
              </span>
                        )}

                        {status === "failed" && (
                            <span className="flex items-center gap-1 px-3 py-1 bg-destructive/20 rounded-full text-xs">
                Falha no processamento
              </span>
                        )}
                    </div>
                </div>

                <Button asChild variant="ghost" className="shrink-0">
                    <Link href="/">
                        ← Voltar para lista
                    </Link>
                </Button>
            </div>

            {status === "completed" ? (
                <div className="space-y-10">
                    {/* Seção de Transcrição */}
                    <section>
                        <div className="flex justify-between items-center mb-4">
                            <h2 className="text-xl font-semibold">Transcrição Completa</h2>
                            {transcription_url && (
                                <a
                                    href={transcription_url}
                                    download={`${title.replace(/[^a-z0-9]/gi, '_')}_transcricao.txt`}
                                >
                                    <Button variant="outline" size="sm">
                                        <Download className="mr-2 h-4 w-4" />
                                        Baixar TXT
                                    </Button>
                                </a>
                            )}
                        </div>

                        <div className="bg-muted p-4 rounded-lg max-h-[50vh] overflow-y-auto whitespace-pre-wrap break-words font-sans">
                            {transcription || "Transcrição não disponível."}
                        </div>
                    </section>

                    {/* Seção de Resumo */}
                    <section>
                        <div className="flex justify-between items-center mb-4">
                            <h2 className="text-xl font-semibold">Resumo</h2>
                            {summary_url && (
                                <a
                                    href={summary_url}
                                    download={`${title.replace(/[^a-z0-9]/gi, '_')}_resumo.txt`}
                                >
                                    <Button variant="outline" size="sm">
                                        <Download className="mr-2 h-4 w-4" />
                                        Baixar TXT
                                    </Button>
                                </a>
                            )}
                        </div>

                        <div className="bg-muted p-4 rounded-lg">
                            <p className="whitespace-pre-wrap">
                                {summary || "Resumo não disponível."}
                            </p>
                        </div>
                    </section>

                    {/* Seção de Downloads */}
                    <section>
                        <h2 className="text-xl font-semibold mb-4">Arquivos para Download</h2>
                        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                            <DownloadCard
                                title="Áudio Original"
                                description="Arquivo MP3"
                                url={audio_url}
                                fileName={`${title.replace(/[^a-z0-9]/gi, '_')}.mp3`}
                            />

                            <DownloadCard
                                title="Transcrição"
                                description="Texto completo"
                                url={transcription_url}
                                fileName={`${title.replace(/[^a-z0-9]/gi, '_')}_transcricao.txt`}
                            />

                            <DownloadCard
                                title="Resumo"
                                description="Versão resumida"
                                url={summary_url}
                                fileName={`${title.replace(/[^a-z0-9]/gi, '_')}_resumo.txt`}
                            />
                        </div>
                    </section>
                </div>
            ) : status === "failed" ? (
                <div className="bg-destructive/10 p-6 rounded-lg border border-destructive">
                    <h2 className="text-lg font-semibold mb-2">Falha no Processamento</h2>
                    <p className="mb-4">Ocorreu um erro ao processar seu vídeo. Por favor:</p>
                    <ul className="list-disc pl-5 mb-4 space-y-1">
                        <li>Verifique se o arquivo está em formato compatível</li>
                        <li>Tente novamente mais tarde</li>
                        <li>Entre em contato com o suporte caso o problema persista</li>
                    </ul>
                    <Button asChild>
                        <Link href="/upload">Tentar novamente</Link>
                    </Button>
                </div>
            ) : (
                <div className="text-center py-12">
                    <Loader2 className="mx-auto h-16 w-16 animate-spin text-primary mb-4" />
                    <h2 className="text-xl font-semibold mb-2">Processando seu vídeo</h2>
                    <p className="text-muted-foreground max-w-md mx-auto">
                        Esta operação pode levar alguns minutos. Você pode recarregar a página ou aguardar que atualizaremos automaticamente.
                    </p>
                    <Button className="mt-6" asChild>
                        <Link href={`/videos/${videoId}`}>
                            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                            Recarregar Agora
                        </Link>
                    </Button>
                </div>
            )}
        </div>
    );
}

// Componente para cards de download
function DownloadCard({
                          title,
                          description,
                          url,
                          fileName
                      }: {
    title: string;
    description: string;
    url?: string;
    fileName: string;
}) {
    return (
        <div className="border rounded-lg p-4 flex flex-col">
            <div className="flex-grow">
                <h3 className="font-medium">{title}</h3>
                <p className="text-sm text-muted-foreground">{description}</p>
            </div>
            <div className="mt-4">
                <a
                    href={url}
                    download={fileName}
                    className={!url ? "pointer-events-none opacity-50" : ""}
                >
                    <Button variant="outline" className="w-full" disabled={!url}>
                        <Download className="mr-2 h-4 w-4" />
                        Baixar
                    </Button>
                </a>
            </div>
        </div>
    );
}