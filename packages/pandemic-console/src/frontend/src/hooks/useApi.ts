/**
 * Custom hook for API data fetching with loading and error states
 */

import { useState, useEffect } from 'react';

interface UseApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useApi<T>(
  apiCall: () => Promise<T>,
  dependencies: any[] = []
): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await apiCall();
      setData(result);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, dependencies);

  return {
    data,
    loading,
    error,
    refetch: fetchData,
  };
}

export function usePolling<T>(
  apiCall: () => Promise<T>,
  interval: number = 5000,
  dependencies: any[] = []
): UseApiState<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      if (loading) setError(null);
      const result = await apiCall();
      setData(result);
      if (loading) setLoading(false);
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'An error occurred');
      if (loading) setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
    const intervalId = setInterval(fetchData, interval);
    
    return () => clearInterval(intervalId);
  }, dependencies);

  return {
    data,
    loading,
    error,
    refetch: fetchData,
  };
}