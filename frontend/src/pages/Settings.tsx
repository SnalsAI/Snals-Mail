import { useState, useEffect } from 'react'
import { Save, Mail, Database, Cpu, Calendar as CalendarIcon, HardDrive, PlayCircle, CheckCircle, XCircle, Loader } from 'lucide-react'
import toast from 'react-hot-toast'
import { settingsApi } from '../lib/api'

interface SettingsData {
  // Email Normal
  email_normal_pop3_host: string
  email_normal_pop3_port: number
  email_normal_pop3_user: string
  email_normal_pop3_password: string
  email_normal_smtp_host: string
  email_normal_smtp_port: number
  email_normal_smtp_user: string
  email_normal_smtp_password: string

  // Email PEC
  email_pec_pop3_host: string
  email_pec_pop3_port: number
  email_pec_pop3_user: string
  email_pec_pop3_password: string
  email_pec_smtp_host: string
  email_pec_smtp_port: number
  email_pec_smtp_user: string
  email_pec_smtp_password: string

  // LLM
  llm_provider: 'ollama' | 'openai'
  ollama_base_url: string
  ollama_model_categorization: string
  ollama_model_interpretation: string
  ollama_model_generation: string
  openai_api_key: string
  openai_model: string

  // Google
  google_credentials_file: string
  google_calendar_id: string
  google_drive_folder_ust: string
  google_drive_folder_snals: string

  // System
  email_poll_interval: number
  daily_summary_hour: number
  email_mark_as_read: boolean
  email_delete_from_server: boolean
  email_fetch_limit: number
  debug: boolean
  log_level: string
}

export default function Settings() {
  const [activeTab, setActiveTab] = useState<'email_normal' | 'email_pec' | 'llm' | 'google' | 'system'>('email_normal')
  const [settings, setSettings] = useState<SettingsData>({
    // Email Normal
    email_normal_pop3_host: '',
    email_normal_pop3_port: 995,
    email_normal_pop3_user: '',
    email_normal_pop3_password: '',
    email_normal_smtp_host: '',
    email_normal_smtp_port: 587,
    email_normal_smtp_user: '',
    email_normal_smtp_password: '',

    // Email PEC
    email_pec_pop3_host: '',
    email_pec_pop3_port: 995,
    email_pec_pop3_user: '',
    email_pec_pop3_password: '',
    email_pec_smtp_host: '',
    email_pec_smtp_port: 587,
    email_pec_smtp_user: '',
    email_pec_smtp_password: '',

    // LLM
    llm_provider: 'ollama',
    ollama_base_url: 'http://ollama:11434',
    ollama_model_categorization: 'llama3.2:3b',
    ollama_model_interpretation: 'mistral:7b',
    ollama_model_generation: 'mistral:7b',
    openai_api_key: '',
    openai_model: 'gpt-4',

    // Google
    google_credentials_file: '',
    google_calendar_id: 'primary',
    google_drive_folder_ust: '',
    google_drive_folder_snals: '',

    // System
    email_poll_interval: 120,
    daily_summary_hour: 18,
    email_mark_as_read: false,
    email_delete_from_server: false,
    email_fetch_limit: 50,
    debug: true,
    log_level: 'INFO',
  })

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testingNormal, setTestingNormal] = useState(false)
  const [testingPEC, setTestingPEC] = useState(false)
  const [testResultNormal, setTestResultNormal] = useState<any>(null)
  const [testResultPEC, setTestResultPEC] = useState<any>(null)

  // Carica le configurazioni all'avvio
  useEffect(() => {
    const loadSettings = async () => {
      try {
        const response = await settingsApi.getAll()
        setSettings(response.data)
      } catch (error: any) {
        console.error('Errore caricamento configurazioni:', error)
        toast.error('Errore nel caricamento delle configurazioni')
      } finally {
        setLoading(false)
      }
    }

    loadSettings()
  }, [])

  const handleTestEmailNormal = async () => {
    setTestingNormal(true)
    setTestResultNormal(null)
    try {
      const response = await settingsApi.testEmailNormal()
      setTestResultNormal(response.data)
      if (response.data.overall_success) {
        toast.success('Test Email Normale completato con successo!')
      } else {
        toast.error('Test Email Normale completato con errori')
      }
    } catch (error: any) {
      toast.error('Errore durante il test: ' + (error.response?.data?.detail || error.message))
      setTestResultNormal({
        overall_success: false,
        pop3: { success: false, message: '❌ Errore di connessione' },
        smtp: { success: false, message: '❌ Errore di connessione' }
      })
    } finally {
      setTestingNormal(false)
    }
  }

  const handleTestEmailPEC = async () => {
    setTestingPEC(true)
    setTestResultPEC(null)
    try {
      const response = await settingsApi.testEmailPEC()
      setTestResultPEC(response.data)
      if (response.data.overall_success) {
        toast.success('Test Email PEC completato con successo!')
      } else {
        toast.error('Test Email PEC completato con errori')
      }
    } catch (error: any) {
      toast.error('Errore durante il test: ' + (error.response?.data?.detail || error.message))
      setTestResultPEC({
        overall_success: false,
        pop3: { success: false, message: '❌ Errore di connessione' },
        smtp: { success: false, message: '❌ Errore di connessione' }
      })
    } finally {
      setTestingPEC(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const response = await settingsApi.update(settings)
      toast.success(response.data.message)
      toast('⚠️ Riavvia i servizi: docker-compose restart backend celery-worker celery-beat', {
        duration: 8000,
        icon: '🔄'
      })
    } catch (error: any) {
      console.error('Errore salvataggio configurazioni:', error)
      toast.error('Errore nel salvataggio: ' + (error.response?.data?.detail || error.message))
    } finally {
      setSaving(false)
    }
  }

  const tabs = [
    { id: 'email_normal' as const, name: 'Email Normale', icon: Mail },
    { id: 'email_pec' as const, name: 'Email PEC', icon: Mail },
    { id: 'llm' as const, name: 'LLM', icon: Cpu },
    { id: 'google' as const, name: 'Google', icon: HardDrive },
    { id: 'system' as const, name: 'Sistema', icon: Database },
  ]

  // Componente per mostrare i risultati del test
  const TestResults = ({ results }: { results: any }) => {
    if (!results) return null

    return (
      <div className="mt-6 space-y-3">
        <h3 className="text-sm font-semibold text-gray-700">Risultati Test</h3>

        {/* POP3 Result */}
        <div className={`p-4 rounded-lg border ${results.pop3.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
          <div className="flex items-start gap-3">
            {results.pop3.success ? (
              <CheckCircle className="w-5 h-5 text-green-600 mt-0.5" />
            ) : (
              <XCircle className="w-5 h-5 text-red-600 mt-0.5" />
            )}
            <div className="flex-1">
              <h4 className="font-medium text-sm text-gray-900">Test POP3 (Ricezione)</h4>
              <p className="text-sm text-gray-700 mt-1">{results.pop3.message}</p>
              {results.pop3.details?.num_messages !== undefined && (
                <p className="text-xs text-gray-600 mt-2">
                  Email trovate: {results.pop3.details.num_messages}
                </p>
              )}
              {results.pop3.details?.first_email_subject && (
                <p className="text-xs text-gray-600 mt-1">
                  Prima email: "{results.pop3.details.first_email_subject}" da {results.pop3.details.first_email_from}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* SMTP Result */}
        <div className={`p-4 rounded-lg border ${results.smtp.success ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
          <div className="flex items-start gap-3">
            {results.smtp.success ? (
              <CheckCircle className="w-5 h-5 text-green-600 mt-0.5" />
            ) : (
              <XCircle className="w-5 h-5 text-red-600 mt-0.5" />
            )}
            <div className="flex-1">
              <h4 className="font-medium text-sm text-gray-900">Test SMTP (Invio)</h4>
              <p className="text-sm text-gray-700 mt-1">{results.smtp.message}</p>
              {results.smtp.details?.recipient && (
                <p className="text-xs text-gray-600 mt-2">
                  Email di test inviata a: {results.smtp.details.recipient}
                </p>
              )}
              {results.smtp.details?.starttls !== undefined && (
                <p className="text-xs text-gray-600 mt-1">
                  STARTTLS: {results.smtp.details.starttls ? '✓ Supportato' : '✗ Non supportato'}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Configurazioni</h1>
          <p className="mt-1 text-sm text-gray-500">
            Gestisci le configurazioni di sistema, credenziali e parametri
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-primary flex items-center gap-2"
        >
          <Save className="w-4 h-4" />
          {saving ? 'Salvataggio...' : 'Salva Modifiche'}
        </button>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200">
        <nav className="flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-4 py-2 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <div className="card">
        {/* Email Normale */}
        {activeTab === 'email_normal' && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-gray-900">Configurazione Email Normale</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* POP3 */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-gray-700 uppercase">POP3 (Ricezione)</h3>
                <div>
                  <label className="label">Host POP3</label>
                  <input
                    type="text"
                    className="input"
                    value={settings.email_normal_pop3_host}
                    onChange={(e) => setSettings({ ...settings, email_normal_pop3_host: e.target.value })}
                    placeholder="pop.gmail.com"
                  />
                </div>
                <div>
                  <label className="label">Porta POP3</label>
                  <input
                    type="number"
                    className="input"
                    value={settings.email_normal_pop3_port}
                    onChange={(e) => setSettings({ ...settings, email_normal_pop3_port: Number(e.target.value) })}
                  />
                </div>
                <div>
                  <label className="label">Username POP3</label>
                  <input
                    type="email"
                    className="input"
                    value={settings.email_normal_pop3_user}
                    onChange={(e) => setSettings({ ...settings, email_normal_pop3_user: e.target.value })}
                    placeholder="user@gmail.com"
                  />
                </div>
                <div>
                  <label className="label">Password POP3</label>
                  <input
                    type="password"
                    className="input"
                    value={settings.email_normal_pop3_password}
                    onChange={(e) => setSettings({ ...settings, email_normal_pop3_password: e.target.value })}
                    placeholder="••••••••"
                  />
                </div>
              </div>

              {/* SMTP */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-gray-700 uppercase">SMTP (Invio)</h3>
                <div>
                  <label className="label">Host SMTP</label>
                  <input
                    type="text"
                    className="input"
                    value={settings.email_normal_smtp_host}
                    onChange={(e) => setSettings({ ...settings, email_normal_smtp_host: e.target.value })}
                    placeholder="smtp.gmail.com"
                  />
                </div>
                <div>
                  <label className="label">Porta SMTP</label>
                  <input
                    type="number"
                    className="input"
                    value={settings.email_normal_smtp_port}
                    onChange={(e) => setSettings({ ...settings, email_normal_smtp_port: Number(e.target.value) })}
                  />
                </div>
                <div>
                  <label className="label">Username SMTP</label>
                  <input
                    type="email"
                    className="input"
                    value={settings.email_normal_smtp_user}
                    onChange={(e) => setSettings({ ...settings, email_normal_smtp_user: e.target.value })}
                    placeholder="user@gmail.com"
                  />
                </div>
                <div>
                  <label className="label">Password SMTP</label>
                  <input
                    type="password"
                    className="input"
                    value={settings.email_normal_smtp_password}
                    onChange={(e) => setSettings({ ...settings, email_normal_smtp_password: e.target.value })}
                    placeholder="••••••••"
                  />
                </div>
              </div>
            </div>

            {/* Test Button */}
            <div className="border-t border-gray-200 pt-6">
              <button
                onClick={handleTestEmailNormal}
                disabled={testingNormal}
                className="btn-secondary flex items-center gap-2"
              >
                {testingNormal ? (
                  <>
                    <Loader className="w-4 h-4 animate-spin" />
                    Test in corso...
                  </>
                ) : (
                  <>
                    <PlayCircle className="w-4 h-4" />
                    Test Connessione Email
                  </>
                )}
              </button>
              <p className="mt-2 text-xs text-gray-500">
                Verifica la connessione POP3/SMTP e invia un'email di test a se stesso
              </p>
            </div>

            {/* Test Results */}
            <TestResults results={testResultNormal} />
          </div>
        )}

        {/* Email PEC */}
        {activeTab === 'email_pec' && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-gray-900">Configurazione Email PEC</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* POP3 */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-gray-700 uppercase">POP3 (Ricezione)</h3>
                <div>
                  <label className="label">Host POP3</label>
                  <input
                    type="text"
                    className="input"
                    value={settings.email_pec_pop3_host}
                    onChange={(e) => setSettings({ ...settings, email_pec_pop3_host: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label">Porta POP3</label>
                  <input
                    type="number"
                    className="input"
                    value={settings.email_pec_pop3_port}
                    onChange={(e) => setSettings({ ...settings, email_pec_pop3_port: Number(e.target.value) })}
                  />
                </div>
                <div>
                  <label className="label">Username POP3</label>
                  <input
                    type="email"
                    className="input"
                    value={settings.email_pec_pop3_user}
                    onChange={(e) => setSettings({ ...settings, email_pec_pop3_user: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label">Password POP3</label>
                  <input
                    type="password"
                    className="input"
                    value={settings.email_pec_pop3_password}
                    onChange={(e) => setSettings({ ...settings, email_pec_pop3_password: e.target.value })}
                    placeholder="••••••••"
                  />
                </div>
              </div>

              {/* SMTP */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-gray-700 uppercase">SMTP (Invio)</h3>
                <div>
                  <label className="label">Host SMTP</label>
                  <input
                    type="text"
                    className="input"
                    value={settings.email_pec_smtp_host}
                    onChange={(e) => setSettings({ ...settings, email_pec_smtp_host: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label">Porta SMTP</label>
                  <input
                    type="number"
                    className="input"
                    value={settings.email_pec_smtp_port}
                    onChange={(e) => setSettings({ ...settings, email_pec_smtp_port: Number(e.target.value) })}
                  />
                </div>
                <div>
                  <label className="label">Username SMTP</label>
                  <input
                    type="email"
                    className="input"
                    value={settings.email_pec_smtp_user}
                    onChange={(e) => setSettings({ ...settings, email_pec_smtp_user: e.target.value })}
                  />
                </div>
                <div>
                  <label className="label">Password SMTP</label>
                  <input
                    type="password"
                    className="input"
                    value={settings.email_pec_smtp_password}
                    onChange={(e) => setSettings({ ...settings, email_pec_smtp_password: e.target.value })}
                    placeholder="••••••••"
                  />
                </div>
              </div>
            </div>

            {/* Test Button */}
            <div className="border-t border-gray-200 pt-6">
              <button
                onClick={handleTestEmailPEC}
                disabled={testingPEC}
                className="btn-secondary flex items-center gap-2"
              >
                {testingPEC ? (
                  <>
                    <Loader className="w-4 h-4 animate-spin" />
                    Test in corso...
                  </>
                ) : (
                  <>
                    <PlayCircle className="w-4 h-4" />
                    Test Connessione Email PEC
                  </>
                )}
              </button>
              <p className="mt-2 text-xs text-gray-500">
                Verifica la connessione POP3/SMTP PEC e invia un'email di test a se stesso
              </p>
            </div>

            {/* Test Results */}
            <TestResults results={testResultPEC} />
          </div>
        )}

        {/* LLM */}
        {activeTab === 'llm' && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-gray-900">Configurazione LLM</h2>

            <div>
              <label className="label">Provider LLM</label>
              <select
                className="input"
                value={settings.llm_provider}
                onChange={(e) => setSettings({ ...settings, llm_provider: e.target.value as 'ollama' | 'openai' })}
              >
                <option value="ollama">Ollama (Locale)</option>
                <option value="openai">OpenAI (Cloud)</option>
              </select>
            </div>

            {settings.llm_provider === 'ollama' ? (
              <div className="space-y-4">
                <div>
                  <label className="label">URL Base Ollama</label>
                  <input
                    type="text"
                    className="input"
                    value={settings.ollama_base_url}
                    onChange={(e) => setSettings({ ...settings, ollama_base_url: e.target.value })}
                    placeholder="http://ollama:11434"
                  />
                </div>
                <div>
                  <label className="label">Modello Categorizzazione</label>
                  <input
                    type="text"
                    className="input"
                    value={settings.ollama_model_categorization}
                    onChange={(e) => setSettings({ ...settings, ollama_model_categorization: e.target.value })}
                    placeholder="llama3.2:3b"
                  />
                </div>
                <div>
                  <label className="label">Modello Interpretazione</label>
                  <input
                    type="text"
                    className="input"
                    value={settings.ollama_model_interpretation}
                    onChange={(e) => setSettings({ ...settings, ollama_model_interpretation: e.target.value })}
                    placeholder="mistral:7b"
                  />
                </div>
                <div>
                  <label className="label">Modello Generazione</label>
                  <input
                    type="text"
                    className="input"
                    value={settings.ollama_model_generation}
                    onChange={(e) => setSettings({ ...settings, ollama_model_generation: e.target.value })}
                    placeholder="mistral:7b"
                  />
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <div>
                  <label className="label">OpenAI API Key</label>
                  <input
                    type="password"
                    className="input"
                    value={settings.openai_api_key}
                    onChange={(e) => setSettings({ ...settings, openai_api_key: e.target.value })}
                    placeholder="sk-..."
                  />
                </div>
                <div>
                  <label className="label">Modello OpenAI</label>
                  <input
                    type="text"
                    className="input"
                    value={settings.openai_model}
                    onChange={(e) => setSettings({ ...settings, openai_model: e.target.value })}
                    placeholder="gpt-4"
                  />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Google */}
        {activeTab === 'google' && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-gray-900">Configurazione Google</h2>

            <div className="space-y-4">
              <div>
                <label className="label">Percorso Credentials JSON</label>
                <input
                  type="text"
                  className="input"
                  value={settings.google_credentials_file}
                  onChange={(e) => setSettings({ ...settings, google_credentials_file: e.target.value })}
                  placeholder="/app/credentials.json"
                />
                <p className="mt-1 text-sm text-gray-500">
                  File delle credenziali Google API scaricato dalla console
                </p>
              </div>

              <div>
                <label className="label">ID Cartella Google Drive UST</label>
                <input
                  type="text"
                  className="input"
                  value={settings.google_drive_folder_ust}
                  onChange={(e) => setSettings({ ...settings, google_drive_folder_ust: e.target.value })}
                  placeholder="1a2b3c4d5e6f7g8h9i0j"
                />
                <p className="mt-1 text-sm text-gray-500">
                  ID della cartella Google Drive per documenti UST
                </p>
              </div>

              <div>
                <label className="label">ID Cartella Google Drive SNALS</label>
                <input
                  type="text"
                  className="input"
                  value={settings.google_drive_folder_snals}
                  onChange={(e) => setSettings({ ...settings, google_drive_folder_snals: e.target.value })}
                  placeholder="1a2b3c4d5e6f7g8h9i0j"
                />
                <p className="mt-1 text-sm text-gray-500">
                  ID della cartella Google Drive per documenti SNALS
                </p>
              </div>

              <div>
                <label className="label">ID Calendario Google</label>
                <input
                  type="text"
                  className="input"
                  value={settings.google_calendar_id}
                  onChange={(e) => setSettings({ ...settings, google_calendar_id: e.target.value })}
                  placeholder="primary"
                />
                <p className="mt-1 text-sm text-gray-500">
                  ID del calendario dove creare gli eventi (default: primary)
                </p>
              </div>
            </div>
          </div>
        )}

        {/* System */}
        {activeTab === 'system' && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold text-gray-900">Configurazione Sistema</h2>

            <div className="space-y-4">
              <div>
                <label className="label">Intervallo Polling Email (secondi)</label>
                <input
                  type="number"
                  className="input"
                  value={settings.email_poll_interval}
                  onChange={(e) => setSettings({ ...settings, email_poll_interval: Number(e.target.value) })}
                />
                <p className="mt-1 text-sm text-gray-500">
                  Frequenza controllo nuove email (default: 120 secondi)
                </p>
              </div>

              <div>
                <label className="label">Limite Email per Polling</label>
                <input
                  type="number"
                  min="1"
                  max="200"
                  className="input"
                  value={settings.email_fetch_limit}
                  onChange={(e) => setSettings({ ...settings, email_fetch_limit: Number(e.target.value) })}
                />
                <p className="mt-1 text-sm text-gray-500">
                  Numero massimo di email da scaricare per ogni polling (default: 50)
                </p>
              </div>

              <div>
                <label className="label">Ora Riepilogo Giornaliero</label>
                <input
                  type="number"
                  min="0"
                  max="23"
                  className="input"
                  value={settings.daily_summary_hour}
                  onChange={(e) => setSettings({ ...settings, daily_summary_hour: Number(e.target.value) })}
                />
                <p className="mt-1 text-sm text-gray-500">
                  Ora del giorno per inviare riepilogo (formato 24h, default: 18)
                </p>
              </div>

              <div className="border-t border-gray-200 pt-4">
                <h3 className="text-sm font-semibold text-gray-700 uppercase mb-3">
                  Comportamento Email sul Server
                </h3>

                <div className="space-y-3">
                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      id="mark_as_read"
                      checked={settings.email_mark_as_read}
                      onChange={(e) => setSettings({ ...settings, email_mark_as_read: e.target.checked })}
                      className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500 mt-1"
                    />
                    <div className="flex-1">
                      <label htmlFor="mark_as_read" className="text-sm font-medium text-gray-700">
                        Marca email come lette sul server
                      </label>
                      <p className="text-xs text-gray-500 mt-1">
                        ⚠️ Richiede IMAP. Con POP3 questa opzione non ha effetto.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-start gap-3">
                    <input
                      type="checkbox"
                      id="delete_from_server"
                      checked={settings.email_delete_from_server}
                      onChange={(e) => setSettings({ ...settings, email_delete_from_server: e.target.checked })}
                      className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500 mt-1"
                    />
                    <div className="flex-1">
                      <label htmlFor="delete_from_server" className="text-sm font-medium text-gray-700">
                        Elimina email dal server dopo il download
                      </label>
                      <p className="text-xs text-red-600 mt-1">
                        ⚠️ ATTENZIONE: Le email saranno cancellate definitivamente dal server!
                      </p>
                    </div>
                  </div>
                </div>

                <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm text-blue-800">
                    <strong>ℹ️ Nota:</strong> Di default il sistema scarica SOLO una copia delle email
                    e le lascia intatte sul server. Nessuna modifica viene apportata alle email originali.
                  </p>
                </div>
              </div>

              <div className="border-t border-gray-200 pt-4">
                <h3 className="text-sm font-semibold text-gray-700 uppercase mb-3">Debug & Logging</h3>

                <div>
                  <label className="label">Livello Log</label>
                  <select
                    className="input"
                    value={settings.log_level}
                    onChange={(e) => setSettings({ ...settings, log_level: e.target.value })}
                  >
                    <option value="DEBUG">DEBUG</option>
                    <option value="INFO">INFO</option>
                    <option value="WARNING">WARNING</option>
                    <option value="ERROR">ERROR</option>
                  </select>
                </div>

                <div className="flex items-center gap-3 mt-3">
                  <input
                    type="checkbox"
                    id="debug"
                    checked={settings.debug}
                    onChange={(e) => setSettings({ ...settings, debug: e.target.checked })}
                    className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500"
                  />
                  <label htmlFor="debug" className="text-sm font-medium text-gray-700">
                    Modalità Debug
                  </label>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Warning */}
      <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p className="text-sm text-yellow-800">
          <strong>⚠️ Nota:</strong> Dopo aver salvato le modifiche, è necessario riavviare i servizi Docker per applicare le nuove configurazioni.
          Esegui: <code className="px-2 py-1 bg-yellow-100 rounded">docker-compose restart backend celery-worker celery-beat</code>
        </p>
      </div>
    </div>
  )
}
