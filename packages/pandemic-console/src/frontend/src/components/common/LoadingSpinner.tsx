/**
 * Loading spinner component
 */

import React from 'react';
import { Spinner } from 'react-bootstrap';

interface LoadingSpinnerProps {
  size?: 'sm' | undefined;
  text?: string;
  className?: string;
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({ 
  size, 
  text = 'Loading...', 
  className = '' 
}) => {
  return (
    <div className={`d-flex align-items-center justify-content-center ${className}`}>
      <Spinner animation="border" size={size} className="me-2" />
      <span>{text}</span>
    </div>
  );
};