/**
 * Main dashboard page
 */

import React from 'react';
import { Container, Row, Col, Alert } from 'react-bootstrap';
import { usePolling } from '../hooks/useApi';
import { HealthCards } from '../components/Dashboard/HealthCards';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import api from '../services/api';

export const Dashboard: React.FC = () => {
  const { data: status, loading: statusLoading, error: statusError } = usePolling(
    () => api.getStatus(),
    5000
  );

  const { data: health, loading: healthLoading, error: healthError } = usePolling(
    () => api.getHealth(),
    10000
  );

  const { data: infections, loading: infectionsLoading, error: infectionsError } = usePolling(
    () => api.getInfections(),
    5000
  );

  const isLoading = statusLoading || healthLoading || infectionsLoading;
  const hasError = statusError || healthError || infectionsError;

  if (isLoading && !status && !health && !infections) {
    return (
      <Container fluid>
        <LoadingSpinner text="Loading dashboard..." className="mt-5" />
      </Container>
    );
  }

  return (
    <Container fluid>
      <Row className="mb-4">
        <Col>
          <h1>Dashboard</h1>
          <p className="text-muted">System overview and health monitoring</p>
        </Col>
      </Row>

      {hasError && (
        <Row className="mb-4">
          <Col>
            <Alert variant="warning">
              <Alert.Heading>Connection Issues</Alert.Heading>
              <p>Some data may be outdated due to connection issues with the backend.</p>
              <ul className="mb-0">
                {statusError && <li>Status: {statusError}</li>}
                {healthError && <li>Health: {healthError}</li>}
                {infectionsError && <li>Infections: {infectionsError}</li>}
              </ul>
            </Alert>
          </Col>
        </Row>
      )}

      <HealthCards status={status} health={health} infections={infections} />

      <Row className="mt-4">
        <Col md={8}>
          <div className="bg-light p-4 rounded">
            <h5>Recent Activity</h5>
            <p className="text-muted">Activity feed coming soon...</p>
          </div>
        </Col>
        <Col md={4}>
          <div className="bg-light p-4 rounded">
            <h5>Quick Actions</h5>
            <p className="text-muted">Quick actions coming soon...</p>
          </div>
        </Col>
      </Row>
    </Container>
  );
};