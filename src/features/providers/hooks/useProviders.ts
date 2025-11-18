import { ProviderType } from '../api';
import { useProviderList } from '../context/ProvidersContext';

export const useProviders = (type: ProviderType) => useProviderList(type);
