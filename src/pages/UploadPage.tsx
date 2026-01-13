import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { UploadForm } from "@/features/media/components/UploadForm";
import { useAuth } from "@/contexts/AuthContext";
import { UploadCloud, Shield, Sparkles, HardDrive, Server } from "lucide-react";

const supportedMedia = [
  {
    label: "Vídeos",
    emoji: "🎥",
    formats: ".mp4, .webm, .mov, .avi, .mkv",
    pipeline: "Visão Computacional → Transcrição → Descoberta de Tópicos → Síntese Interpretativa",
    hint: "Reuniões, aulas e palestras com contexto visual",
    accent: "from-purple-700 via-purple-600 to-purple-800",
  },
  {
    label: "Áudios",
    emoji: "🎵",
    formats: ".mp3, .wav, .m4a, .flac",
    pipeline: "Diarização → Transcrição → Modelagem Semântica → Artigo Analítico",
    hint: "Podcasts, entrevistas e chamadas telefônicas",
    accent: "from-emerald-700 via-emerald-600 to-emerald-800",
  },
  {
    label: "Textos",
    emoji: "📄",
    formats: ".pdf, .txt",
    pipeline: "Extração Digital → Indexação Vetorial → Resumo Executivo",
    hint: "Documentos, artigos técnicos e relatórios longos",
    accent: "from-sky-700 via-sky-600 to-sky-800",
  },
];

const storageOptions = [
  {
    title: "Armazenamento local",
    icon: <Server className="h-5 w-5" />,
    location: "Diretório do servidor",
    perks: "Baixa latência, controle total e custo zero",
    ideal: "Ambientes de desenvolvimento ou dados sensíveis",
  },
  {
    title: "Nuvem (S3/MinIO)",
    icon: <HardDrive className="h-5 w-5" />,
    location: "Buckets distribuídos",
    perks: "Escalável, com backup automático e CDN",
    ideal: "Produção, grandes volumes e times distribuídos",
  },
];

const UploadPage = () => {
  const { user } = useAuth();
  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted/40 px-4 py-10">
      <div className="mx-auto flex w-full max-w-5xl flex-col gap-8">
        <section className="rounded-3xl border border-border/60 bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 p-6 text-white shadow-2xl">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-sm uppercase tracking-wide text-white/70">Central de uploads inteligentes</p>
              <h1 className="text-3xl font-semibold">Pronto para processar, {user?.email?.split("@")[0] ?? "criador"}?</h1>
              <p className="text-sm text-white/70">
                Arraste e solte ou selecione um arquivo. Nosso pipeline cuida da transcrição, resumo e análise para você.
              </p>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-2">
                <Sparkles className="h-4 w-4 text-amber-300" />
                <span>Suporte para vídeo, áudio e texto em um só fluxo.</span>
              </div>
              <div className="flex items-center gap-2">
                <Shield className="h-4 w-4 text-emerald-300" />
                <span>Processamento seguro com providers aprovados.</span>
              </div>
              <Button variant="secondary" size="sm" className="mt-2 inline-flex items-center gap-2">
                <UploadCloud className="h-4 w-4" />
                Dicas rápidas de upload
              </Button>
            </div>
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
          <Card className="border border-border/80 shadow-xl">
            <CardHeader>
              <CardTitle>Enviar nova mídia</CardTitle>
              <CardDescription>
                Selecione o arquivo, defina o tipo correto e escolha os providers conforme sua necessidade.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <UploadForm />
            </CardContent>
          </Card>
          <Card className="border-dashed border-primary/40 bg-primary/5">
            <CardHeader>
              <CardTitle>Dicas para um processamento perfeito</CardTitle>
              <CardDescription>Otimize seus uploads antes de enviar.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-muted-foreground">
              <p>• Use arquivos com áudio limpo ou texto legível para melhorar a transcrição.</p>
              <p>• Escolha apenas os providers necessários para acelerar o pipeline.</p>
              <p>• Acompanhe o status em tempo real no painel assim que o upload for concluído.</p>
            </CardContent>
          </Card>
        </section>

        <section className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-semibold">Tipos de mídia suportados</h2>
              <p className="text-sm text-muted-foreground">Cada tipo segue um pipeline especializado com providers recomendados.</p>
            </div>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {supportedMedia.map((type) => (
              <Card key={type.label} className={`border-none bg-gradient-to-br ${type.accent} text-white shadow-lg`}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <span>{type.emoji}</span>
                    {type.label}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-1 text-sm text-white/80">
                  <p><strong>Formatos:</strong> {type.formats}</p>
                  <p><strong>Pipeline:</strong> {type.pipeline}</p>
                  <p className="text-white">Ideal para: {type.hint}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        <section className="space-y-4">
          <div>
            <h2 className="text-2xl font-semibold">Opções de armazenamento</h2>
            <p className="text-sm text-muted-foreground">Escolha onde seus arquivos ficarão guardados antes e depois do processamento.</p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            {storageOptions.map((option) => (
              <Card key={option.title} className="border border-border/60 bg-background/80">
                <CardHeader className="flex flex-row items-center justify-between pb-2">
                  <CardTitle className="text-lg flex items-center gap-2">
                    <span className="rounded-full bg-muted p-2 text-primary">{option.icon}</span>
                    {option.title}
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 text-sm text-muted-foreground">
                  <p><strong>Localização:</strong> {option.location}</p>
                  <p><strong>Vantagens:</strong> {option.perks}</p>
                  <p className="text-primary font-medium">Ideal para: {option.ideal}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
};

export default UploadPage;
