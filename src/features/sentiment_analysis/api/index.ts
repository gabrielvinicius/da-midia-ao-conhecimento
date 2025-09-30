import api from "@/lib/api";
import { Analysis, AnalysisType } from "@/types";

export const getAnalysis = async (mediaId: string, type: AnalysisType): Promise<Analysis | null> => {
  try {
    const response = await api.get<Analysis>("/analyses/", {
      params: { media_id: mediaId, analysis_type: type },
    });
    return response.data;
  } catch (error: any) {
    if (error.response && error.response.status === 404) {
      // A 404 is not necessarily an error, it just means the analysis isn't ready.
      return null;
    }
    throw error;
  }
};
