/**
 * Health summary cards for dashboard
 */

import React from 'react';
import { Row, Col, Card } from 'react-bootstrap';
import { StatusResponse, HealthResponse } from '../../types/api';
import { InfectionListResponse } from '../../types/infection';

interface HealthCardsProps {
  status?: StatusResponse | null;
  health?: HealthResponse | null;
  infections?: InfectionListResponse | null;
}

export const HealthCards: React.FC<HealthCardsProps> = ({ status, health, infections }) => {
  const getHealthIcon = (isHealthy: boolean | undefined) => isHealthy ? '🟢' : '🔴';
  const getHealthText = (isHealthy: boolean | undefined) => isHealthy ? 'Healthy' : 'Unhealthy';

  return (
    <Row>
      <Col md={3} className="mb-3">
        <Card className="h-100">
          <Card.Body className="text-center">
            <div className="display-6 mb-2">
              {getHealthIcon(health?.status === 'healthy')}
            </div>
            <Card.Title className="h5">Host Health</Card.Title>
            <Card.Text className="text-muted">
              {getHealthText(health?.status === 'healthy')}
            </Card.Text>
          </Card.Body>
        </Card>
      </Col>

      <Col md={3} className="mb-3">
        <Card className="h-100">
          <Card.Body className="text-center">
            <div className="display-6 mb-2">📊</div>
            <Card.Title className="h5">Infections</Card.Title>
            <Card.Text>
              <span className="h4 text-primary">{infections?.runningCount || 0}</span>
              <span className="text-muted"> / {infections?.totalCount || 0}</span>
            </Card.Text>
            <Card.Text className="text-muted small">Running / Total</Card.Text>
          </Card.Body>
        </Card>
      </Col>

      <Col md={3} className="mb-3">
        <Card className="h-100">
          <Card.Body className="text-center">
            <div className="display-6 mb-2">
              {getHealthIcon(status?.daemon === 'active')}
            </div>
            <Card.Title className="h5">Daemon</Card.Title>
            <Card.Text className="text-muted">
              {status?.daemon === 'active' ? 'Active' : status?.daemon || 'Unknown'}
            </Card.Text>
          </Card.Body>
        </Card>
      </Col>

      <Col md={3} className="mb-3">
        <Card className="h-100">
          <Card.Body className="text-center">
            <div className="display-6 mb-2">⏱️</div>
            <Card.Title className="h5">Uptime</Card.Title>
            <Card.Text className="text-muted">
              {status?.uptime || 'Unknown'}
            </Card.Text>
          </Card.Body>
        </Card>
      </Col>
    </Row>
  );
};