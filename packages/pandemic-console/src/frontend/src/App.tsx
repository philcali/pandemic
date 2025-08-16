/**
 * Main App component with routing
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { Navigation } from './components/Navigation';
import { Login } from './pages/Login';
import { Dashboard } from './pages/Dashboard';
import { Infections } from './pages/Infections';
import { LoadingSpinner } from './components/common/LoadingSpinner';
import 'bootstrap/dist/css/bootstrap.min.css';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <LoadingSpinner text="Loading..." className="vh-100" />;
  }

  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
};

const AppContent: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return <LoadingSpinner text="Loading..." className="vh-100" />;
  }

  return (
    <Router>
      <Routes>
        <Route 
          path="/login" 
          element={isAuthenticated ? <Navigate to="/" replace /> : <Login />} 
        />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <Navigation />
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/infections" element={<Infections />} />
                <Route path="/host" element={
                  <div className="container-fluid mt-5 text-center">
                    <h2>Host Monitoring</h2>
                    <p className="text-muted">Coming soon...</p>
                  </div>
                } />
                <Route path="/infections/:id" element={
                  <div className="container-fluid mt-5 text-center">
                    <h2>Infection Details</h2>
                    <p className="text-muted">Coming soon...</p>
                  </div>
                } />
                <Route path="*" element={<Navigate to="/" replace />} />
              </Routes>
            </ProtectedRoute>
          }
        />
      </Routes>
    </Router>
  );
};

const App: React.FC = () => {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
};

export default App;