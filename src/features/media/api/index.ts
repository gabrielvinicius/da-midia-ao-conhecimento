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
  
  // Verificar se há token
  const token = localStorage.getItem('token');
  console.log('🔑 Token presente:', !!token, token ? `(${token.substring(0, 20)}...)` : 'Nenhum');
  
  const { file, ...queryParams } = params;
  const formData = new FormData();
  formData.append("file", file);

  console.log('📦 FormData created:', {
    fileName: file.name,
    fileSize: file.size,
    fileType: file.type,
    queryParams
  });

  // Debug FormData contents
  console.log('🔍 FormData entries:');
  for (let [key, value] of formData.entries()) {
    console.log(`  ${key}:`, value instanceof File ? `File(${value.name}, ${value.size}B)` : value);
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
    
    const response = await api.post<Media>(url, formData, {
      headers: {
        // Não definir Content-Type para multipart/form-data - deixar browser definir
      },
      timeout: 300000, // 5 minutos timeout para uploads grandes
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1));
        console.log(`📈 Upload progress: ${percentCompleted}%`);
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
    }
    throw error;
  }
};

export const reprocessMedia = async (mediaId: string): Promise<{ message: string }> => {
  const response = await api.post<{ message: string }>(`/media/${mediaId}/reprocess`);
  return response.data;
};
