import * as React from 'react';
import { SubmitHandler, useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';

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
import { useProviders } from '@/features/providers/hooks/useProviders';
import { useStorageProviders } from '@/features/providers/hooks/useStorageProviders';
import { useProvidersContext } from '@/features/providers/context/ProvidersContext';
import { useCreateMediaCommand } from '@/hooks/useCommands';
import { CreateMediaCommand } from '@/api/commands';

const MAX_FILE_SIZE = 200 * 1024 * 1024; // 200 MB (conforme configuração do backend)
const ACCEPTED_FILE_TYPES = [
  "video/mp4", "video/webm", "video/quicktime", "video/x-msvideo", "video/x-matroska",
  "audio/mpeg", "audio/wav", "audio/mp4", "audio/flac",
  "application/pdf", "text/plain"
];

const PROVIDER_GROUPS: { key: 'storage' | 'transcription' | 'summarization' | 'sentiment' | 'topics'; label: string }[] = [
  { key: 'storage', label: 'Armazenamento' },
  { key: 'transcription', label: 'Transcrição' },
  { key: 'summarization', label: 'Sumarização' },
  { key: 'sentiment', label: 'Sentimento' },
  { key: 'topics', label: 'Modelagem de tópicos' },
];

const uploadSchema = z.object({
  storageProvider: z.string().default("local"),
  transcriptionProvider: z.string().optional(),
  summarizationProvider: z.string().optional(),
  sentimentProvider: z.string().optional(),
  topicModelingProvider: z.string().optional(),
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

export const UploadForm = () => {
  const { mutate: upload, isPending, progress } = useCreateMediaCommand();
  const { data: transcriptionProviders } = useProviders("transcription");
  const { data: summarizationProviders } = useProviders("summarization");
  const { data: sentimentProviders } = useProviders("sentiment");
  const { data: topicProviders } = useProviders("topics");
  const { data: storageProviders, isLoading: isLoadingStorage } = useStorageProviders();
  const { providers: providerMap } = useProvidersContext();
  const [selectedFile, setSelectedFile] = React.useState<File | null>(null);
  const [fileType, setFileType] = React.useState<'video' | 'audio' | 'text' | null>(null);

  const form = useForm<UploadFormValues>({
    resolver: zodResolver(uploadSchema),
    defaultValues: {
      storageProvider: 'local',
    },
  });

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
  const selectedTopicProvider = form.watch('topicModelingProvider');
  const selectedSummarizationProvider = form.watch('summarizationProvider');
  const topicProviderDetails = selectedTopicProvider
    ? topicProviders?.find((entry) => entry.name === selectedTopicProvider)
    : undefined;
  const summarizationProviderDetails = selectedSummarizationProvider
    ? summarizationProviders?.find((entry) => entry.name === selectedSummarizationProvider)
    : undefined;
  
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

  const onSubmit: SubmitHandler<UploadFormValues> = (data) => {
    const file = data.file[0];
    const detectedFileType = detectFileType(file);
    
    console.log('Uploading file:', { 
      name: file.name, 
      size: file.size, 
      type: file.type,
      detectedFileType,
      storageProvider: data.storageProvider
    });
    
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
    
    console.log('Sending upload data:', uploadData);
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
            <CardTitle className="text-base">Provedores disponíveis (API)</CardTitle>
            <p className="text-sm text-muted-foreground">
              Esta lista reflete exatamente o que o endpoint `/providers` retorna para cada etapa do pipeline.
            </p>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            {PROVIDER_GROUPS.map((group) => {
              const list = providerMap[group.key] || [];
              return (
                <div key={group.key} className="space-y-1">
                  <p className="font-medium text-slate-900 dark:text-slate-100">{group.label}</p>
                  {list.length ? (
                    <div className="flex flex-wrap gap-2">
                      {list.map((provider) => (
                        <span key={provider.name} className="rounded-full border border-[#f2eadf] bg-[#fdfbf6] px-3 py-1 text-xs text-slate-800">
                          {provider.label || provider.name}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <p className="text-xs text-muted-foreground">Nenhum provider registrado para este tipo.</p>
                  )}
                </div>
              );
            })}
          </CardContent>
        </Card>
      </div>
      
      {/* Storage Provider Section - Always visible */}
      <div className="space-y-2">
        <Label htmlFor="storage-provider">Provider de Armazenamento</Label>
        <Select 
          onValueChange={(value) => form.setValue('storageProvider', value)} 
          disabled={isPending || isLoadingStorage || (storageProviders?.length ?? 0) === 0}
          defaultValue="local"
        >
          <SelectTrigger id="storage-provider">
            <SelectValue placeholder={isLoadingStorage ? 'Carregando providers...' : 'Selecione onde armazenar o arquivo'} />
          </SelectTrigger>
          <SelectContent>
            {storageProviders && storageProviders.length > 0 ? (
              storageProviders.map(provider => (
                <SelectItem key={provider.name} value={provider.name}>
                  <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-medium text-slate-900 dark:text-slate-100">
                      {provider.label || provider.name}
                    </span>
                    {provider.description && (
                      <span className="text-xs text-muted-foreground">
                        {provider.description}
                      </span>
                    )}
                  </div>
                </SelectItem>
              ))
            ) : (
              <SelectItem value="_empty" disabled>
                {isLoadingStorage ? 'Carregando opções...' : 'Nenhum provider disponível'}
              </SelectItem>
            )}
          </SelectContent>
        </Select>
        <p className="text-xs text-gray-500">
          {isLoadingStorage ? 'Carregando providers...' : 
           'Escolha onde o arquivo será armazenado. Local mantém no servidor, S3/MinIO para armazenamento em nuvem.'}
        </p>
      </div>
      
      {/* Providers Section - Only show if file is selected */}
      {selectedFile && fileType && (
        <div className="space-y-4">
          <div className="border-t pt-4">
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-4">
              Opções de Processamento de Conteúdo
            </h3>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Transcription Provider - Only for video and audio */}
              {(fileType === 'video' || fileType === 'audio') && (
                <div className="space-y-2">
                  <Label htmlFor="transcription-provider">
                    Provider de Transcrição
                    <span className="text-xs text-gray-500 ml-1">
                      (para {fileType === 'video' ? 'vídeos' : 'áudios'})
                    </span>
                  </Label>
                  <Select onValueChange={(value) => form.setValue('transcriptionProvider', value)} disabled={isPending}>
                    <SelectTrigger id="transcription-provider">
                      <SelectValue placeholder="Selecione um provider (opcional)" />
                    </SelectTrigger>
                    <SelectContent>
                    {transcriptionProviders && transcriptionProviders.length > 0 ? (
                      transcriptionProviders.map(p => (
                        <SelectItem key={p.name} value={p.name}>
                          <div className="flex flex-col gap-0.5">
                            <span className="text-sm font-medium text-slate-900 dark:text-slate-100">{p.label || p.name}</span>
                            {p.description && <span className="text-xs text-muted-foreground">{p.description}</span>}
                          </div>
                        </SelectItem>
                      ))
                      ) : (
                        <SelectItem value="_empty" disabled>
                          Nenhum provider disponível
                        </SelectItem>
                      )}
                    </SelectContent>
                  </Select>
                </div>
              )}
              
              {/* Summarization Provider - For all types */}
              <div className="space-y-2">
                <Label htmlFor="summarization-provider">
                  Provider de Sumarização
                  <span className="text-xs text-gray-500 ml-1">
                    (para {fileType === 'text' ? 'textos' : fileType === 'video' ? 'transcrições de vídeo' : 'transcrições de áudio'})
                  </span>
                </Label>
                <Select onValueChange={(value) => form.setValue('summarizationProvider', value)} disabled={isPending}>
                  <SelectTrigger id="summarization-provider">
                    <SelectValue placeholder="Selecione um provider (opcional)" />
                  </SelectTrigger>
                  <SelectContent>
                    {summarizationProviders && summarizationProviders.length > 0 ? (
                      summarizationProviders.map(p => (
                        <SelectItem key={p.name} value={p.name}>
                          <div className="flex flex-col gap-0.5">
                            <span className="text-sm font-medium text-slate-900 dark:text-slate-100">{p.label || p.name}</span>
                            {p.description && (
                              <span className="text-xs text-muted-foreground">
                                {p.description}
                              </span>
                            )}
                          </div>
                        </SelectItem>
                      ))
                    ) : (
                      <SelectItem value="_empty" disabled>
                        Nenhum provider disponível
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
                {selectedSummarizationProvider && (
                  <p className="text-xs text-muted-foreground">
                    {summarizationProviderDetails?.description || 'Provider selecionado.'}
                  </p>
                )}
              </div>

              {/* Sentiment Provider */}
              <div className="space-y-2">
                <Label htmlFor="sentiment-provider">
                  Provider de Análise de Sentimento
                  <span className="text-xs text-gray-500 ml-1">(executado após a transcrição)</span>
                </Label>
                <Select onValueChange={(value) => form.setValue('sentimentProvider', value)} disabled={isPending}>
                  <SelectTrigger id="sentiment-provider">
                    <SelectValue placeholder="Selecione um provider (opcional)" />
                  </SelectTrigger>
                  <SelectContent>
                    {sentimentProviders && sentimentProviders.length > 0 ? (
                      sentimentProviders.map(p => (
                        <SelectItem key={p.name} value={p.name}>
                          <div className="flex flex-col gap-0.5">
                            <span className="text-sm font-medium text-slate-900 dark:text-slate-100">{p.label || p.name}</span>
                            {p.description && <span className="text-xs text-muted-foreground">{p.description}</span>}
                          </div>
                        </SelectItem>
                      ))
                    ) : (
                      <SelectItem value="_empty" disabled>
                        Nenhum provider disponível
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
              </div>

              {/* Topic Modeling Provider */}
              <div className="space-y-2">
                <Label htmlFor="topic-provider">
                  Provider de Modelagem de Tópicos
                  <span className="text-xs text-gray-500 ml-1">(executado após a sumarização)</span>
                </Label>
                <Select onValueChange={(value) => form.setValue('topicModelingProvider', value)} disabled={isPending}>
                  <SelectTrigger id="topic-provider">
                    <SelectValue placeholder="Selecione um provider (opcional)" />
                  </SelectTrigger>
                  <SelectContent>
                    {topicProviders && topicProviders.length > 0 ? (
                      topicProviders.map(p => (
                        <SelectItem key={p.name} value={p.name}>
                          <div className="flex flex-col gap-0.5">
                            <span className="text-sm font-medium text-slate-900 dark:text-slate-100">{p.label || p.name}</span>
                            {p.description && (
                              <span className="text-xs text-muted-foreground">
                                {p.description}
                              </span>
                            )}
                          </div>
                        </SelectItem>
                      ))
                    ) : (
                      <SelectItem value="_empty" disabled>
                        Nenhum provider disponível
                      </SelectItem>
                    )}
                  </SelectContent>
                </Select>
                {selectedTopicProvider && (
                  <p className="text-xs text-muted-foreground">
                    {topicProviderDetails?.description || 'Provider selecionado.'}
                  </p>
                )}
              </div>
            </div>
            
            {/* Information about processing */}
            <div className="mt-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-md border border-blue-200 dark:border-blue-800">
              <p className="text-sm text-blue-700 dark:text-blue-300">
                <strong>Pipeline de Processamento:</strong>
                {fileType === 'video' && " Vídeo → Transcrição → Sumarização → Sentimento → Tópicos"}
                {fileType === 'audio' && " Áudio → Transcrição → Sumarização → Sentimento → Tópicos"}
                {fileType === 'text' && " Texto → Sumarização → Sentimento → Tópicos"}
              </p>
            </div>

            <Card className="mt-4 border border-dashed border-gray-200 dark:border-gray-700">
              <CardHeader>
                <CardTitle className="text-base">Provedores disponíveis (dados da API)</CardTitle>
                <p className="text-sm text-muted-foreground">
                  Esta lista reflete o endpoint <code className="font-mono text-xs text-slate-600">/providers</code> em tempo real.
                </p>
              </CardHeader>
              <CardContent className="space-y-4 text-sm">
                {PROVIDER_GROUPS.map((group) => {
                  const list = providerMap[group.key] || [];
                  return (
                    <div key={group.key} className="space-y-1">
                      <p className="font-medium text-slate-900 dark:text-slate-100">{group.label}</p>
                      {list.length ? (
                        <div className="flex flex-wrap gap-2">
                          {list.map((provider) => (
                            <span key={provider.name} className="rounded-full border border-[#f2eadf] bg-[#fdfbf6] px-3 py-1 text-xs text-slate-800">
                              {provider.label || provider.name}
                            </span>
                          ))}
                        </div>
                      ) : (
                        <p className="text-xs text-muted-foreground">Nenhum provider registrado para este tipo.</p>
                      )}
                    </div>
                  );
                })}
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      <Button type="submit" className="w-full" disabled={isPending || !selectedFile}>
        {isPending ? 'Enviando...' : 'Enviar Arquivo'}
      </Button>
    </form>
  );
};
