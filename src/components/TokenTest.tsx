import React, { useState } from 'react';
import { Button } from './ui/Button';
import api from '@/lib/api';

export const TokenTest = () => {
  const [testing, setTesting] = useState(false);
  const [results, setResults] = useState<any[]>([]);

  const addResult = (test: string, success: boolean, data: any) => {
    const result = {
      test,
      success,
      data,
      timestamp: new Date().toLocaleTimeString()
    };
    setResults(prev => [result, ...prev]);
    console.log(`🧪 ${test}:`, result);
  };

  const runTests = async () => {
    setTesting(true);
    setResults([]);

    try {
      // Test 1: Verificar token no localStorage
      const token = localStorage.getItem('token');
      addResult('Token no localStorage', !!token, { 
        exists: !!token, 
        preview: token ? token.substring(0, 30) + '...' : 'Nenhum' 
      });

      if (!token) {
        addResult('Conclusão', false, { message: 'Nenhum token encontrado. Faça login primeiro.' });
        return;
      }

      // Test 2: Testar endpoint de auth/me
      try {
        const meResponse = await api.get('/auth/me');
        addResult('GET /auth/me', true, { 
          status: meResponse.status, 
          user: meResponse.data 
        });
      } catch (error: any) {
        addResult('GET /auth/me', false, { 
          status: error.response?.status, 
          error: error.response?.data || error.message 
        });
      }

      // Test 3: Testar endpoint de providers
      try {
        const providersResponse = await api.get('/providers/storage');
        addResult('GET /providers/storage', true, { 
          status: providersResponse.status, 
          providers: providersResponse.data 
        });
      } catch (error: any) {
        addResult('GET /providers/storage', false, { 
          status: error.response?.status, 
          error: error.response?.data || error.message 
        });
      }

      // Test 4: Testar endpoint de media (listar)
      try {
        const mediaResponse = await api.get('/media/');
        addResult('GET /media/', true, { 
          status: mediaResponse.status, 
          count: mediaResponse.data?.length || 0 
        });
      } catch (error: any) {
        addResult('GET /media/', false, { 
          status: error.response?.status, 
          error: error.response?.data || error.message 
        });
      }

      // Test 5: Testar upload sem arquivo (deve dar erro 400)
      try {
        const formData = new FormData();
        formData.append('file', new Blob(['test'], { type: 'text/plain' }), 'test.txt');
        
        const uploadResponse = await api.post('/media/?storage_provider=local', formData, {
          headers: {
            // Não definir Content-Type para multipart
          }
        });
        addResult('POST /media/ (teste)', true, { 
          status: uploadResponse.status, 
          data: uploadResponse.data 
        });
      } catch (error: any) {
        addResult('POST /media/ (teste)', false, { 
          status: error.response?.status, 
          error: error.response?.data || error.message 
        });
      }

    } catch (error) {
      addResult('Erro geral', false, { error: error });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="p-6 border border-blue-300 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
      <h3 className="text-lg font-semibold mb-4 text-blue-800 dark:text-blue-200">
        🔑 Teste de Token de Autenticação
      </h3>
      
      <div className="space-y-4">
        <Button 
          onClick={runTests} 
          disabled={testing}
          className="w-full"
        >
          {testing ? '⏳ Testando...' : '🧪 Executar Testes de Token'}
        </Button>
        
        {results.length > 0 && (
          <div className="space-y-2 max-h-96 overflow-y-auto">
            <h4 className="font-semibold">Resultados dos Testes:</h4>
            {results.map((result, index) => (
              <div 
                key={index} 
                className={`p-3 rounded text-sm ${
                  result.success 
                    ? 'bg-green-100 border border-green-300 text-green-700' 
                    : 'bg-red-100 border border-red-300 text-red-700'
                }`}
              >
                <div className="flex justify-between items-center mb-1">
                  <span className="font-medium">
                    {result.success ? '✅' : '❌'} {result.test}
                  </span>
                  <span className="text-xs opacity-75">{result.timestamp}</span>
                </div>
                <pre className="text-xs whitespace-pre-wrap overflow-auto">
                  {JSON.stringify(result.data, null, 2)}
                </pre>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};