import React, { useState } from 'react';
import {
  Container,
  Paper,
  TextField,
  Button,
  Typography,
  Box,
  Alert
} from '@mui/material';
import { Email as EmailIcon } from '@mui/icons-material';
import { authAPI } from '../services/api';

function Login({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [isRegister, setIsRegister] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = isRegister
        ? await authAPI.register(email, password, name)
        : await authAPI.login(email, password);

      onLogin(response.data.token);
    } catch (err) {
      setError(err.response?.data?.error || 'Errore durante l\'autenticazione');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="sm" sx={{ mt: 8 }}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
          <EmailIcon sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
          <Typography component="h1" variant="h4" gutterBottom>
            Snals-Mail
          </Typography>
          <Typography variant="subtitle1" color="text.secondary" gutterBottom>
            Analizzatore Email dello SNALS
          </Typography>

          {error && (
            <Alert severity="error" sx={{ width: '100%', mt: 2 }}>
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3, width: '100%' }}>
            {isRegister && (
              <TextField
                margin="normal"
                required
                fullWidth
                label="Nome"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus={isRegister}
              />
            )}
            <TextField
              margin="normal"
              required
              fullWidth
              label="Email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoFocus={!isRegister}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              label="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2 }}
              disabled={loading}
            >
              {loading ? 'Caricamento...' : (isRegister ? 'Registrati' : 'Accedi')}
            </Button>
            <Button
              fullWidth
              onClick={() => {
                setIsRegister(!isRegister);
                setError('');
              }}
            >
              {isRegister ? 'Hai già un account? Accedi' : 'Non hai un account? Registrati'}
            </Button>
          </Box>
        </Box>
      </Paper>
    </Container>
  );
}

export default Login;
