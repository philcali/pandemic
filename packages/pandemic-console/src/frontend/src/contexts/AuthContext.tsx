/**
 * Authentication context for managing user state
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { UserInfo } from '../types/api';
import { AuthService } from '../services/auth';
import api from '../services/api';

interface AuthContextType {
  user: UserInfo | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  hasRole: (role: string) => boolean;
  hasAnyRole: (roles: string[]) => boolean;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    // Check if user is already authenticated on app start
    const initAuth = async () => {
      if (AuthService.isAuthenticated()) {
        try {
          // Try to get current user info
          const currentUser = await api.getCurrentUser();
          setUser(currentUser);
          AuthService.setUser(currentUser);
        } catch (error) {
          // Token might be invalid, clear it
          console.warn('Failed to get current user, clearing auth:', error);
          AuthService.logout();
        }
      }
      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (username: string, password: string): Promise<void> => {
    try {
      const authResponse = await api.login({ username, password });
      
      // Set token first so subsequent API calls work
      AuthService.setToken(authResponse.access_token);
      
      const currentUser = await api.getCurrentUser();
      
      AuthService.setUser(currentUser);
      setUser(currentUser);
    } catch (error) {
      // Clear any partial auth state on login failure
      AuthService.logout();
      throw error;
    }
  };

  const logout = (): void => {
    AuthService.logout();
    setUser(null);
  };

  const hasRole = (role: string): boolean => {
    return AuthService.hasRole(role);
  };

  const hasAnyRole = (roles: string[]): boolean => {
    return AuthService.hasAnyRole(roles);
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
    hasRole,
    hasAnyRole,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};