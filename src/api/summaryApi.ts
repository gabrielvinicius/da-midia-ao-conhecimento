import api from "@/lib/api";
import { Summary, SummarizationReprocessResponse } from "../types";

export const getSummaryByMediaId = async (mediaId: string): Promise<Summary> => {
  const response = await api.get(`/summaries/?media_id=${mediaId}`);
  return response.data;
};

export const reprocessSummarization = async (
  mediaId: string,
  options?: {
    provider?: string;
    maxLength?: number;
    force?: boolean;
  }
): Promise<SummarizationReprocessResponse> => {
  const formData = new FormData();
  formData.append("media_id", mediaId);
  
  if (options?.provider) {
    formData.append("provider", options.provider);
  }
  if (options?.maxLength) {
    formData.append("max_length", options.maxLength.toString());
  }
  if (options?.force !== undefined) {
    formData.append("force", options.force.toString());
  }

  const response = await api.post<SummarizationReprocessResponse>("/summaries/reprocess", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });
  return response.data;
};

export default { getSummaryByMediaId, reprocessSummarization };
