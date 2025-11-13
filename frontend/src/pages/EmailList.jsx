import React, { useState } from 'react';
import { useQuery } from 'react-query';
import { useNavigate, useSearchParams } from 'react-router-dom';
import {
  Container,
  Box,
  List,
  ListItem,
  ListItemButton,
  ListItemText,
  Paper,
  Typography,
  Chip,
  TextField,
  InputAdornment,
  CircularProgress
} from '@mui/material';
import { Search as SearchIcon, Email as EmailIcon } from '@mui/icons-material';
import { format } from 'date-fns';
import { it } from 'date-fns/locale';
import Navbar from '../components/Navbar';
import { emailAPI } from '../services/api';

function EmailList({ onLogout }) {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [search, setSearch] = useState('');

  const status = searchParams.get('status');

  const { data, isLoading } = useQuery(['emails', status, search], () =>
    emailAPI.getAll({ status, search }).then(res => res.data)
  );

  const getStatusColor = (status) => {
    switch (status) {
      case 'unread': return 'warning';
      case 'read': return 'success';
      case 'archived': return 'default';
      default: return 'default';
    }
  };

  const getPriorityColor = (priority) => {
    switch (priority) {
      case 'urgent': return 'error';
      case 'high': return 'warning';
      default: return 'default';
    }
  };

  return (
    <Box sx={{ width: '100%' }}>
      <Navbar onLogout={onLogout} />
      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4">
            Email
          </Typography>
          <TextField
            placeholder="Cerca email..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon />
                </InputAdornment>
              ),
            }}
            sx={{ width: 300 }}
          />
        </Box>

        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
            <CircularProgress />
          </Box>
        ) : data?.emails?.length === 0 ? (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <EmailIcon sx={{ fontSize: 60, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary">
              Nessuna email trovata
            </Typography>
          </Paper>
        ) : (
          <Paper>
            <List>
              {data?.emails?.map((email) => (
                <ListItem key={email._id} disablePadding divider>
                  <ListItemButton onClick={() => navigate(`/emails/${email._id}`)}>
                    <ListItemText
                      primary={
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Typography
                            variant="body1"
                            sx={{
                              fontWeight: email.status === 'unread' ? 700 : 400,
                              flex: 1
                            }}
                          >
                            {email.subject || '(Nessun oggetto)'}
                          </Typography>
                          {email.analysis?.priority && email.analysis.priority !== 'normal' && (
                            <Chip
                              label={email.analysis.priority}
                              size="small"
                              color={getPriorityColor(email.analysis.priority)}
                            />
                          )}
                          <Chip
                            label={email.status}
                            size="small"
                            color={getStatusColor(email.status)}
                          />
                        </Box>
                      }
                      secondary={
                        <Box>
                          <Typography variant="body2" color="text.secondary">
                            Da: {email.from?.name || email.from?.address}
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {format(new Date(email.date), 'PPp', { locale: it })}
                          </Typography>
                        </Box>
                      }
                    />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          </Paper>
        )}
      </Container>
    </Box>
  );
}

export default EmailList;
