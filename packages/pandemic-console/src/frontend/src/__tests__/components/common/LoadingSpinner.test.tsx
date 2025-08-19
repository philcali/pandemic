/**
 * Tests for LoadingSpinner component
 */

import { render, screen } from '@testing-library/react';
import { LoadingSpinner } from '../../../components/common/LoadingSpinner';

describe('LoadingSpinner', () => {
  it('should render with default text', () => {
    render(<LoadingSpinner />);
    
    expect(screen.getByText('Loading...')).toBeInTheDocument();
  });

  it('should render with custom text', () => {
    render(<LoadingSpinner text="Please wait..." />);
    
    expect(screen.getByText('Please wait...')).toBeInTheDocument();
  });

  it('should apply custom className', () => {
    render(<LoadingSpinner className="custom-spinner" />);
    
    const container = screen.getByText('Loading...').parentElement;
    expect(container).toHaveClass('custom-spinner');
  });

  it('should render small spinner when size prop is provided', () => {
    render(<LoadingSpinner size="sm" />);
    
    const spinner = document.querySelector('.spinner-border');
    expect(spinner).toHaveClass('spinner-border-sm');
  });
});