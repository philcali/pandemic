/**
 * Tests for AuthContext
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { AuthProvider, useAuth } from '../../contexts/AuthContext';
import * as api from '../../services/api';

// Mock the API
jest.mock('../../services/api');
const mockApi = api as jest.Mocked<typeof api>;

// Mock AuthService
jest.mock('../../services/auth', () => ({
  AuthService: {
    isAuthenticated: jest.fn(),
    setToken: jest.fn(),
    setUser: jest.fn(),
    logout: jest.fn(),
    hasRole: jest.fn(),
    hasAnyRole: jest.fn(),
  }
}));

// Test component that uses AuthContext
const TestComponent: React.FC = () => {
  const { user, isAuthenticated, isLoading, login, logout } = useAuth();
  
  if (isLoading) return <div>Loading...</div>;
  
  return (
    <div>
      <div data-testid="authenticated">{isAuthenticated.toString()}</div>
      <div data-testid="username">{user?.username || 'No user'}</div>
      <button onClick={() => login('test', 'password')}>Login</button>
      <button onClick={logout}>Logout</button>
    </div>
  );
};

describe('AuthContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('should provide authentication state', async () => {
    const { AuthService } = require('../../services/auth');
    AuthService.isAuthenticated.mockReturnValue(false);
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );
    
    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });
    
    expect(screen.getByTestId('authenticated')).toHaveTextContent('false');
    expect(screen.getByTestId('username')).toHaveTextContent('No user');
  });

  it('should handle successful login', async () => {
    const { AuthService } = require('../../services/auth');
    AuthService.isAuthenticated.mockReturnValue(false);
    
    const mockAuthResponse = {
      access_token: 'test-token',
      token_type: 'Bearer',
      expires_in: 3600
    };
    
    const mockUser = {
      username: 'testuser',
      roles: ['admin']
    };
    
    mockApi.default.login.mockResolvedValue(mockAuthResponse);
    mockApi.default.getCurrentUser.mockResolvedValue(mockUser);
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );
    
    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });
    
    // Simulate login
    const loginButton = screen.getByText('Login');
    loginButton.click();
    
    await waitFor(() => {
      expect(AuthService.setToken).toHaveBeenCalledWith('test-token');
      expect(AuthService.setUser).toHaveBeenCalledWith(mockUser);
    });
  });

  it('should handle logout', async () => {
    const { AuthService } = require('../../services/auth');
    AuthService.isAuthenticated.mockReturnValue(true);
    
    render(
      <AuthProvider>
        <TestComponent />
      </AuthProvider>
    );
    
    await waitFor(() => {
      expect(screen.queryByText('Loading...')).not.toBeInTheDocument();
    });
    
    // Simulate logout
    const logoutButton = screen.getByText('Logout');
    logoutButton.click();
    
    expect(AuthService.logout).toHaveBeenCalled();
  });

  it('should throw error when used outside provider', () => {
    // Suppress console.error for this test
    const consoleSpy = jest.spyOn(console, 'error').mockImplementation();
    
    expect(() => {
      render(<TestComponent />);
    }).toThrow('useAuth must be used within an AuthProvider');
    
    consoleSpy.mockRestore();
  });
});