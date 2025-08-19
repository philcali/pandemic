/**
 * Tests for App component
 */

import React from 'react';
import { render } from '@testing-library/react';
import App from '../App';

// Mock the API service
jest.mock('../services/api', () => ({
  __esModule: true,
  default: {
    login: jest.fn(),
    getCurrentUser: jest.fn(),
    logout: jest.fn(),
    getHealth: jest.fn(),
    getStatus: jest.fn(),
    getInfections: jest.fn(),
  },
  api: {
    login: jest.fn(),
    getCurrentUser: jest.fn(),
    logout: jest.fn(),
    getHealth: jest.fn(),
    getStatus: jest.fn(),
    getInfections: jest.fn(),
  }
}));

// Mock AuthService
jest.mock('../services/auth', () => ({
  AuthService: {
    isAuthenticated: jest.fn(() => false),
    setToken: jest.fn(),
    setUser: jest.fn(),
    logout: jest.fn(),
    hasRole: jest.fn(() => false),
    hasAnyRole: jest.fn(() => false),
    getUser: jest.fn(() => null),
    getToken: jest.fn(() => null),
  }
}));

describe('App', () => {
  it('should render without crashing', () => {
    const { container } = render(<App />);
    expect(container).toBeInTheDocument();
  });
});