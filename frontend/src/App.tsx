import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Emails from './pages/Emails'
import EmailDetail from './pages/EmailDetail'
import Actions from './pages/Actions'
import Rules from './pages/Rules'
import Calendar from './pages/Calendar'
import Settings from './pages/Settings'

function App() {
  return (
    <Routes>
      <Route path="/" element={<Layout />}>
        <Route index element={<Dashboard />} />
        <Route path="emails" element={<Emails />} />
        <Route path="emails/:id" element={<EmailDetail />} />
        <Route path="actions" element={<Actions />} />
        <Route path="rules" element={<Rules />} />
        <Route path="calendar" element={<Calendar />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}

export default App
