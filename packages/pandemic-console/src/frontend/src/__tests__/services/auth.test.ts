/**
 * Tests for AuthService
 */

import { AuthService } from '../../services/auth';
import { AuthResponse, UserInfo } from '../../types/api';

// Mock localStorage
const localStorageMock = {
  getItem: jest.fn(),
  setItem: jest.fn(),
  removeItem: jest.fn(),
  clear: jest.fn(),
};
Object.defineProperty(window, 'localStorage', { value: localStorageMock });

describe('AuthService', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('token management', () => {
    it('should set and get token', () => {
      const token = 'test-token';
      AuthService.setToken(token);
      
      expect(localStorageMock.setItem).toHaveBeenCalledWith('pandemic_auth_token', token);
    });

    it('should remove token', () => {
      AuthService.removeToken();
      
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('pandemic_auth_token');
    });
  });

  describe('authentication status', () => {
    it('should return false when no token', () => {
      localStorageMock.getItem.mockReturnValue(null);
      
      const result = AuthService.isAuthenticated();
      
      expect(result).toBe(false);
    });

    it('should return false for invalid token format', () => {
      localStorageMock.getItem.mockReturnValue('invalid-token');
      
      const result = AuthService.isAuthenticated();
      
      expect(result).toBe(false);
    });

    it('should return true for valid non-expired token', () => {
      const futureExp = Math.floor(Date.now() / 1000) + 3600;
      const payload = { exp: futureExp };
      const token = `header.${btoa(JSON.stringify(payload))}.signature`;
      
      localStorageMock.getItem.mockReturnValue(token);
      
      const result = AuthService.isAuthenticated();
      
      expect(result).toBe(true);
    });
  });

  describe('role management', () => {
    beforeEach(() => {
      const user: UserInfo = {
        username: 'testuser',
        roles: ['admin', 'operator']
      };
      localStorageMock.getItem.mockReturnValue(JSON.stringify(user));
    });

    it('should check if user has specific role', () => {
      const hasAdmin = AuthService.hasRole('admin');
      const hasUser = AuthService.hasRole('user');
      
      expect(hasAdmin).toBe(true);
      expect(hasUser).toBe(false);
    });
  });
});