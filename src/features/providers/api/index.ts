import api from "@/lib/api";

export type ProviderType = "storage" | "transcription" | "summarization" | "sentiment" | "topics";

export interface ProviderCatalogEntry {
  name: string;
  label: string;
  description: string;
  type: string;
  version: string;
  status: string;
  capabilities: string[];
  isDefault: boolean;
}

const backendKeyToFrontend: Record<string, ProviderType> = {
  storage: "storage",
  transcription: "transcription",
  summarization: "summarization",
  sentiment_analysis: "sentiment",
  topic_modeling: "topics",
};

export const getProvidersCatalog = async (): Promise<Partial<Record<ProviderType, ProviderCatalogEntry[]>>> => {
  const response = await api.get<Record<string, ProviderCatalogEntry[]>>("/providers/catalog");
  const normalized: Partial<Record<ProviderType, ProviderCatalogEntry[]>> = {};
  Object.entries(response.data ?? {}).forEach(([key, entries]) => {
    const mappedKey = backendKeyToFrontend[key];
    if (mappedKey) {
      normalized[mappedKey] = entries ?? [];
    }
  });
  return normalized;
};
