import * as React from 'react';
import { SubmitHandler, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { useQuery } from '@tanstack/react-query';

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";
import { useCreateMediaCommand } from '@/hooks/useCommands';
import { CreateMediaCommand } from '@/api/commands';
import { getProviders, ProvidersResponse } from '@/api/queries';

const MAX_FILE_SIZE = 200 * 1024 * 1024; // 200 MB (conforme configuração do backend)
const ACCEPTED_FILE_TYPES = [
  "video/mp4", "video/webm", "video/quicktime", "video/x-msvideo", "video/x-matroska",
  "audio/mpeg", "audio/wav", "audio/mp4", "audio/flac",
  "application/pdf", "text/plain"
];

const optionalProviderName = z.preprocess(
  (value) => {
    if (typeof value !== "string") return value;
    const trimmed = value.trim();
    return trimmed.length ? trimmed : undefined;
  },
  z.string().optional(),
);

const uploadSchema = z.object({
  storageProvider: z.string().min(1, "Provider de armazenamento é obrigatório.").default("local"),
  transcriptionProvider: optionalProviderName,
  summarizationProvider: optionalProviderName,
  sentimentProvider: optionalProviderName,
  topicModelingProvider: optionalProviderName,
  file: z
    .any()
    .refine((files) => files?.length === 1, "Arquivo é obrigatório.")
    .refine((files) => {
      const file = files?.[0];
      return file && file.size <= MAX_FILE_SIZE;
    }, `Tamanho máximo do arquivo é 200MB.`)
    .refine((files) => {
      const file = files?.[0];
      if (!file) return false;
      
      // Verifica por tipo MIME e extensão
      const acceptedTypes = ACCEPTED_FILE_TYPES.includes(file.type);
      const filename = file.name.toLowerCase();
      const acceptedExtensions = ['.mp4', '.webm', '.mov', '.avi', '.mkv', '.mp3', '.wav', '.m4a', '.flac', '.pdf', '.txt'].some(ext => filename.endsWith(ext));
      
      return acceptedTypes || acceptedExtensions;
    }, "Tipos aceitos: .mp4, .webm, .mov, .avi, .mkv, .mp3, .wav, .m4a, .flac, .pdf, .txt")
});

type UploadFormValues = z.infer<typeof uploadSchema>;

const AUTO_PROVIDER_VALUE = "__auto__";

export const UploadForm = () => {
  const { mutate: upload, isPending, progress } = useCreateMediaCommand();
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);
  const [fileType, setFileType] = React.useState<'video' | 'audio' | 'text' | null>(null);

  const {
    data: providersData,
    isLoading: providersLoading,
    isError: providersError,
    error: providersErrorObj,
  } = useQuery<ProvidersResponse>({
    queryKey: ["providers"],
    queryFn: getProviders,
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });

  const form = useForm<UploadFormValues>({
    resolver: zodResolver(uploadSchema),
    defaultValues: {
      storageProvider: 'local',
    },
  });

  const stageProviders = providersData?.stages ?? {};
  const storageProviders = stageProviders["storage"] ?? [];
  const transcriptionProviders = stageProviders["transcription"] ?? [];
  const summarizationProviders = stageProviders["summarization"] ?? [];
  const sentimentProviders = stageProviders["sentiment"] ?? [];
  const topicProviders = stageProviders["topic_modeling"] ?? [];

  const detectFileType = (file: File): 'video' | 'audio' | 'text' | null => {
    const filename = file.name.toLowerCase();
    const mimeType = file.type.toLowerCase();
    
    // Verifica por tipo MIME primeiro
    if (mimeType.startsWith('video/')) return 'video';
    if (mimeType.startsWith('audio/')) return 'audio';
    if (mimeType === 'application/pdf' || mimeType === 'text/plain') return 'text';
    
    // Verifica por extensão como fallback
    const videoExtensions = ['.mp4', '.webm', '.mov', '.avi', '.mkv'];
    const audioExtensions = ['.mp3', '.wav', '.m4a', '.flac'];
    const textExtensions = ['.pdf', '.txt'];
    
    if (videoExtensions.some(ext => filename.endsWith(ext))) return 'video';
    if (audioExtensions.some(ext => filename.endsWith(ext))) return 'audio';
    if (textExtensions.some(ext => filename.endsWith(ext))) return 'text';
    
    return null;
  };

  const watchedFile = form.watch('file');
  const watchedStorageProvider = form.watch("storageProvider");
  const watchedTranscriptionProvider = form.watch("transcriptionProvider");
  const watchedSummarizationProvider = form.watch("summarizationProvider");
  const watchedSentimentProvider = form.watch("sentimentProvider");
  const watchedTopicProvider = form.watch("topicModelingProvider");
  
  React.useEffect(() => {
    if (watchedFile?.length > 0) {
      const file = watchedFile[0];
      setSelectedFile(file);
      setFileType(detectFileType(file));
      
      // Reset providers quando tipo de arquivo muda
      form.setValue('transcriptionProvider', undefined);
      form.setValue('summarizationProvider', undefined);
      form.setValue('sentimentProvider', undefined);
      form.setValue('topicModelingProvider', undefined);
    } else {
      setSelectedFile(null);
      setFileType(null);
    }
  }, [watchedFile, form]);

  React.useEffect(() => {
    if (!providersData) return;
    if (!storageProviders.length) return;

    const current = watchedStorageProvider || "local";
    if (!storageProviders.some((p) => p.name === current)) {
      form.setValue("storageProvider", storageProviders[0].name);
    }
  }, [providersData, storageProviders, watchedStorageProvider, form]);

  const onSubmit: SubmitHandler<UploadFormValues> = (data) => {
    const file = data.file[0];
    const detectedFileType = detectFileType(file);
    
    // Enviar apenas providers relevantes baseados no tipo de arquivo
    const uploadData: CreateMediaCommand = {
      file,
      storageProvider: data.storageProvider,
    };
    
    // Só incluir transcriptionProvider para vídeo e áudio
    if (detectedFileType === 'video' || detectedFileType === 'audio') {
      if (data.transcriptionProvider) {
        uploadData.transcriptionProvider = data.transcriptionProvider;
      }
    }
    
    // Incluir summarizationProvider para todos os tipos
    if (data.summarizationProvider) {
      uploadData.summarizationProvider = data.summarizationProvider;
    }

    if (data.sentimentProvider) {
      uploadData.sentimentProvider = data.sentimentProvider;
    }

    if (data.topicModelingProvider) {
      uploadData.topicModelingProvider = data.topicModelingProvider;
    }
    
    upload(uploadData);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="file">Arquivo de Mídia</Label>
        <Input 
          id="file" 
          type="file" 
          accept=".mp4,.webm,.mov,.avi,.mkv,.mp3,.wav,.m4a,.flac,.pdf,.txt"
          {...form.register('file')} 
          disabled={isPending} 
        />
        {form.formState.errors.file && (
          <p className="text-sm text-destructive">{form.formState.errors.file.message?.toString()}</p>
        )}

        {(isPending || progress > 0) && (
          <div className="space-y-1">
            <div className="h-2 w-full rounded-full bg-muted overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-150"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-xs text-muted-foreground">Upload em andamento: {progress}%</p>
          </div>
        )}

        {selectedFile && (
          <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-md border">
            <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Arquivo Selecionado:</h4>
            <div className="space-y-1 text-sm text-gray-600 dark:text-gray-400">
              <p><span className="font-medium">Nome:</span> {selectedFile.name}</p>
              <p><span className="font-medium">Tamanho:</span> {formatFileSize(selectedFile.size)}</p>
              <p><span className="font-medium">Tipo:</span> {selectedFile.type || 'Não identificado'}</p>
              <p><span className="font-medium">Categoria:</span> {
                fileType === 'video' ? 'Vídeo - Transcrição e Sumarização disponíveis' :
                fileType === 'audio' ? 'Áudio - Transcrição e Sumarização disponíveis' :
                fileType === 'text' ? 'Texto - Apenas Sumarização disponível' :
                'Tipo não identificado'
              }</p>
            </div>
          </div>
        )}

        <Card className="mt-6 border border-dashed border-gray-200 dark:border-gray-700">
          <CardHeader>
            <CardTitle className="text-base">Configuração avançada</CardTitle>
            <p className="text-sm text-muted-foreground">
              Providers disponíveis são carregados do endpoint{" "}
              <code className="font-mono text-xs">/providers</code>. Use{" "}
              <span className="font-medium">Automático</span> para manter o padrão do sistema.
            </p>
            {providersError && (
              <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2 mt-3">
                Falha ao carregar /providers. Você pode digitar os nomes manualmente.
                {providersErrorObj instanceof Error ? ` (${providersErrorObj.message})` : ""}
              </p>
            )}
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="space-y-2">
              <Label htmlFor="storage-provider">Provider de Armazenamento</Label>
              {storageProviders.length > 0 && !providersError ? (
                <Select
                  value={watchedStorageProvider}
                  onValueChange={(value) => form.setValue("storageProvider", value)}
                  disabled={isPending || providersLoading}
                >
                  <SelectTrigger id="storage-provider">
                    <SelectValue
                      placeholder={
                        providersLoading ? "Carregando..." : "Selecione o storage"
                      }
                    />
                  </SelectTrigger>
                  <SelectContent>
                    {storageProviders.map((p) => (
                      <SelectItem key={p.name} value={p.name}>
                        <div className="flex flex-col gap-0.5">
                          <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
                            {p.label || p.name}
                          </span>
                          {p.description && (
                            <span className="text-xs text-muted-foreground">
                              {p.description}
                            </span>
                          )}
                        </div>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              ) : (
                <Input
                  id="storage-provider"
                  placeholder={
                    providersError
                      ? "Falha ao carregar /providers (digite manualmente)"
                      : "Digite o nome do storage"
                  }
                  disabled={isPending}
                  {...form.register("storageProvider")}
                />
              )}
              {form.formState.errors.storageProvider && (
                <p className="text-sm text-destructive">{form.formState.errors.storageProvider.message?.toString()}</p>
              )}
              <p className="text-xs text-muted-foreground">
                Este provider precisa suportar <span className="font-mono text-xs">upload</span> e{" "}
                <span className="font-mono text-xs">download</span> (para exibição no frontend).
              </p>
            </div>

            {selectedFile && fileType && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {(fileType === "video" || fileType === "audio") && (
                  <div className="space-y-2">
                    <Label htmlFor="transcription-provider">
                      Provider de Transcrição{" "}
                      <span className="text-xs text-gray-500">
                        (para {fileType === "video" ? "vídeos" : "áudios"})
                      </span>
                    </Label>
                    {transcriptionProviders.length > 0 && !providersError ? (
                      <Select
                        value={watchedTranscriptionProvider ?? AUTO_PROVIDER_VALUE}
                        onValueChange={(value) =>
                          form.setValue(
                            "transcriptionProvider",
                            value === AUTO_PROVIDER_VALUE ? undefined : value,
                          )
                        }
                        disabled={isPending || providersLoading}
                      >
                        <SelectTrigger id="transcription-provider">
                          <SelectValue placeholder="Selecione (opcional)" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value={AUTO_PROVIDER_VALUE}>Automático</SelectItem>
                          {transcriptionProviders.map((p) => (
                            <SelectItem key={p.name} value={p.name}>
                              {p.label || p.name}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    ) : (
                      <Input
                        id="transcription-provider"
                        placeholder="Automático (ou digite o nome)"
                        disabled={isPending}
                        {...form.register("transcriptionProvider")}
                      />
                    )}
                  </div>
                )}

                <div className="space-y-2">
                  <Label htmlFor="summarization-provider">Provider de Sumarização</Label>
                  {summarizationProviders.length > 0 && !providersError ? (
                    <Select
                      value={watchedSummarizationProvider ?? AUTO_PROVIDER_VALUE}
                      onValueChange={(value) =>
                        form.setValue(
                          "summarizationProvider",
                          value === AUTO_PROVIDER_VALUE ? undefined : value,
                        )
                      }
                      disabled={isPending || providersLoading}
                    >
                      <SelectTrigger id="summarization-provider">
                        <SelectValue placeholder="Selecione (opcional)" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value={AUTO_PROVIDER_VALUE}>Automático</SelectItem>
                        {summarizationProviders.map((p) => (
                          <SelectItem key={p.name} value={p.name}>
                            {p.label || p.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input
                      id="summarization-provider"
                      placeholder="Automático (ou digite o nome)"
                      disabled={isPending}
                      {...form.register("summarizationProvider")}
                    />
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="sentiment-provider">Provider de Análise de Sentimento</Label>
                  {sentimentProviders.length > 0 && !providersError ? (
                    <Select
                      value={watchedSentimentProvider ?? AUTO_PROVIDER_VALUE}
                      onValueChange={(value) =>
                        form.setValue(
                          "sentimentProvider",
                          value === AUTO_PROVIDER_VALUE ? undefined : value,
                        )
                      }
                      disabled={isPending || providersLoading}
                    >
                      <SelectTrigger id="sentiment-provider">
                        <SelectValue placeholder="Selecione (opcional)" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value={AUTO_PROVIDER_VALUE}>Automático</SelectItem>
                        {sentimentProviders.map((p) => (
                          <SelectItem key={p.name} value={p.name}>
                            {p.label || p.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input
                      id="sentiment-provider"
                      placeholder="Automático (ou digite o nome)"
                      disabled={isPending}
                      {...form.register("sentimentProvider")}
                    />
                  )}
                </div>

                <div className="space-y-2">
                  <Label htmlFor="topic-provider">Provider de Modelagem de Tópicos</Label>
                  {topicProviders.length > 0 && !providersError ? (
                    <Select
                      value={watchedTopicProvider ?? AUTO_PROVIDER_VALUE}
                      onValueChange={(value) =>
                        form.setValue(
                          "topicModelingProvider",
                          value === AUTO_PROVIDER_VALUE ? undefined : value,
                        )
                      }
                      disabled={isPending || providersLoading}
                    >
                      <SelectTrigger id="topic-provider">
                        <SelectValue placeholder="Selecione (opcional)" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value={AUTO_PROVIDER_VALUE}>Automático</SelectItem>
                        {topicProviders.map((p) => (
                          <SelectItem key={p.name} value={p.name}>
                            {p.label || p.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  ) : (
                    <Input
                      id="topic-provider"
                      placeholder="Automático (ou digite o nome)"
                      disabled={isPending}
                      {...form.register("topicModelingProvider")}
                    />
                  )}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Opções de processamento - exibidas apenas com arquivo selecionado */}
      {selectedFile && fileType && (
        <div className="space-y-4">
          <div className="border-t pt-4">
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
              Opções de Processamento de Conteúdo
            </h3>
            
            {/* Information about processing */}
            <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md border border-blue-200 dark:border-blue-800">
              <p className="text-sm text-blue-700 dark:text-blue-300">
                <strong>Pipeline de Processamento:</strong>
                {fileType === 'video' && " Vídeo → Transcrição → Sumarização → Sentimento → Tópicos"}
                {fileType === 'audio' && " Áudio → Transcrição → Sumarização → Sentimento → Tópicos"}
                {fileType === 'text' && " Texto → Sumarização → Sentimento → Tópicos"}
              </p>
            </div>
          </div>
        </div>
      )}

      <Button type="submit" className="w-full" disabled={isPending || !selectedFile}>
        {isPending ? 'Enviando...' : 'Enviar Arquivo'}
      </Button>
    </form>
  );
};
