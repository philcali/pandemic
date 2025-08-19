/**
 * Tests for useApi hooks
 */

import { renderHook, waitFor } from '@testing-library/react';
import { useApi, usePolling } from '../../hooks/useApi';

// Mock API function
const mockApiCall = jest.fn();

describe('useApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should return loading state initially', () => {
    mockApiCall.mockResolvedValue({ data: 'test' });
    
    const { result } = renderHook(() => useApi(mockApiCall));
    
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBeNull();
  });

  it('should return data on successful API call', async () => {
    const testData = { id: 1, name: 'test' };
    mockApiCall.mockResolvedValue(testData);
    
    const { result } = renderHook(() => useApi(mockApiCall));
    
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    
    expect(result.current.data).toEqual(testData);
    expect(result.current.error).toBeNull();
  });

  it('should return error on failed API call', async () => {
    const errorMessage = 'API Error';
    mockApiCall.mockRejectedValue(new Error(errorMessage));
    
    const { result } = renderHook(() => useApi(mockApiCall));
    
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe(errorMessage);
  });

  it('should handle API response error format', async () => {
    const apiError = {
      response: {
        data: {
          detail: 'Detailed API error'
        }
      }
    };
    mockApiCall.mockRejectedValue(apiError);
    
    const { result } = renderHook(() => useApi(mockApiCall));
    
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    
    expect(result.current.error).toBe('Detailed API error');
  });

  it('should refetch data when refetch is called', async () => {
    const testData = { id: 1, name: 'test' };
    mockApiCall.mockResolvedValue(testData);
    
    const { result } = renderHook(() => useApi(mockApiCall));
    
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    
    // Clear the mock and set new data
    mockApiCall.mockClear();
    const newData = { id: 2, name: 'updated' };
    mockApiCall.mockResolvedValue(newData);
    
    // Call refetch
    result.current.refetch();
    
    await waitFor(() => {
      expect(result.current.data).toEqual(newData);
    });
    
    expect(mockApiCall).toHaveBeenCalledTimes(1);
  });
});

describe('usePolling', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('should poll API at specified interval', async () => {
    const testData = { id: 1, name: 'test' };
    mockApiCall.mockResolvedValue(testData);
    
    const { result } = renderHook(() => usePolling(mockApiCall, 1000));
    
    // Initial call
    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    expect(mockApiCall).toHaveBeenCalledTimes(2);
    
    // Advance timer and check for second call
    jest.advanceTimersByTime(1000);
    
    await waitFor(() => {
      expect(mockApiCall).toHaveBeenCalledTimes(3);
    });
  });

  it('should cleanup interval on unmount', () => {
    const clearIntervalSpy = jest.spyOn(global, 'clearInterval');
    mockApiCall.mockResolvedValue({ data: 'test' });
    
    const { unmount } = renderHook(() => usePolling(mockApiCall, 1000));
    
    unmount();
    
    expect(clearIntervalSpy).toHaveBeenCalled();
    clearIntervalSpy.mockRestore();
  });
});