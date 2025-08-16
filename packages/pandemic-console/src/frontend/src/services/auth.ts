/**
 * Authentication service for JWT token management
 */

import { AuthResponse, UserInfo } from '../types/api';

const TOKEN_KEY = 'pandemic_auth_token';
const USER_KEY = 'pandemic_user_info';

export class AuthService {
  static setToken(token: string): void {
    localStorage.setItem(TOKEN_KEY, token);
  }

  static getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  static removeToken(): void {
    localStorage.removeItem(TOKEN_KEY);
  }

  static setUser(user: UserInfo): void {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  static getUser(): UserInfo | null {
    const userStr = localStorage.getItem(USER_KEY);
    if (userStr) {
      try {
        return JSON.parse(userStr);
      } catch {
        return null;
      }
    }
    return null;
  }

  static removeUser(): void {
    localStorage.removeItem(USER_KEY);
  }

  static isAuthenticated(): boolean {
    const token = this.getToken();
    if (!token) return false;

    // Basic token validation - check if it has 3 parts
    const parts = token.split('.');
    if (parts.length !== 3) return false;

    try {
      const payload = JSON.parse(atob(parts[1]));
      const now = Date.now() / 1000;
      return payload.exp > now;
    } catch {
      // If we can't decode the token, assume it's invalid
      return false;
    }
  }

  static login(authResponse: AuthResponse, user: UserInfo): void {
    this.setToken(authResponse.access_token);
    this.setUser(user);
  }

  static logout(): void {
    this.removeToken();
    this.removeUser();
  }

  static hasRole(role: string): boolean {
    const user = this.getUser();
    return user?.roles.includes(role) || false;
  }

  static hasAnyRole(roles: string[]): boolean {
    const user = this.getUser();
    if (!user) return false;
    return roles.some(role => user.roles.includes(role));
  }
}