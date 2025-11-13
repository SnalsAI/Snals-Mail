import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  IconButton,
  Box
} from '@mui/material';
import {
  Email as EmailIcon,
  Dashboard as DashboardIcon,
  Settings as SettingsIcon,
  Logout as LogoutIcon
} from '@mui/icons-material';

function Navbar({ onLogout }) {
  const navigate = useNavigate();

  return (
    <AppBar position="static">
      <Toolbar>
        <EmailIcon sx={{ mr: 2 }} />
        <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
          Snals-Mail
        </Typography>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            color="inherit"
            startIcon={<DashboardIcon />}
            onClick={() => navigate('/')}
          >
            Dashboard
          </Button>
          <Button
            color="inherit"
            startIcon={<EmailIcon />}
            onClick={() => navigate('/emails')}
          >
            Email
          </Button>
          <Button
            color="inherit"
            startIcon={<SettingsIcon />}
            onClick={() => navigate('/settings')}
          >
            Impostazioni
          </Button>
          <IconButton color="inherit" onClick={onLogout}>
            <LogoutIcon />
          </IconButton>
        </Box>
      </Toolbar>
    </AppBar>
  );
}

export default Navbar;
