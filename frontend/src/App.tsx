import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Emails from './pages/Emails'
import EmailDetail from './pages/EmailDetail'
import Calendar from './pages/Calendar'
import Rules from './pages/Rules'
import Documents from './pages/Documents'
import Actions from './pages/Actions'
import Settings from './pages/Settings'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="emails" element={<Emails />} />
          <Route path="emails/:id" element={<EmailDetail />} />
          <Route path="calendar" element={<Calendar />} />
          <Route path="rules" element={<Rules />} />
          <Route path="documents" element={<Documents />} />
          <Route path="actions" element={<Actions />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
