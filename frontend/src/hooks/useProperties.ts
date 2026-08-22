import { useState, useCallback } from 'react';
import { PropertyAPI } from '../api/properties';
import type { Property } from '../components/PropertyPane/PropertyPane';

export const useProperties = () => {
  const [properties, setProperties] = useState<Property[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchProperties = useCallback(async (filters: any = {}) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await PropertyAPI.getProperties(filters);
      setProperties(data);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch properties');
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const getPropertyDetails = useCallback(async (id: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await PropertyAPI.getPropertyDetails(id);
      // Optional: update the specific property in the list
      setProperties(prev => prev.map(p => p.id === id ? data : p));
      return data;
    } catch (err: any) {
      setError(err.message || 'Failed to fetch property details');
      console.error(err);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    properties,
    isLoading,
    error,
    fetchProperties,
    getPropertyDetails,
    setProperties, // Expose setter to allow overriding from WebSocket shortlist updates
  };
};
