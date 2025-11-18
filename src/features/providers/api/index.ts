import api from "@/lib/api";

export type ProviderType = "storage" | "transcription" | "summarization" | "sentiment" | "topics";

export const getProviders = async (type: ProviderType): Promise<string[]> => {
  const response = await api.get<string[]>(`/providers/${type}`);
  return response.data;
};
