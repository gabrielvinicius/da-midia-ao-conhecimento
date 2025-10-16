import api from "@/lib/api";
import { Media } from "@/types";

export interface UploadMediaParams {
  file: File;
  storageProvider: string;
  transcriptionProvider?: string;
  summarizationProvider?: string;
}

export const listMedia = async (): Promise<Media[]> => {
  const response = await api.get<Media[]>("/media/");
  return response.data;
};

export const getMediaById = async (id: string): Promise<Media> => {
  const response = await api.get<Media>(`/media/${id}`);
  return response.data;
};

export const uploadMedia = async (params: UploadMediaParams): Promise<Media> => {
  console.log('🚀 Upload API called with params:', params);
  
  // Validações iniciais
  if (!params.file) {
    throw new Error('Arquivo é obrigatório');
  }
  
  if (!(params.file instanceof File)) {
    throw new Error('Parâmetro file deve ser uma instância de File');
  }
  
  // Verificar se há token
  const token = localStorage.getItem('token');
  console.log('🔑 Token presente:', !!token, token ? `(${token.substring(0, 20)}...)` : 'Nenhum');
  
  const { file, ...queryParams } = params;
  
  // Criar FormData com validações
  const formData = new FormData();
  
  console.log('📁 Arquivo para upload:', {
    name: file.name,
    size: file.size,
    type: file.type,
    lastModified: file.lastModified,
    isValidFile: file instanceof File
  });
  
  // Anexar arquivo com nome específico
  formData.append("file", file, file.name);

  // Debug FormData contents - método mais detalhado
  console.log('🔍 FormData entries:');
  for (let [key, value] of formData.entries()) {
    if (value instanceof File) {
      console.log(`  ${key}: File {
        name: "${value.name}",
        size: ${value.size} bytes,
        type: "${value.type}",
        lastModified: ${value.lastModified}
      }`);
    } else {
      console.log(`  ${key}: ${value}`);
    }
  }

  try {
    // Converter camelCase para snake_case para o backend
    const backendParams: any = {};
    if (queryParams.storageProvider) {
      backendParams.storage_provider = queryParams.storageProvider;
    }
    if (queryParams.transcriptionProvider) {
      backendParams.transcription_provider = queryParams.transcriptionProvider;
    }
    if (queryParams.summarizationProvider) {
      backendParams.summarization_provider = queryParams.summarizationProvider;
    }
    
    console.log('🔄 Convertendo params:', queryParams, '→', backendParams);
    
    // Construir URL com query params convertidos
    const queryString = new URLSearchParams(backendParams).toString();
    const url = queryString ? `/media/?${queryString}` : '/media/';
    
    console.log('🎯 Final URL:', url);
    console.log('📋 Backend params:', backendParams);
    console.log('🌐 Full API URL:', `${api.defaults.baseURL}${url}`);
    
    // Fazer upload com configurações específicas
    const response = await api.post<Media>(url, formData, {
      headers: {
        // IMPORTANTE: Não definir Content-Type - deixar o browser definir o boundary
        // 'Content-Type': 'multipart/form-data' // ❌ NUNCA fazer isso
      },
      timeout: 300000, // 5 minutos timeout para uploads grandes
      maxContentLength: Infinity,
      maxBodyLength: Infinity,
      onUploadProgress: (progressEvent) => {
        if (progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          console.log(`📈 Upload progress: ${percentCompleted}% (${progressEvent.loaded}/${progressEvent.total} bytes)`);
        }
      }
    });
    
    console.log('✅ Upload response:', response.data);
    return response.data;
  } catch (error: any) {
    console.error('❌ Upload API error:', error);
    if (error.response) {
      console.error('📊 Status:', error.response.status);
      console.error('📋 Headers:', error.response.headers);
      console.error('📄 Data:', error.response.data);
      
      // Log detalhado do erro de validação
      if (error.response.status === 422 && error.response.data?.detail) {
        console.error('🔍 Detalhes da validação:', error.response.data.detail);
      }
    }
    throw error;
  }
};

export const reprocessMedia = async (mediaId: string): Promise<{ message: string }> => {
  const response = await api.post<{ message: string }>(`/media/${mediaId}/reprocess`);
  return response.data;
};
