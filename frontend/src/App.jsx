import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout/Layout';
import Dashboard from './pages/Dashboard';
import EmailsPage from './pages/EmailsPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Dashboard />} />
            <Route path="emails" element={<EmailsPage />} />
            <Route path="calendario" element={<div className="p-8">Calendario (TODO)</div>} />
            <Route path="regole" element={<div className="p-8">Regole (TODO)</div>} />
            <Route path="repository" element={<div className="p-8">Repository (TODO)</div>} />
            <Route path="config" element={<div className="p-8">Config (TODO)</div>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
