import React, { useState } from 'react';
import { Button } from './ui/Button';
import { uploadMedia } from '@/features/media/api';

export const SimpleUpload = () => {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setResult(null);
    }
  };

  const handleUpload = async () => {
    if (!file) return;

    setUploading(true);
    setResult(null);

    try {
      console.log('🧪 Iniciando upload simples...');
      console.log('📁 Arquivo selecionado:', {
        name: file.name,
        size: file.size,
        type: file.type,
        constructor: file.constructor.name,
        isFile: file instanceof File
      });
      
      // Verificar se é realmente um File
      if (!(file instanceof File)) {
        throw new Error('Arquivo selecionado não é uma instância válida de File');
      }
      
      const uploadData = {
        file: file,
        storageProvider: 'local', // Será convertido para storage_provider na API
      };

      console.log('📤 Dados do upload:', uploadData);

      // Teste manual de FormData
      console.log('🧪 Testando FormData manualmente:');
      const testFormData = new FormData();
      testFormData.append('file', file, file.name);
      
      console.log('FormData entries:');
      for (let [key, value] of testFormData.entries()) {
        console.log(`${key}:`, value);
      }

      const response = await uploadMedia(uploadData);
      
      console.log('✅ Upload concluído:', response);
      setResult({ success: true, data: response });

    } catch (error: any) {
      console.error('❌ Erro no upload:', error);
      setResult({ 
        success: false, 
        error: error.response?.data || error.message,
        status: error.response?.status 
      });
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="p-6 border border-green-300 bg-green-50 dark:bg-green-900/20 rounded-lg">
      <h3 className="text-lg font-semibold mb-4 text-green-800 dark:text-green-200">
        🧪 Upload Simples
      </h3>
      
      <div className="space-y-4">
        <div>
          <input
            type="file"
            onChange={handleFileChange}
            accept=".txt,.pdf,.mp3,.mp4"
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-green-50 file:text-green-700 hover:file:bg-green-100"
          />
        </div>
        
        {file && (
          <div className="text-sm bg-white p-3 rounded border">
            <p><strong>📁 Arquivo:</strong> {file.name}</p>
            <p><strong>📏 Tamanho:</strong> {(file.size / 1024).toFixed(1)} KB</p>
            <p><strong>🏷️ Tipo:</strong> {file.type || 'Não identificado'}</p>
          </div>
        )}
        
        <Button 
          onClick={handleUpload} 
          disabled={!file || uploading}
          className="w-full"
        >
          {uploading ? '⏳ Enviando...' : '📤 Upload Simples'}
        </Button>
        
        {result && (
          <div className={`p-3 rounded text-sm ${
            result.success 
              ? 'bg-green-100 border border-green-300 text-green-700' 
              : 'bg-red-100 border border-red-300 text-red-700'
          }`}>
            {result.success ? (
              <>
                <div className="font-semibold">✅ Sucesso!</div>
                <div>ID: {result.data.id}</div>
                <div>Status: {result.data.status}</div>
                <div>Tipo: {result.data.media_type}</div>
              </>
            ) : (
              <>
                <div className="font-semibold">❌ Erro!</div>
                <div>Status: {result.status}</div>
                <pre className="mt-2 text-xs whitespace-pre-wrap">
                  {JSON.stringify(result.error, null, 2)}
                </pre>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
};