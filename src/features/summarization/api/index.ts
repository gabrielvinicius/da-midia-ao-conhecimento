import api from "../../../lib/api";
import { Summary } from "../../../types";

export const getSummaryByMediaId = async (mediaId: string): Promise<Summary | null> => {
  try {
    const response = await api.get<Summary>(`/summaries/?media_id=${mediaId}`);
    return response.data;
  } catch (error: any) {
    if (error.response && error.response.status === 404) {
      // A 404 is not an error, it just means the summary isn't ready or doesn't exist.
      return null;
    }
    // For other errors, let the global handler deal with it.
    throw error;
  }
};

export const reprocessSummarization = async (
  mediaId: string,
  options?: {
    provider?: string;
    maxLength?: number;
    force?: boolean;
  }
): Promise<any> => {
  console.log('🔄 Reprocessando sumarização para mídia:', mediaId);
  
  const formData = new FormData();
  formData.append('media_id', mediaId);
  
  if (options?.provider) {
    formData.append('provider', options.provider);
  }
  if (options?.maxLength) {
    formData.append('max_length', options.maxLength.toString());
  }
  if (options?.force !== undefined) {
    formData.append('force', options.force.toString());
  }

  const response = await api.post('/summaries/reprocess', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  
  console.log('✅ Reprocessamento de sumarização iniciado:', response.data);
  return response.data;
};
