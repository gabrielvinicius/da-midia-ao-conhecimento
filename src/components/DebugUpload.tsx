import React, { useState } from 'react';
import { Button } from './ui/Button';
import api from '@/lib/api';

export const DebugUpload = () => {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string>('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile) {
      setFile(selectedFile);
      setResult(null);
      setError('');
    }
  };

  const testUpload = async () => {
    if (!file) return;

    setLoading(true);
    setError('');
    setResult(null);

    try {
      console.log('🔍 Iniciando teste de upload...');
      
      // 1. Verificar se há token
      const token = localStorage.getItem('token');
      console.log('🔑 Token presente:', !!token);
      
      // 2. Teste de conectividade
      console.log('🌐 Testando conectividade...');
      const healthCheck = await api.get('/health').catch(() => null);
      console.log('🏥 Health check:', healthCheck?.status || 'FALHOU');
      
      // 3. Teste de autenticação
      console.log('👤 Testando autenticação...');
      const meCheck = await api.get('/auth/me').catch((err) => {
        console.log('❌ Auth check failed:', err.response?.status, err.response?.data);
        return null;
      });
      console.log('👤 Auth check:', meCheck?.status || 'FALHOU');
      
      // 4. Teste de providers
      console.log('🔧 Testando providers...');
      const providersCheck = await api.get('/providers/storage').catch((err) => {
        console.log('❌ Providers check failed:', err.response?.status, err.response?.data);
        return null;
      });
      console.log('🔧 Providers:', providersCheck?.data || 'FALHOU');
      
      // 5. Teste de upload
      console.log('📤 Testando upload...');
      const formData = new FormData();
      formData.append('file', file);
      
      const uploadResponse = await api.post('/media/', formData, {
        params: {
          storageProvider: 'local',
        },
        headers: {
          // Não definir Content-Type para multipart
        },
        timeout: 60000, // 1 minuto
      });
      
      console.log('✅ Upload sucesso:', uploadResponse.data);
      setResult({
        success: true,
        data: uploadResponse.data,
        checks: {
          token: !!token,
          health: healthCheck?.status || 'FALHOU',
          auth: meCheck?.status || 'FALHOU',
          providers: providersCheck?.data || 'FALHOU',
        }
      });
      
    } catch (err: any) {
      console.error('❌ Erro no upload:', err);
      setError(`Erro: ${err.response?.status} - ${err.response?.data?.detail || err.message}`);
      setResult({
        success: false,
        error: err.response?.data || err.message,
        status: err.response?.status,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 border border-yellow-300 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg">
      <h3 className="text-lg font-semibold mb-4 text-yellow-800 dark:text-yellow-200">
        🔧 Debug Upload
      </h3>
      
      <div className="space-y-4">
        <div>
          <input
            type="file"
            onChange={handleFileChange}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
        </div>
        
        {file && (
          <div className="text-sm">
            <p><strong>Arquivo:</strong> {file.name}</p>
            <p><strong>Tamanho:</strong> {(file.size / 1024 / 1024).toFixed(2)} MB</p>
            <p><strong>Tipo:</strong> {file.type}</p>
          </div>
        )}
        
        <Button 
          onClick={testUpload} 
          disabled={!file || loading}
          className="w-full"
        >
          {loading ? 'Testando...' : '🧪 Testar Upload'}
        </Button>
        
        {error && (
          <div className="p-3 bg-red-100 border border-red-300 rounded text-red-700 text-sm">
            {error}
          </div>
        )}
        
        {result && (
          <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded text-sm">
            <pre className="whitespace-pre-wrap text-xs">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
};