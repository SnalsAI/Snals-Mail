import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import {
  Container,
  Box,
  Paper,
  Typography,
  Button,
  Chip,
  Divider,
  CircularProgress,
  Grid
} from '@mui/material';
import {
  ArrowBack,
  Analytics as AnalyticsIcon,
  Delete as DeleteIcon,
  Archive as ArchiveIcon
} from '@mui/icons-material';
import { format } from 'date-fns';
import { it } from 'date-fns/locale';
import Navbar from '../components/Navbar';
import { emailAPI } from '../services/api';

function EmailDetail({ onLogout }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: email, isLoading } = useQuery(['email', id], () =>
    emailAPI.getById(id).then(res => res.data)
  );

  const analyzeMutation = useMutation(
    () => emailAPI.analyze(id),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['email', id]);
      }
    }
  );

  const deleteMutation = useMutation(
    () => emailAPI.delete(id),
    {
      onSuccess: () => {
        navigate('/emails');
      }
    }
  );

  const archiveMutation = useMutation(
    () => emailAPI.updateStatus(id, 'archived'),
    {
      onSuccess: () => {
        queryClient.invalidateQueries(['email', id]);
      }
    }
  );

  if (isLoading) {
    return (
      <Box sx={{ width: '100%' }}>
        <Navbar onLogout={onLogout} />
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
          <CircularProgress />
        </Box>
      </Box>
    );
  }

  return (
    <Box sx={{ width: '100%' }}>
      <Navbar onLogout={onLogout} />
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Box sx={{ mb: 3 }}>
          <Button
            startIcon={<ArrowBack />}
            onClick={() => navigate('/emails')}
          >
            Torna alle email
          </Button>
        </Box>

        <Paper sx={{ p: 3 }}>
          <Box sx={{ mb: 3 }}>
            <Typography variant="h5" gutterBottom>
              {email.subject || '(Nessun oggetto)'}
            </Typography>
            <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
              <Chip label={email.status} size="small" />
              {email.analysis?.priority && (
                <Chip label={`Priorità: ${email.analysis.priority}`} size="small" />
              )}
              {email.analysis?.category && (
                <Chip label={email.analysis.category} size="small" />
              )}
            </Box>
          </Box>

          <Divider sx={{ mb: 3 }} />

          <Grid container spacing={2} sx={{ mb: 3 }}>
            <Grid item xs={12}>
              <Typography variant="body2" color="text.secondary">
                Da:
              </Typography>
              <Typography variant="body1">
                {email.from?.name || email.from?.address}
              </Typography>
            </Grid>
            <Grid item xs={12}>
              <Typography variant="body2" color="text.secondary">
                A:
              </Typography>
              <Typography variant="body1">
                {email.to?.map(t => t.name || t.address).join(', ')}
              </Typography>
            </Grid>
            <Grid item xs={12}>
              <Typography variant="body2" color="text.secondary">
                Data:
              </Typography>
              <Typography variant="body1">
                {format(new Date(email.date), 'PPpp', { locale: it })}
              </Typography>
            </Grid>
          </Grid>

          <Divider sx={{ mb: 3 }} />

          <Box sx={{ mb: 3 }}>
            <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
              {email.body?.text || 'Nessun contenuto testuale'}
            </Typography>
          </Box>

          {email.analysis && (
            <>
              <Divider sx={{ mb: 3 }} />
              <Box sx={{ mb: 3 }}>
                <Typography variant="h6" gutterBottom>
                  Analisi Email
                </Typography>
                <Grid container spacing={2}>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="body2" color="text.secondary">
                      Sentiment:
                    </Typography>
                    <Typography variant="body1">
                      {email.analysis.sentiment}
                    </Typography>
                  </Grid>
                  <Grid item xs={12} sm={6}>
                    <Typography variant="body2" color="text.secondary">
                      Spam Score:
                    </Typography>
                    <Typography variant="body1">
                      {(email.analysis.spam_score * 100).toFixed(0)}%
                    </Typography>
                  </Grid>
                  {email.analysis.keywords?.length > 0 && (
                    <Grid item xs={12}>
                      <Typography variant="body2" color="text.secondary">
                        Keywords:
                      </Typography>
                      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
                        {email.analysis.keywords.map((keyword, idx) => (
                          <Chip key={idx} label={keyword} size="small" />
                        ))}
                      </Box>
                    </Grid>
                  )}
                </Grid>
              </Box>
            </>
          )}

          <Divider sx={{ mb: 3 }} />

          <Box sx={{ display: 'flex', gap: 2 }}>
            <Button
              variant="contained"
              startIcon={<AnalyticsIcon />}
              onClick={() => analyzeMutation.mutate()}
              disabled={analyzeMutation.isLoading}
            >
              {analyzeMutation.isLoading ? 'Analizzando...' : 'Analizza Email'}
            </Button>
            <Button
              variant="outlined"
              startIcon={<ArchiveIcon />}
              onClick={() => archiveMutation.mutate()}
              disabled={archiveMutation.isLoading}
            >
              Archivia
            </Button>
            <Button
              variant="outlined"
              color="error"
              startIcon={<DeleteIcon />}
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isLoading}
            >
              Elimina
            </Button>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
}

export default EmailDetail;
