import { BookOpen, FileText, Music, ScrollText, Search, ShieldCheck, Video } from "lucide-react";
import type { ReactNode } from "react";

import { UploadForm } from "@/features/media/components/UploadForm";

const KINDS: { icon: ReactNode; title: string; formats: string; steps: string }[] = [
  {
    icon: <Video className="h-4 w-4" />,
    title: "Vídeo",
    formats: "MP4, WebM, MOV, AVI, MKV, FLV",
    steps: "Transcrição da fala e descrição do que aparece na tela (slides, nomes, títulos).",
  },
  {
    icon: <Music className="h-4 w-4" />,
    title: "Áudio",
    formats: "MP3, WAV, M4A, FLAC, AAC, OGG",
    steps: "Transcrição da fala, com horário de cada trecho.",
  },
  {
    icon: <FileText className="h-4 w-4" />,
    title: "Documento ou imagem",
    formats: "PDF, DOCX, TXT, PNG, JPG, TIFF, BMP",
    steps: "Extração do texto, com OCR em imagens e PDFs escaneados.",
  },
];

const RESULTS: { icon: ReactNode; text: string }[] = [
  { icon: <ScrollText className="h-4 w-4" />, text: "Resumo adequado ao tipo de conteúdo (aula, palestra, reunião...), conferido contra a transcrição" },
  { icon: <BookOpen className="h-4 w-4" />, text: "Capítulos, perguntas de revisão, temas e tom" },
  { icon: <Search className="h-4 w-4" />, text: "Indexação para a busca por significado em todo o seu acervo" },
];

/**
 * Envio de mídias. Antes, a página prometia o que o sistema não faz
 * (identificação de quem fala), mostrava opções de armazenamento que o usuário
 * não escolhe e um botão de dicas sem ação; o envio era de um arquivo por vez.
 */
const UploadPage = () => (
  <div className="mx-auto w-full max-w-6xl space-y-6 pb-12">
    <header className="space-y-1">
      <h1 className="text-2xl font-semibold tracking-tight text-slate-950 sm:text-3xl">Enviar mídias</h1>
      <p className="text-slate-600">
        O envio termina em instantes; transcrição e análise seguem em segundo plano, e o sino avisa quando cada uma termina.
      </p>
    </header>

    <div className="grid gap-6 lg:grid-cols-[minmax(0,3fr)_minmax(0,2fr)]">
      <section className="min-w-0 rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
        <UploadForm />
      </section>

      <aside className="space-y-4">
        <section className="rounded-2xl border border-slate-200 bg-white p-5">
          <h2 className="mb-3 text-sm font-semibold text-slate-900">O que cada tipo recebe</h2>
          <ul className="space-y-3">
            {KINDS.map((kind) => (
              <li key={kind.title} className="flex gap-3">
                <span className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
                  {kind.icon}
                </span>
                <div className="text-sm">
                  <p className="font-medium text-slate-900">{kind.title}</p>
                  <p className="text-slate-600">{kind.steps}</p>
                  <p className="text-xs text-slate-400">{kind.formats}</p>
                </div>
              </li>
            ))}
          </ul>
          <h2 className="mb-3 mt-5 text-sm font-semibold text-slate-900">Depois, para todos</h2>
          <ul className="space-y-2">
            {RESULTS.map((item) => (
              <li key={item.text} className="flex gap-3 text-sm text-slate-600">
                <span className="mt-0.5 shrink-0 text-amber-600">{item.icon}</span>
                {item.text}
              </li>
            ))}
          </ul>
          <p className="mt-4 rounded-lg bg-slate-50 px-3 py-2 text-xs text-slate-500">
            Referência: uma aula em vídeo de 30 minutos leva cerca de 4 minutos para ficar pronta.
          </p>
        </section>

        <section className="rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-600">
          <h2 className="mb-2 text-sm font-semibold text-slate-900">Para um resultado melhor</h2>
          <ul className="list-disc space-y-1.5 pl-5">
            <li>Prefira gravações com o microfone perto de quem fala e pouco ruído.</li>
            <li>Envie PDFs com texto selecionável quando tiver: o OCR de escaneados é mais lento e erra mais.</li>
            <li>Uma aula ou reunião por arquivo: o resumo e os capítulos ficam mais claros.</li>
          </ul>
          <p className="mt-3 flex items-start gap-2 text-xs text-slate-500">
            <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />
            Tudo é processado neste servidor; nenhum arquivo é enviado a serviços externos.
          </p>
        </section>
      </aside>
    </div>
  </div>
);

export default UploadPage;
