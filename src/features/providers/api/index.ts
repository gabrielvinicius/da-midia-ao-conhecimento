import api from "@/lib/api";

export type ProviderType = "storage" | "transcription" | "summarization" | "sentiment" | "topics";

export const getProviders = async (type: ProviderType): Promise<string[]> => {
  const response = await api.get<string[]>(`/providers/${type}`);
  return response.data;
};

const backendKeyToFrontend: Record<string, ProviderType> = {
  storage: "storage",
  transcription: "transcription",
  summarization: "summarization",
  sentiment_analysis: "sentiment",
  topic_modeling: "topics",
};

export const getProvidersMap = async (): Promise<Partial<Record<ProviderType, string[]>>> => {
  const response = await api.get<Record<string, string[]>>("/providers/");
  const normalized: Partial<Record<ProviderType, string[]>> = {};
  Object.entries(response.data ?? {}).forEach(([key, list]) => {
    const mappedKey = backendKeyToFrontend[key];
    if (mappedKey) {
      normalized[mappedKey] = list;
    }
  });
  return normalized;
};
