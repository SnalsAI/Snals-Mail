import React from 'react';
import { useQuery } from 'react-query';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Grid,
  Paper,
  Typography,
  Card,
  CardContent,
  CardActionArea,
  Box
} from '@mui/material';
import {
  Email as EmailIcon,
  MarkEmailUnread as UnreadIcon,
  CheckCircle as ReadIcon,
  Warning as SpamIcon
} from '@mui/icons-material';
import Navbar from '../components/Navbar';
import { emailAPI } from '../services/api';

function Dashboard({ onLogout }) {
  const navigate = useNavigate();

  const { data: emailsData } = useQuery('emails', () =>
    emailAPI.getAll({ limit: 100 }).then(res => res.data)
  );

  const stats = React.useMemo(() => {
    if (!emailsData?.emails) return { total: 0, unread: 0, read: 0, spam: 0 };

    const emails = emailsData.emails;
    return {
      total: emails.length,
      unread: emails.filter(e => e.status === 'unread').length,
      read: emails.filter(e => e.status === 'read').length,
      spam: emails.filter(e => e.analysis?.spam_score > 0.5).length
    };
  }, [emailsData]);

  const StatCard = ({ title, value, icon, color, onClick }) => (
    <Card>
      <CardActionArea onClick={onClick}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box>
              <Typography color="text.secondary" gutterBottom>
                {title}
              </Typography>
              <Typography variant="h4">
                {value}
              </Typography>
            </Box>
            <Box sx={{ color, fontSize: 48 }}>
              {icon}
            </Box>
          </Box>
        </CardContent>
      </CardActionArea>
    </Card>
  );

  return (
    <Box sx={{ width: '100%' }}>
      <Navbar onLogout={onLogout} />
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Typography variant="h4" gutterBottom>
          Dashboard
        </Typography>

        <Grid container spacing={3} sx={{ mt: 2 }}>
          <Grid item xs={12} sm={6} md={3}>
            <StatCard
              title="Totale Email"
              value={stats.total}
              icon={<EmailIcon fontSize="inherit" />}
              color="primary.main"
              onClick={() => navigate('/emails')}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <StatCard
              title="Non Lette"
              value={stats.unread}
              icon={<UnreadIcon fontSize="inherit" />}
              color="warning.main"
              onClick={() => navigate('/emails?status=unread')}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <StatCard
              title="Lette"
              value={stats.read}
              icon={<ReadIcon fontSize="inherit" />}
              color="success.main"
              onClick={() => navigate('/emails?status=read')}
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <StatCard
              title="Potenziale Spam"
              value={stats.spam}
              icon={<SpamIcon fontSize="inherit" />}
              color="error.main"
              onClick={() => navigate('/emails')}
            />
          </Grid>
        </Grid>

        <Paper sx={{ mt: 4, p: 3 }}>
          <Typography variant="h6" gutterBottom>
            Benvenuto in Snals-Mail
          </Typography>
          <Typography variant="body1" paragraph>
            Analizzatore email dello SNALS - Sistema completo per la gestione e l'analisi delle email.
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Utilizza la navigazione sopra per:
          </Typography>
          <ul>
            <li>
              <Typography variant="body2" color="text.secondary">
                Visualizzare e gestire le tue email
              </Typography>
            </li>
            <li>
              <Typography variant="body2" color="text.secondary">
                Analizzare automaticamente il contenuto delle email
              </Typography>
            </li>
            <li>
              <Typography variant="body2" color="text.secondary">
                Configurare la sincronizzazione IMAP
              </Typography>
            </li>
          </ul>
        </Paper>
      </Container>
    </Box>
  );
}

export default Dashboard;
