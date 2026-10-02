import * as React from 'react';
import { useQuery } from '@tanstack/react-query';

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/Card";
import { useCreateMediaCommand } from '@/hooks/useCommands';
import { getProviders, ProvidersResponse } from '@/api/queries';
import {
  ACCEPTED_EXTENSIONS,
  PIPELINE_STEPS,
  fileProblem,
  formatFileSize,
  uploadKind,
} from '../uploadFile';
import { ProviderSelect } from './ProviderSelect';

const KIND_LABEL = { video: 'Vídeo', audio: 'Áudio', text: 'Documento ou imagem' } as const;

export const UploadForm = () => {
  const { mutate: upload, isPending, progress } = useCreateMediaCommand();
  const [file, setFile] = React.useState<File | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [storageProvider, setStorageProvider] = React.useState<string | undefined>('local');
  const [transcriptionProvider, setTranscriptionProvider] = React.useState<string | undefined>();

  const providers = useQuery<ProvidersResponse>({
    queryKey: ["providers"],
    queryFn: getProviders,
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  });
  const stages = providers.isError ? {} : providers.data?.stages ?? {};
  const storageOptions = stages["storage"] ?? [];
  const transcriptionOptions = stages["transcription"] ?? [];

  // O armazenamento escolhido precisa existir na lista do servidor.
  React.useEffect(() => {
    if (storageOptions.length && !storageOptions.some((p) => p.name === storageProvider)) {
      setStorageProvider(storageOptions[0].name);
    }
  }, [storageOptions, storageProvider]);

  const kind = file ? uploadKind(file) : null;

  const onFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const chosen = event.target.files?.[0] ?? null;
    setFile(chosen);
    setTranscriptionProvider(undefined);
    setError(chosen ? fileProblem(chosen) : null);
  };

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    const problem = fileProblem(file ?? undefined);
    if (problem || !file) {
      setError(problem);
      return;
    }
    if (!storageProvider) {
      setError('Provider de armazenamento é obrigatório.');
      return;
    }
    upload({
      file,
      storageProvider,
      // A escolha do transcritor só vale para o que tem fala.
      transcriptionProvider: kind === 'text' ? undefined : transcriptionProvider,
    });
  };

  return (
    <form onSubmit={onSubmit} className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="file">Arquivo de Mídia</Label>
        <Input
          id="file"
          type="file"
          accept={ACCEPTED_EXTENSIONS.join(",")}
          onChange={onFileChange}
          disabled={isPending}
        />
        {error && <p className="text-sm text-destructive">{error}</p>}

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

        {file && kind && (
          <div className="mt-3 p-3 bg-gray-50 dark:bg-gray-800 rounded-md border">
            <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Arquivo Selecionado:</h4>
            <div className="space-y-1 text-sm text-gray-600 dark:text-gray-400">
              <p><span className="font-medium">Nome:</span> {file.name}</p>
              <p><span className="font-medium">Tamanho:</span> {formatFileSize(file.size)}</p>
              <p><span className="font-medium">Categoria:</span> {KIND_LABEL[kind]}</p>
              <p><span className="font-medium">O que será feito:</span> {PIPELINE_STEPS[kind]}.</p>
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
            {providers.isError && (
              <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-md px-3 py-2 mt-3">
                Falha ao carregar /providers. Você pode digitar os nomes manualmente.
              </p>
            )}
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="space-y-2">
              <Label htmlFor="storage-provider">Provider de Armazenamento</Label>
              <ProviderSelect
                id="storage-provider"
                options={storageOptions}
                value={storageProvider}
                onChange={setStorageProvider}
                disabled={isPending || providers.isLoading}
                fallbackPlaceholder="Digite o nome do storage"
              />
              <p className="text-xs text-muted-foreground">
                Este provider precisa suportar <span className="font-mono text-xs">upload</span> e{" "}
                <span className="font-mono text-xs">download</span> (para exibição no frontend).
              </p>
            </div>

            {(kind === "video" || kind === "audio") && (
              <div className="space-y-2">
                <Label htmlFor="transcription-provider">
                  Provider de Transcrição{" "}
                  <span className="text-xs text-gray-500">
                    (para {kind === "video" ? "vídeos" : "áudios"})
                  </span>
                </Label>
                <ProviderSelect
                  id="transcription-provider"
                  options={transcriptionOptions}
                  value={transcriptionProvider}
                  onChange={setTranscriptionProvider}
                  disabled={isPending || providers.isLoading}
                  allowAuto
                  fallbackPlaceholder="Automático (ou digite o nome)"
                />
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      <Button type="submit" className="w-full" disabled={isPending || !file}>
        {isPending ? 'Enviando...' : 'Enviar Arquivo'}
      </Button>
    </form>
  );
};
