import { Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Emails from './pages/Emails'
import EmailDetail from './pages/EmailDetail'
import Actions from './pages/Actions'
import Rules from './pages/Rules'
import Calendar from './pages/Calendar'
import Schools from './pages/Schools'
import RAGDocuments from './pages/RAGDocuments'
import KnowledgeBase from './pages/KnowledgeBase'
import ChatRAG from './pages/ChatRAG'
import Spam from './pages/Spam'
import RicevutePEC from './pages/RicevutePEC'
import Interpelli from './pages/Interpelli'
import ClassiConcorso from './pages/ClassiConcorso'
import Settings from './pages/Settings'
import Debug from './pages/Debug'
import Delegati from './pages/Delegati'
import Reports from './pages/Reports'
import NLPTraining from './pages/NLPTraining'
import Bugs from './pages/Bugs'
import PWAInstallBanner from './components/PWAInstallBanner'
import { usePWA } from './hooks/usePWA'

function App() {
  const { isOnline } = usePWA()

  return (
    <>
      {/* Offline indicator */}
      {!isOnline && (
        <div className="fixed top-0 left-0 right-0 z-50 bg-red-500 text-white text-center py-2 px-4 text-sm font-medium">
          <span className="inline-flex items-center gap-2">
            <span className="w-2 h-2 bg-white rounded-full animate-pulse"></span>
            Sei offline - Alcune funzionalità potrebbero non essere disponibili
          </span>
        </div>
      )}

      {/* Routes */}
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<Emails />} />
          <Route path="emails" element={<Emails />} />
          <Route path="emails/:id" element={<EmailDetail />} />
          <Route path="actions" element={<Actions />} />
          <Route path="rules" element={<Rules />} />
          <Route path="delegati" element={<Delegati />} />
          <Route path="calendar" element={<Calendar />} />
          <Route path="schools" element={<Schools />} />
          <Route path="interpelli" element={<Interpelli />} />
          <Route path="classi-concorso" element={<ClassiConcorso />} />
          <Route path="knowledge" element={<KnowledgeBase />} />
          <Route path="rag-documents" element={<RAGDocuments />} />
          <Route path="chat-rag" element={<ChatRAG />} />
          <Route path="spam" element={<Spam />} />
          <Route path="ricevute-pec" element={<RicevutePEC />} />
          <Route path="reports" element={<Reports />} />
          <Route path="debug" element={<Debug />} />
          <Route path="settings" element={<Settings />} />
          <Route path="nlp-training" element={<NLPTraining />} />
          <Route path="bugs" element={<Bugs />} />
        </Route>
      </Routes>

      {/* PWA Install Banner */}
      <PWAInstallBanner />
    </>
  )
}

export default App
