/**
 * Status badge component for infection states
 */

import React from 'react';
import { Badge } from 'react-bootstrap';
import { InfectionState } from '../../types/infection';

interface StatusBadgeProps {
  state: InfectionState;
  className?: string;
}

const getVariant = (state: InfectionState): string => {
  switch (state) {
    case 'running':
      return 'success';
    case 'stopped':
      return 'secondary';
    case 'starting':
      return 'warning';
    case 'stopping':
      return 'warning';
    case 'failed':
      return 'danger';
    default:
      return 'light';
  }
};

const getIcon = (state: InfectionState): string => {
  switch (state) {
    case 'running':
      return '🟢';
    case 'stopped':
      return '🔴';
    case 'starting':
      return '🟡';
    case 'stopping':
      return '🟡';
    case 'failed':
      return '❌';
    default:
      return '⚪';
  }
};

export const StatusBadge: React.FC<StatusBadgeProps> = ({ state, className = '' }) => {
  return (
    <Badge bg={getVariant(state)} className={className}>
      {getIcon(state)} {state.charAt(0).toUpperCase() + state.slice(1)}
    </Badge>
  );
};