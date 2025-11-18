import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/Card";
import { UploadForm } from "../features/media/components/UploadForm";

const UploadPage = () => {
  return (
    <div className="flex items-center justify-center min-h-screen p-4">
      <div className="w-full max-w-4xl space-y-6">
        {/* Main Upload Card */}
        <Card className="w-full">
          <CardHeader>
            <CardTitle>Enviar Nova Mídia</CardTitle>
            <CardDescription>
              Selecione um arquivo e escolha os providers de processamento adequados para o tipo de mídia.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <UploadForm />
          </CardContent>
        </Card>

        {/* File Type Information Cards */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Tipos de Mídia Suportados
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center">
                🎥 Vídeos
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                <strong>Formatos:</strong> .mp4, .webm, .mov, .avi, .mkv
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                <strong>Processamento:</strong> Transcrição → Sumarização → Sentimento → Tópicos
              </p>
              <p className="text-sm text-blue-600 dark:text-blue-400">
                Ideal para: Reuniões, aulas, entrevistas
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center">
                🎵 Áudios
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                <strong>Formatos:</strong> .mp3, .wav, .m4a, .flac
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                <strong>Processamento:</strong> Transcrição → Sumarização → Sentimento → Tópicos
              </p>
              <p className="text-sm text-blue-600 dark:text-blue-400">
                Ideal para: Podcasts, gravações, chamadas
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center">
                📄 Textos
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <p className="text-sm text-gray-600 dark:text-gray-400">
                <strong>Formatos:</strong> .pdf, .txt
              </p>
              <p className="text-sm text-gray-600 dark:text-gray-400">
                <strong>Processamento:</strong> Sumarização → Sentimento → Tópicos
              </p>
              <p className="text-sm text-blue-600 dark:text-blue-400">
                Ideal para: Documentos, artigos, relatórios
              </p>
            </CardContent>
          </Card>
          </div>
        </div>

        {/* Storage Providers Information */}
        <div className="space-y-4">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-gray-100">
            Opções de Armazenamento
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center">
                  💾 Local (Servidor)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  <strong>Localização:</strong> Diretório do servidor
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  <strong>Vantagens:</strong> Rápido, sem custos externos, controle total
                </p>
                <p className="text-sm text-blue-600 dark:text-blue-400">
                  Ideal para: Desenvolvimento, dados sensíveis, pequenos volumes
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-lg flex items-center">
                  ☁️ Nuvem (S3/MinIO)
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  <strong>Localização:</strong> Armazenamento em nuvem
                </p>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  <strong>Vantagens:</strong> Escalável, backup automático, CDN
                </p>
                <p className="text-sm text-blue-600 dark:text-blue-400">
                  Ideal para: Produção, grandes volumes, distribuição global
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UploadPage;
