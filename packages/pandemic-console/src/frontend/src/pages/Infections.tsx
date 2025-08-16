/**
 * Infections management page
 */

import React, { useState } from 'react';
import { Container, Row, Col, Button, Alert, Card } from 'react-bootstrap';
import { useNavigate } from 'react-router-dom';
import { usePolling } from '../hooks/useApi';
import { InfectionTable } from '../components/Infections/InfectionTable';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';

export const Infections: React.FC = () => {
  const navigate = useNavigate();
  const { hasAnyRole } = useAuth();
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState('');
  const [actionSuccess, setActionSuccess] = useState('');

  const { data: infections, loading, error, refetch } = usePolling(
    () => api.getInfections(),
    5000
  );

  const canManage = hasAnyRole(['admin', 'operator']);

  const handleAction = async (action: () => Promise<any>, successMessage: string) => {
    setActionLoading(true);
    setActionError('');
    setActionSuccess('');

    try {
      await action();
      setActionSuccess(successMessage);
      setTimeout(() => refetch(), 1000); // Refresh after action
    } catch (err: any) {
      setActionError(err.response?.data?.detail || err.message || 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleStart = (id: string) => {
    handleAction(
      () => api.startInfection(id),
      'Infection started successfully'
    );
  };

  const handleStop = (id: string) => {
    handleAction(
      () => api.stopInfection(id),
      'Infection stopped successfully'
    );
  };

  const handleRestart = (id: string) => {
    handleAction(
      () => api.restartInfection(id),
      'Infection restarted successfully'
    );
  };

  const handleViewDetails = (id: string) => {
    navigate(`/infections/${id}`);
  };

  if (loading && !infections) {
    return (
      <Container fluid>
        <LoadingSpinner text="Loading infections..." className="mt-5" />
      </Container>
    );
  }

  return (
    <Container fluid>
      <Row className="mb-4">
        <Col>
          <div className="d-flex justify-content-between align-items-center">
            <div>
              <h1>Infections</h1>
              <p className="text-muted">Manage and monitor infection lifecycle</p>
            </div>
            {canManage && (
              <Button variant="primary" disabled>
                Install New (Coming Soon)
              </Button>
            )}
          </div>
        </Col>
      </Row>

      {error && (
        <Row className="mb-4">
          <Col>
            <Alert variant="danger">
              <Alert.Heading>Error Loading Infections</Alert.Heading>
              <p>{error}</p>
            </Alert>
          </Col>
        </Row>
      )}

      {actionError && (
        <Row className="mb-4">
          <Col>
            <Alert variant="danger" dismissible onClose={() => setActionError('')}>
              {actionError}
            </Alert>
          </Col>
        </Row>
      )}

      {actionSuccess && (
        <Row className="mb-4">
          <Col>
            <Alert variant="success" dismissible onClose={() => setActionSuccess('')}>
              {actionSuccess}
            </Alert>
          </Col>
        </Row>
      )}

      <Row>
        <Col>
          <Card>
            <Card.Header>
              <div className="d-flex justify-content-between align-items-center">
                <span>
                  <strong>Infections</strong> 
                  {infections && (
                    <span className="text-muted ms-2">
                      ({infections.runningCount} running / {infections.totalCount} total)
                    </span>
                  )}
                </span>
                {loading && <LoadingSpinner size="sm" text="" />}
              </div>
            </Card.Header>
            <Card.Body className="p-0">
              {infections && infections.infections.length > 0 ? (
                <InfectionTable
                  infections={infections.infections}
                  onStart={handleStart}
                  onStop={handleStop}
                  onRestart={handleRestart}
                  onViewDetails={handleViewDetails}
                  loading={actionLoading}
                />
              ) : (
                <div className="text-center p-4">
                  <p className="text-muted">No infections found</p>
                </div>
              )}
            </Card.Body>
          </Card>
        </Col>
      </Row>
    </Container>
  );
};