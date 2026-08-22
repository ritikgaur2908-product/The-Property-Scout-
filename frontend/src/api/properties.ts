import { fetchApi } from './client';
import type { Property } from '../components/PropertyPane/PropertyPane';

export const PropertyAPI = {
  getProperties: async (filters: any = {}): Promise<Property[]> => {
    const queryParams = new URLSearchParams(filters).toString();
    const queryString = queryParams ? `?${queryParams}` : '';
    return fetchApi<Property[]>(`/api/properties${queryString}`);
  },

  getPropertyDetails: async (id: string): Promise<Property> => {
    return fetchApi<Property>(`/api/properties/${id}`);
  },
};
