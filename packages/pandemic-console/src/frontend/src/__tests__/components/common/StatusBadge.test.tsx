/**
 * Tests for StatusBadge component
 */

import { render, screen } from '@testing-library/react';
import { StatusBadge } from '../../../components/common/StatusBadge';

describe('StatusBadge', () => {
  it('should render running state correctly', () => {
    render(<StatusBadge state="running" />);
    
    const badge = screen.getByText(/running/i);
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('bg-success');
  });

  it('should render stopped state correctly', () => {
    render(<StatusBadge state="stopped" />);
    
    const badge = screen.getByText(/stopped/i);
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('bg-secondary');
  });

  it('should render failed state correctly', () => {
    render(<StatusBadge state="failed" />);
    
    const badge = screen.getByText(/failed/i);
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('bg-danger');
  });

  it('should render starting state correctly', () => {
    render(<StatusBadge state="starting" />);
    
    const badge = screen.getByText(/starting/i);
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass('bg-warning');
  });

  it('should apply custom className', () => {
    render(<StatusBadge state="running" className="custom-class" />);
    
    const badge = screen.getByText(/running/i);
    expect(badge).toHaveClass('custom-class');
  });
});