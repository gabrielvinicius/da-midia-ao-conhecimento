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
