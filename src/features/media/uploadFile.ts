// Regras do arquivo enviado, separadas do formulário para serem testadas.

// Mesmo limite do backend (media_max_file_size_bytes) e do nginx (client_max_body_size).
export const MAX_FILE_SIZE_MB = 500;
export const MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024;

// Espelha as extensões aceitas pelo backend (media_management/config/settings.py).
const VIDEO_EXTENSIONS = [".mp4", ".webm", ".mov", ".avi", ".mkv", ".flv"];
const AUDIO_EXTENSIONS = [".mp3", ".wav", ".m4a", ".flac", ".aac", ".ogg"];
const TEXT_EXTENSIONS = [".txt", ".pdf", ".docx", ".png", ".jpg", ".jpeg", ".tiff", ".bmp"];
export const ACCEPTED_EXTENSIONS = [...VIDEO_EXTENSIONS, ...AUDIO_EXTENSIONS, ...TEXT_EXTENSIONS];

export type UploadKind = "video" | "audio" | "text";

/** Como o arquivo será processado: vídeo e áudio são transcritos; documentos e
 *  imagens têm o texto extraído (com OCR). Pela extensão, como no backend. */
export function uploadKind(file: Pick<File, "name">): UploadKind | null {
  const name = file.name.toLowerCase();
  if (VIDEO_EXTENSIONS.some((ext) => name.endsWith(ext))) return "video";
  if (AUDIO_EXTENSIONS.some((ext) => name.endsWith(ext))) return "audio";
  if (TEXT_EXTENSIONS.some((ext) => name.endsWith(ext))) return "text";
  return null;
}

/** Mensagem de erro do arquivo, ou null se ele pode ser enviado. */
export function fileProblem(file: Pick<File, "name" | "size"> | undefined): string | null {
  if (!file) return "Arquivo é obrigatório.";
  if (file.size > MAX_FILE_SIZE) return `Tamanho máximo do arquivo é ${MAX_FILE_SIZE_MB} MB.`;
  if (!uploadKind(file)) {
    const ext = /\.[^.]+$/.exec(file.name)?.[0] ?? "";
    return `Tipo de arquivo não aceito${ext ? ` (${ext})` : ""}. Envie vídeo, áudio, PDF, DOCX, TXT ou imagem.`;
  }
  return null;
}

export function formatFileSize(bytes: number): string {
  if (bytes <= 0) return "0 Bytes";
  const units = ["Bytes", "KB", "MB", "GB"];
  const i = Math.min(units.length - 1, Math.floor(Math.log(bytes) / Math.log(1024)));
  return `${parseFloat((bytes / 1024 ** i).toFixed(2))} ${units[i]}`;
}

/** O que acontece com o arquivo depois do envio, nas palavras do usuário. */
export const PIPELINE_STEPS: Record<UploadKind, string> = {
  video: "transcrição da fala, descrição de quadros do vídeo, temas, tom, resumo e indexação para a busca",
  audio: "transcrição da fala, temas, tom, resumo e indexação para a busca",
  text: "extração do texto (com OCR em imagens e PDFs escaneados), temas, tom, resumo e indexação para a busca",
};
