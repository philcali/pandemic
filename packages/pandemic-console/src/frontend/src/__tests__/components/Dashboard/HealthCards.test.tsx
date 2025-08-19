/**
 * Tests for HealthCards component
 */

import { render, screen } from '@testing-library/react';
import { HealthCards } from '../../../components/Dashboard/HealthCards';
import { StatusResponse, HealthResponse } from '../../../types/api';
import { InfectionListResponse } from '../../../types/infection';

describe('HealthCards', () => {
  const mockStatus: StatusResponse = {
    daemon: 'active',
    uptime: '2 days, 3 hours'
  };

  const mockHealth: HealthResponse = {
    status: 'healthy'
  };

  const mockInfections: InfectionListResponse = {
    infections: [],
    totalCount: 5,
    runningCount: 3
  };

  it('should render all health cards', () => {
    render(
      <HealthCards 
        status={mockStatus} 
        health={mockHealth} 
        infections={mockInfections} 
      />
    );

    expect(screen.getByText('Host Health')).toBeInTheDocument();
    expect(screen.getByText('Infections')).toBeInTheDocument();
    expect(screen.getByText('Daemon')).toBeInTheDocument();
    expect(screen.getByText('Uptime')).toBeInTheDocument();
  });

  it('should display healthy status correctly', () => {
    render(
      <HealthCards 
        status={mockStatus} 
        health={mockHealth} 
        infections={mockInfections} 
      />
    );

    expect(screen.getByText('Healthy')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('should display infection counts correctly', () => {
    render(
      <HealthCards 
        status={mockStatus} 
        health={mockHealth} 
        infections={mockInfections} 
      />
    );

    expect(screen.getByText('3')).toBeInTheDocument(); // running count
    expect(screen.getByText('/ 5')).toBeInTheDocument(); // total count
  });

  it('should display uptime correctly', () => {
    render(
      <HealthCards 
        status={mockStatus} 
        health={mockHealth} 
        infections={mockInfections} 
      />
    );

    expect(screen.getByText('2 days, 3 hours')).toBeInTheDocument();
  });

  it('should handle null props gracefully', () => {
    render(<HealthCards />);

    expect(screen.getByText('Host Health')).toBeInTheDocument();
    expect(screen.getByText('Unhealthy')).toBeInTheDocument();
    expect(screen.getByText('0')).toBeInTheDocument();
    expect(screen.getByText('/ 0')).toBeInTheDocument();
  });

  it('should display unhealthy status when health check fails', () => {
    const unhealthyStatus = { ...mockHealth, status: 'unhealthy' };
    
    render(
      <HealthCards 
        status={mockStatus} 
        health={unhealthyStatus} 
        infections={mockInfections} 
      />
    );

    expect(screen.getByText('Unhealthy')).toBeInTheDocument();
  });

  it('should display inactive daemon status', () => {
    const inactiveStatus = { ...mockStatus, daemon: 'inactive' };
    
    render(
      <HealthCards 
        status={inactiveStatus} 
        health={mockHealth} 
        infections={mockInfections} 
      />
    );

    expect(screen.getByText('inactive')).toBeInTheDocument();
  });
});