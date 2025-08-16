/**
 * Infection table component
 */

import React from 'react';
import { Table, Button, ButtonGroup } from 'react-bootstrap';
import { Infection } from '../../types/infection';
import { StatusBadge } from '../common/StatusBadge';
import { useAuth } from '../../contexts/AuthContext';

interface InfectionTableProps {
  infections: Infection[];
  onStart: (id: string) => void;
  onStop: (id: string) => void;
  onRestart: (id: string) => void;
  onViewDetails: (id: string) => void;
  loading?: boolean;
}

export const InfectionTable: React.FC<InfectionTableProps> = ({
  infections,
  onStart,
  onStop,
  onRestart,
  onViewDetails,
  loading = false
}) => {
  const { hasAnyRole } = useAuth();
  const canManage = hasAnyRole(['admin', 'operator']);

  return (
    <Table responsive striped hover>
      <thead>
        <tr>
          <th>Name</th>
          <th>Status</th>
          <th>Source</th>
          <th>Memory</th>
          <th>CPU</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {infections.map((infection) => (
          <tr key={infection.infectionId}>
            <td>
              <strong>{infection.name}</strong>
              <br />
              <small className="text-muted">{infection.infectionId}</small>
            </td>
            <td>
              <StatusBadge state={infection.state} />
            </td>
            <td>
              <small className="text-muted">
                {infection.source ? (
                  infection.source.length > 40 
                    ? `${infection.source.substring(0, 40)}...`
                    : infection.source
                ) : 'Built-in'}
              </small>
            </td>
            <td>
              <small className="text-muted">
                {infection.systemdStatus?.memoryUsage || 'N/A'}
              </small>
            </td>
            <td>
              <small className="text-muted">
                {infection.systemdStatus?.cpuUsage || 'N/A'}
              </small>
            </td>
            <td>
              <ButtonGroup size="sm">
                <Button
                  variant="outline-primary"
                  onClick={() => onViewDetails(infection.infectionId)}
                  disabled={loading}
                >
                  Details
                </Button>
                
                {canManage && (
                  <>
                    {infection.state === 'stopped' && (
                      <Button
                        variant="outline-success"
                        onClick={() => onStart(infection.infectionId)}
                        disabled={loading}
                      >
                        Start
                      </Button>
                    )}
                    
                    {infection.state === 'running' && (
                      <>
                        <Button
                          variant="outline-warning"
                          onClick={() => onStop(infection.infectionId)}
                          disabled={loading}
                        >
                          Stop
                        </Button>
                        <Button
                          variant="outline-info"
                          onClick={() => onRestart(infection.infectionId)}
                          disabled={loading}
                        >
                          Restart
                        </Button>
                      </>
                    )}
                  </>
                )}
              </ButtonGroup>
            </td>
          </tr>
        ))}
      </tbody>
    </Table>
  );
};