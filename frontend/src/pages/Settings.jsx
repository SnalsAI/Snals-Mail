import React, { useState } from 'react';
import { useMutation, useQueryClient } from 'react-query';
import {
  Container,
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Alert,
  Grid
} from '@mui/material';
import { Sync as SyncIcon } from '@mui/icons-material';
import Navbar from '../components/Navbar';
import { emailAPI, authAPI } from '../services/api';

function Settings({ onLogout }) {
  const queryClient = useQueryClient();
  const [imapConfig, setImapConfig] = useState({
    host: '',
    port: 993,
    user: '',
    password: '',
    tls: true
  });
  const [message, setMessage] = useState({ type: '', text: '' });

  const syncMutation = useMutation(
    () => emailAPI.sync(imapConfig),
    {
      onSuccess: (response) => {
        setMessage({
          type: 'success',
          text: `Sincronizzazione completata: ${response.data.syncedEmails} email sincronizzate`
        });
        queryClient.invalidateQueries('emails');
      },
      onError: (error) => {
        setMessage({
          type: 'error',
          text: error.response?.data?.error || 'Errore durante la sincronizzazione'
        });
      }
    }
  );

  const saveConfigMutation = useMutation(
    () => authAPI.updateEmailConfig({
      imapHost: imapConfig.host,
      imapPort: imapConfig.port,
      imapUser: imapConfig.user,
      imapPassword: imapConfig.password
    }),
    {
      onSuccess: () => {
        setMessage({
          type: 'success',
          text: 'Configurazione salvata con successo'
        });
      },
      onError: (error) => {
        setMessage({
          type: 'error',
          text: error.response?.data?.error || 'Errore nel salvataggio'
        });
      }
    }
  );

  const handleSync = () => {
    setMessage({ type: '', text: '' });
    syncMutation.mutate();
  };

  const handleSaveConfig = () => {
    setMessage({ type: '', text: '' });
    saveConfigMutation.mutate();
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Navbar onLogout={onLogout} />
      <Container maxWidth="md" sx={{ mt: 4, mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Impostazioni
        </Typography>

        {message.text && (
          <Alert severity={message.type} sx={{ mb: 3 }}>
            {message.text}
          </Alert>
        )}

        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Configurazione IMAP
          </Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Configura il server IMAP per sincronizzare le tue email
          </Typography>

          <Grid container spacing={2}>
            <Grid item xs={12} sm={8}>
              <TextField
                fullWidth
                label="Host IMAP"
                value={imapConfig.host}
                onChange={(e) => setImapConfig({ ...imapConfig, host: e.target.value })}
                placeholder="imap.gmail.com"
              />
            </Grid>
            <Grid item xs={12} sm={4}>
              <TextField
                fullWidth
                label="Porta"
                type="number"
                value={imapConfig.port}
                onChange={(e) => setImapConfig({ ...imapConfig, port: parseInt(e.target.value) })}
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Username/Email"
                value={imapConfig.user}
                onChange={(e) => setImapConfig({ ...imapConfig, user: e.target.value })}
                placeholder="tua@email.com"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="Password"
                type="password"
                value={imapConfig.password}
                onChange={(e) => setImapConfig({ ...imapConfig, password: e.target.value })}
              />
            </Grid>
          </Grid>

          <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
            <Button
              variant="contained"
              startIcon={<SyncIcon />}
              onClick={handleSync}
              disabled={syncMutation.isLoading || !imapConfig.host || !imapConfig.user || !imapConfig.password}
            >
              {syncMutation.isLoading ? 'Sincronizzando...' : 'Sincronizza Ora'}
            </Button>
            <Button
              variant="outlined"
              onClick={handleSaveConfig}
              disabled={saveConfigMutation.isLoading}
            >
              Salva Configurazione
            </Button>
          </Box>
        </Paper>

        <Paper sx={{ p: 3, mt: 3 }}>
          <Typography variant="h6" gutterBottom>
            Informazioni
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Snals-Mail - Analizzatore Email dello SNALS
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Versione: 1.0.0
          </Typography>
        </Paper>
      </Container>
    </Box>
  );
}

export default Settings;
