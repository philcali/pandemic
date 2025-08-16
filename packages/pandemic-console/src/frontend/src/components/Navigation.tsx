/**
 * Main navigation component
 */

import React from 'react';
import { Navbar, Nav, NavDropdown, Container } from 'react-bootstrap';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export const Navigation: React.FC = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const isActive = (path: string) => location.pathname === path;

  return (
    <Navbar bg="dark" variant="dark" expand="lg" className="mb-3">
      <Container fluid>
        <Navbar.Brand 
          onClick={() => navigate('/')} 
          style={{ cursor: 'pointer' }}
        >
          🦠 Pandemic Console
        </Navbar.Brand>
        
        <Navbar.Toggle aria-controls="basic-navbar-nav" />
        <Navbar.Collapse id="basic-navbar-nav">
          <Nav className="me-auto">
            <Nav.Link 
              onClick={() => navigate('/')}
              active={isActive('/')}
            >
              Dashboard
            </Nav.Link>
            <Nav.Link 
              onClick={() => navigate('/host')}
              active={isActive('/host')}
            >
              Host
            </Nav.Link>
            <Nav.Link 
              onClick={() => navigate('/infections')}
              active={isActive('/infections')}
            >
              Infections
            </Nav.Link>
          </Nav>
          
          <Nav>
            <NavDropdown title={user?.username || 'User'} id="user-dropdown" align="end">
              <NavDropdown.Item disabled>
                {user?.full_name || user?.username}
              </NavDropdown.Item>
              <NavDropdown.Item disabled>
                Roles: {user?.roles.join(', ') || 'None'}
              </NavDropdown.Item>
              <NavDropdown.Divider />
              <NavDropdown.Item onClick={handleLogout}>
                Logout
              </NavDropdown.Item>
            </NavDropdown>
          </Nav>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
};