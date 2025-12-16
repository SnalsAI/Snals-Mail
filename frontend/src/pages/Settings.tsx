import { useState, useEffect } from 'react'
import { Save, Mail, Database, Cpu, Calendar as CalendarIcon, HardDrive, PlayCircle, CheckCircle, XCircle, Loader, Tags, Tag, Users, AlertCircle, Check, X, Info, Shield, Search, FileText, RefreshCw } from 'lucide-react'
import toast from 'react-hot-toast'
import { settingsApi, emailsApi, systemSettingsApi, delegatiApi, verificationApi } from '../lib/api'
import { Link } from 'react-router-dom'

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
  // Google Drive rimosso - non disponibile con account Gmail personale
  // google_drive_folder_ust: string
  // google_drive_folder_snals: string

  // System
  email_poll_interval: number
  daily_summary_hour: number
  email_mark_as_read: boolean
  email_delete_from_server: boolean
  email_fetch_limit: number
}

interface CategoryCharacteristics {
  label: string
  icon: string
  description: string
  keywords: string[]
  sender_patterns: string[]
  subject_patterns: string[]
  priority: number
  subcategories: string[]
}

export default function Settings() {
  const [activeTab, setActiveTab] = useState<'email_normal' | 'email_pec' | 'llm' | 'google' | 'categories' | 'system' | 'automation' | 'delegati' | 'verifiche'>('email_normal')
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
    // Google Drive rimosso
    // google_drive_folder_ust: '',
    // google_drive_folder_snals: '',

    // System
    email_poll_interval: 120,
    daily_summary_hour: 18,
    email_mark_as_read: false,
    email_delete_from_server: false,
    email_fetch_limit: 50,
  })

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testingNormal, setTestingNormal] = useState(false)
  const [testingPEC, setTestingPEC] = useState(false)
  const [testingCalendar, setTestingCalendar] = useState(false)
  // Google Drive rimosso
  // const [testingDrive, setTestingDrive] = useState(false)
  const [testResultNormal, setTestResultNormal] = useState<any>(null)
  const [testResultPEC, setTestResultPEC] = useState<any>(null)
  const [testResultCalendar, setTestResultCalendar] = useState<any>(null)
  // const [testResultDrive, setTestResultDrive] = useState<any>(null)

  // Categories
  const [categories, setCategories] = useState<Record<string, CategoryCharacteristics>>({})
  const [loadingCategories, setLoadingCategories] = useState(false)
  const [savingCategory, setSavingCategory] = useState<string | null>(null)
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [editingCategory, setEditingCategory] = useState<CategoryCharacteristics | null>(null)
  const [categoriesSubTab, setCategoriesSubTab] = useState<'config' | 'proposals'>('config')

  // Subcategory Proposals
  const [proposals, setProposals] = useState<any[]>([])
  const [loadingProposals, setLoadingProposals] = useState(false)
  const [expandedProposalId, setExpandedProposalId] = useState<number | null>(null)

  // Automation
  const [autoProcessEnabled, setAutoProcessEnabled] = useState(false)
  const [autoProcessInterval, setAutoProcessInterval] = useState(10)
  const [loadingAutomation, setLoadingAutomation] = useState(false)

  // Delegati & Zone
  const [delegati, setDelegati] = useState<any[]>([])
  const [zone, setZone] = useState<any[]>([])
  const [loadingDelegati, setLoadingDelegati] = useState(false)
  const [editingDelegato, setEditingDelegato] = useState<any>(null)
  const [editingZona, setEditingZona] = useState<any>(null)
  const [showDelegatoModal, setShowDelegatoModal] = useState(false)
  const [showZonaModal, setShowZonaModal] = useState(false)

  // API Stats
  const [apiStats, setApiStats] = useState<any>(null)
  const [loadingApiStats, setLoadingApiStats] = useState(false)

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

  // Load categories when categories tab is selected
  useEffect(() => {
    if (activeTab === 'categories' && Object.keys(categories).length === 0) {
      loadCategories()
    }
  }, [activeTab])

  // Load automation settings when automation tab is selected
  useEffect(() => {
    if (activeTab === 'automation') {
      loadAutomationSettings()
    }
  }, [activeTab])

  // Load delegati when delegati tab is selected
  useEffect(() => {
    if (activeTab === 'delegati') {
      loadDelegatiAndZone()
    }
  }, [activeTab])

  // Load API stats when LLM tab is selected
  useEffect(() => {
    if (activeTab === 'llm') {
      loadApiStats()
    }
  }, [activeTab])

  const loadCategories = async () => {
    setLoadingCategories(true)
    try {
      const response = await settingsApi.getCategories()
      setCategories(response.data.categories)
      // Select first category by default
      const firstKey = Object.keys(response.data.categories)[0]
      if (firstKey) {
        setSelectedCategory(firstKey)
        setEditingCategory(response.data.categories[firstKey])
      }
    } catch (error: any) {
      console.error('Errore caricamento categorie:', error)
      toast.error('Errore nel caricamento delle categorie')
    } finally {
      setLoadingCategories(false)
    }
  }

  const handleSaveCategory = async () => {
    if (!selectedCategory || !editingCategory) return

    setSavingCategory(selectedCategory)
    try {
      await settingsApi.updateCategory(selectedCategory, editingCategory)
      // Update local state
      setCategories({
        ...categories,
        [selectedCategory]: editingCategory
      })
      toast.success(`Categoria "${editingCategory.label}" salvata con successo`)
    } catch (error: any) {
      console.error('Errore salvataggio categoria:', error)
      toast.error('Errore nel salvataggio: ' + (error.response?.data?.detail || error.message))
    } finally {
      setSavingCategory(null)
    }
  }

  const handleResetCategories = async () => {
    if (!confirm('Sei sicuro di voler resettare tutte le categorie ai valori di default?')) {
      return
    }

    setLoadingCategories(true)
    try {
      const response = await settingsApi.resetCategories()
      setCategories(response.data.categories)
      toast.success('Categorie resettate ai valori di default')
      // Reset selection
      const firstKey = Object.keys(response.data.categories)[0]
      if (firstKey) {
        setSelectedCategory(firstKey)
        setEditingCategory(response.data.categories[firstKey])
      }
    } catch (error: any) {
      console.error('Errore reset categorie:', error)
      toast.error('Errore nel reset: ' + (error.response?.data?.detail || error.message))
    } finally {
      setLoadingCategories(false)
    }
  }

  // Load proposals when proposals sub-tab is selected
  useEffect(() => {
    if (activeTab === 'categories' && categoriesSubTab === 'proposals' && proposals.length === 0) {
      loadProposals()
    }
  }, [activeTab, categoriesSubTab])

  const loadProposals = async () => {
    setLoadingProposals(true)
    try {
      const response = await emailsApi.getProposals()
      setProposals(response.data.emails || [])
    } catch (error: any) {
      console.error('Errore caricamento proposte:', error)
      toast.error('Errore nel caricamento delle proposte')
    } finally {
      setLoadingProposals(false)
    }
  }

  const handleApproveProposal = async (emailId: number) => {
    if (!confirm('Sei sicuro di voler approvare questa sottocategoria? Verrà aggiunta a quelle predefinite.')) {
      return
    }

    try {
      const response = await emailsApi.approveSubcategory(emailId)
      toast.success(response.data.message || 'Proposta approvata con successo')
      // Remove from proposals list
      setProposals(proposals.filter(p => p.id !== emailId))
      // Reload categories to show new subcategory
      loadCategories()
    } catch (error: any) {
      console.error('Errore approvazione proposta:', error)
      toast.error(error.response?.data?.detail || 'Errore durante l\'approvazione')
    }
  }

  const handleRejectProposal = async (emailId: number) => {
    if (!confirm('Sei sicuro di voler rifiutare questa proposta? Verrà mantenuta la sottocategoria attuale.')) {
      return
    }

    try {
      const response = await emailsApi.rejectSubcategory(emailId)
      toast.success(response.data.message || 'Proposta rifiutata')
      // Remove from proposals list
      setProposals(proposals.filter(p => p.id !== emailId))
    } catch (error: any) {
      console.error('Errore rifiuto proposta:', error)
      toast.error(error.response?.data?.detail || 'Errore durante il rifiuto')
    }
  }

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('it-IT', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

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

  const handleTestGoogleCalendar = async () => {
    setTestingCalendar(true)
    setTestResultCalendar(null)
    try {
      const response = await settingsApi.testGoogleCalendar()
      setTestResultCalendar(response.data)
      if (response.data.success) {
        toast.success(`Google Calendar OK! Trovati ${response.data.total_calendars} calendari`)
      } else {
        toast.error('Test Google Calendar fallito: ' + response.data.error)
      }
    } catch (error: any) {
      toast.error('Errore durante il test: ' + (error.response?.data?.detail || error.message))
      setTestResultCalendar({
        success: false,
        error: '❌ Errore di connessione'
      })
    } finally {
      setTestingCalendar(false)
    }
  }

  // Google Drive test rimosso - non disponibile con account Gmail personale
  // const handleTestGoogleDrive = async () => { ... }

  // ========== AUTOMATION FUNCTIONS ==========
  const loadAutomationSettings = async () => {
    setLoadingAutomation(true)
    try {
      const response = await systemSettingsApi.getAll()
      const data = response.data

      if (data.auto_process_enabled) {
        setAutoProcessEnabled(data.auto_process_enabled.value)
      }
      if (data.auto_process_interval) {
        setAutoProcessInterval(data.auto_process_interval.value)
      }
    } catch (error: any) {
      console.error('Errore caricamento impostazioni automazione:', error)
      toast.error('Errore nel caricamento delle impostazioni')
    } finally {
      setLoadingAutomation(false)
    }
  }

  const updateAutomationSetting = async (key: string, value: any, _type: string) => {
    try {
      const response = await systemSettingsApi.update(key, String(value))
      toast.success(response.data.message)
    } catch (error: any) {
      console.error('Errore aggiornamento impostazione:', error)
      toast.error('Errore nel salvataggio')
    }
  }

  // ========== API STATS FUNCTIONS ==========
  const loadApiStats = async () => {
    setLoadingApiStats(true)
    try {
      const response = await settingsApi.getApiStats()
      setApiStats(response.data)
    } catch (error: any) {
      console.error('Errore caricamento statistiche API:', error)
      // Non mostrare toast per evitare spam - le stats potrebbero non essere disponibili
    } finally {
      setLoadingApiStats(false)
    }
  }

  const handleResetApiStats = async () => {
    if (!confirm('Sei sicuro di voler resettare tutte le statistiche API? Questa azione non può essere annullata.')) {
      return
    }

    try {
      await settingsApi.resetApiStats()
      toast.success('Statistiche API resettate')
      loadApiStats()
    } catch (error: any) {
      console.error('Errore reset statistiche API:', error)
      toast.error('Errore nel reset delle statistiche')
    }
  }

  // ========== DELEGATI & ZONE FUNCTIONS ==========
  const loadDelegatiAndZone = async () => {
    setLoadingDelegati(true)
    try {
      // Load zone
      const zoneResponse = await delegatiApi.getZone()
      setZone(zoneResponse.data.zone || [])

      // Load delegati
      const delegatiResponse = await delegatiApi.getAll()
      setDelegati(delegatiResponse.data.delegati || [])
    } catch (error: any) {
      console.error('Errore caricamento delegati/zone:', error)
      toast.error('Errore nel caricamento')
    } finally {
      setLoadingDelegati(false)
    }
  }

  const handleSaveDelegato = async () => {
    try {
      const response = editingDelegato?.id
        ? await delegatiApi.update(editingDelegato.id, editingDelegato)
        : await delegatiApi.create(editingDelegato)

      toast.success(response.data.message)
      setShowDelegatoModal(false)
      setEditingDelegato(null)
      loadDelegatiAndZone()
    } catch (error: any) {
      console.error('Errore salvataggio delegato:', error)
      toast.error('Errore nel salvataggio')
    }
  }

  const handleDeleteDelegato = async (id: number) => {
    if (!confirm('Sei sicuro di voler eliminare questo delegato?')) return

    try {
      await delegatiApi.delete(id)
      toast.success('Delegato eliminato')
      loadDelegatiAndZone()
    } catch (error: any) {
      toast.error('Errore eliminazione')
    }
  }

  const handleSaveZona = async () => {
    try {
      // Filtra righe vuote prima di salvare
      const comuniFiltrati = (editingZona.comuni || [])
        .map((c: string) => c.trim())
        .filter((c: string) => c.length > 0)

      const zonaData = {
        nome: editingZona.nome,
        descrizione: editingZona.descrizione,
        comuni: comuniFiltrati
      }

      const response = editingZona?.id
        ? await delegatiApi.updateZona(editingZona.id, zonaData)
        : await delegatiApi.createZona(zonaData)

      toast.success(response.data.message)
      setShowZonaModal(false)
      setEditingZona(null)
      loadDelegatiAndZone()
    } catch (error: any) {
      console.error('Errore salvataggio zona:', error)
      toast.error('Errore nel salvataggio')
    }
  }

  const handleDeleteZona = async (id: number) => {
    if (!confirm('Sei sicuro di voler eliminare questa zona?')) return

    try {
      await delegatiApi.deleteZona(id)
      toast.success('Zona eliminata')
      loadDelegatiAndZone()
    } catch (error: any) {
      toast.error('Errore eliminazione')
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
    { id: 'categories' as const, name: 'Categorie', icon: Tags },
    { id: 'system' as const, name: 'Sistema', icon: Database },
    { id: 'automation' as const, name: 'Automazione', icon: PlayCircle },
    { id: 'delegati' as const, name: 'Delegati & Zone', icon: Users },
    { id: 'verifiche' as const, name: 'Verifiche', icon: Shield },
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

  // Componente Tab Verifiche
  const VerificheTab = () => {
    const [verificationStatus, setVerificationStatus] = useState<any>(null)
    const [statusLoading, setStatusLoading] = useState(true)
    const [emails, setEmails] = useState<any[]>([])
    const [emailsLoading, setEmailsLoading] = useState(false)
    const [selectedEmails, setSelectedEmails] = useState<Set<number>>(new Set())
    const [verifyTypes, setVerifyTypes] = useState({
      categorizzazione: true,
      interpello: true,
      calendario: true
    })
    const [verifyResults, setVerifyResults] = useState<any[]>([])
    const [verifying, setVerifying] = useState(false)
    const [batchResults, setBatchResults] = useState<any>(null)
    const [batchLoading, setBatchLoading] = useState(false)
    const [selectedModel, setSelectedModel] = useState('gpt-4o-mini')
    const [emailFilter, setEmailFilter] = useState('')
    const [page, setPage] = useState(0)
    const pageSize = 20

    const openaiModels = [
      { id: 'gpt-4o-mini', name: 'GPT-4o Mini (economico, veloce)' },
      { id: 'gpt-4o', name: 'GPT-4o (potente, costoso)' },
      { id: 'gpt-4-turbo', name: 'GPT-4 Turbo' },
      { id: 'gpt-3.5-turbo', name: 'GPT-3.5 Turbo (vecchio, economico)' },
    ]

    useEffect(() => {
      loadStatus()
      loadEmails()
    }, [page])

    const loadStatus = async () => {
      try {
        setStatusLoading(true)
        const response = await verificationApi.getStatus()
        setVerificationStatus(response.data)
      } catch (error) {
        console.error('Error loading verification status:', error)
        toast.error('Errore caricamento stato verifiche')
      } finally {
        setStatusLoading(false)
      }
    }

    const loadEmails = async () => {
      try {
        setEmailsLoading(true)
        const response = await emailsApi.getAll({ skip: page * pageSize, limit: pageSize })
        const data = response.data as any
        if (Array.isArray(data)) {
          setEmails(data)
        } else if (data?.emails && Array.isArray(data.emails)) {
          setEmails(data.emails)
        } else {
          setEmails([])
        }
      } catch (error) {
        console.error('Error loading emails:', error)
        toast.error('Errore caricamento email')
      } finally {
        setEmailsLoading(false)
      }
    }

    const toggleEmailSelection = (emailId: number) => {
      setSelectedEmails(prev => {
        const newSet = new Set(prev)
        if (newSet.has(emailId)) {
          newSet.delete(emailId)
        } else {
          newSet.add(emailId)
        }
        return newSet
      })
    }

    const toggleAllEmails = () => {
      if (selectedEmails.size === emails.length) {
        setSelectedEmails(new Set())
      } else {
        setSelectedEmails(new Set(emails.map(e => e.id)))
      }
    }

    const toggleVerifyType = (type: keyof typeof verifyTypes) => {
      setVerifyTypes(prev => ({ ...prev, [type]: !prev[type] }))
    }

    const runSelectedVerification = async () => {
      if (selectedEmails.size === 0) {
        toast.error('Seleziona almeno una email')
        return
      }
      if (!verifyTypes.categorizzazione && !verifyTypes.interpello && !verifyTypes.calendario) {
        toast.error('Seleziona almeno un tipo di verifica')
        return
      }

      setVerifying(true)
      setVerifyResults([])
      const results: any[] = []

      try {
        for (const emailId of Array.from(selectedEmails)) {
          const emailResults: any = { emailId, verifications: [] }

          if (verifyTypes.categorizzazione) {
            try {
              const response = await verificationApi.verifyEmail(emailId, 'categorizzazione', selectedModel)
              emailResults.verifications.push({
                type: 'categorizzazione',
                ...response.data
              })
            } catch (e: any) {
              emailResults.verifications.push({
                type: 'categorizzazione',
                error: e.response?.data?.detail || e.message
              })
            }
          }

          if (verifyTypes.interpello) {
            try {
              const response = await verificationApi.verifyEmail(emailId, 'interpello', selectedModel)
              emailResults.verifications.push({
                type: 'interpello',
                ...response.data
              })
            } catch (e: any) {
              emailResults.verifications.push({
                type: 'interpello',
                error: e.response?.data?.detail || e.message
              })
            }
          }

          if (verifyTypes.calendario) {
            try {
              const response = await verificationApi.verifyEmail(emailId, 'calendario', selectedModel)
              emailResults.verifications.push({
                type: 'calendario',
                ...response.data
              })
            } catch (e: any) {
              emailResults.verifications.push({
                type: 'calendario',
                error: e.response?.data?.detail || e.message
              })
            }
          }

          results.push(emailResults)
          setVerifyResults([...results])
        }

        const totalDiscrepancies = results.reduce((sum, r) =>
          sum + r.verifications.reduce((vSum: number, v: any) =>
            vSum + (v.data?.discrepancies?.length || 0), 0), 0)
        toast.success(`Verifica completata: ${totalDiscrepancies} discrepanze totali`)
      } catch (error: any) {
        console.error('Verification error:', error)
        toast.error('Errore durante la verifica')
      } finally {
        setVerifying(false)
      }
    }

    const runBatchVerification = async (type: 'interpelli' | 'calendari' | 'categorizzazione') => {
      setBatchLoading(true)
      setBatchResults(null)
      try {
        let response
        if (type === 'interpelli') {
          response = await verificationApi.verifyInterpelliBatch(10, selectedModel)
        } else if (type === 'calendari') {
          response = await verificationApi.verifyCalendariBatch(10, selectedModel)
        } else {
          // Categorization batch - verify recent emails
          const emailsResponse = await emailsApi.getAll({ limit: 10 })
          const batchResult: { results: any[], total_discrepancies: number, count: number } = { results: [], total_discrepancies: 0, count: 0 }
          for (const email of emailsResponse.data) {
            try {
              const vResponse = await verificationApi.verifyEmail(email.id, 'categorizzazione', selectedModel)
              const discCount = vResponse.data.data?.discrepancies?.length || 0
              batchResult.results.push({
                email_id: email.id,
                oggetto: email.oggetto,
                categoria_attuale: email.categoria,
                ...vResponse.data.data
              })
              batchResult.total_discrepancies += discCount
              batchResult.count++
            } catch (e) {
              batchResult.results.push({ email_id: email.id, error: 'Errore verifica' })
            }
          }
          response = { data: batchResult }
        }
        setBatchResults({ type, ...response.data })
        toast.success(`Batch completato: ${response.data.total_discrepancies} discrepanze trovate`)
      } catch (error: any) {
        console.error('Batch verification error:', error)
        toast.error(error.response?.data?.detail || 'Errore batch verification')
      } finally {
        setBatchLoading(false)
      }
    }

    const filteredEmails = emails.filter(e =>
      !emailFilter || e.oggetto?.toLowerCase().includes(emailFilter.toLowerCase()) ||
      e.mittente?.toLowerCase().includes(emailFilter.toLowerCase())
    )

    return (
      <div className="space-y-6">
        {/* Status Section */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Stato Servizio Verifica
          </h3>

          {statusLoading ? (
            <div className="flex items-center gap-2">
              <Loader className="w-4 h-4 animate-spin" />
              <span>Caricamento...</span>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className={`p-4 rounded-lg border ${verificationStatus?.openai_available ? 'bg-green-50 border-green-200' : 'bg-yellow-50 border-yellow-200'}`}>
                <div className="flex items-center gap-2">
                  {verificationStatus?.openai_available ? (
                    <CheckCircle className="w-5 h-5 text-green-600" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-yellow-600" />
                  )}
                  <span className="font-medium">OpenAI</span>
                </div>
                <p className="text-sm mt-1 text-gray-600">
                  {verificationStatus?.openai_available
                    ? `Configurato (${verificationStatus?.openai_model})`
                    : 'API key non configurata'}
                </p>
              </div>

              <div className={`p-4 rounded-lg border ${verificationStatus?.ollama_available ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'}`}>
                <div className="flex items-center gap-2">
                  {verificationStatus?.ollama_available ? (
                    <CheckCircle className="w-5 h-5 text-green-600" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-600" />
                  )}
                  <span className="font-medium">Ollama (Locale)</span>
                </div>
                <p className="text-sm mt-1 text-gray-600">
                  {verificationStatus?.ollama_available ? 'Disponibile' : 'Non disponibile'}
                </p>
              </div>

              <div className={`p-4 rounded-lg border ${verificationStatus?.hybrid_available ? 'bg-blue-50 border-blue-200' : 'bg-gray-50 border-gray-200'}`}>
                <div className="flex items-center gap-2">
                  {verificationStatus?.hybrid_available ? (
                    <CheckCircle className="w-5 h-5 text-blue-600" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-gray-400" />
                  )}
                  <span className="font-medium">Hybrid (Regex + Ollama)</span>
                </div>
                <p className="text-sm mt-1 text-gray-600">
                  {verificationStatus?.hybrid_available
                    ? 'Regex + validazione Ollama con contesto'
                    : 'Richiede Ollama'}
                </p>
              </div>

              <div className={`p-4 rounded-lg border ${verificationStatus?.nlp_available ? 'bg-purple-50 border-purple-200' : 'bg-gray-50 border-gray-200'}`}>
                <div className="flex items-center gap-2">
                  {verificationStatus?.nlp_available ? (
                    <CheckCircle className="w-5 h-5 text-purple-600" />
                  ) : (
                    <AlertCircle className="w-5 h-5 text-gray-400" />
                  )}
                  <span className="font-medium">NLP (spaCy + BERT)</span>
                </div>
                <p className="text-sm mt-1 text-gray-600">
                  {verificationStatus?.nlp_available
                    ? 'Estrazione con modelli NLP italiani'
                    : 'Modelli NLP non caricati'}
                </p>
                {verificationStatus?.nlp_stats && (
                  <div className="mt-2 pt-2 border-t border-purple-200 text-xs text-purple-700 space-y-1">
                    <div className="flex justify-between">
                      <span>Pattern totali:</span>
                      <span className="font-semibold">{verificationStatus.nlp_stats.total_patterns}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Classi concorso:</span>
                      <span>{verificationStatus.nlp_stats.classi_concorso}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Meccanografici:</span>
                      <span>{verificationStatus.nlp_stats.meccanografici}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Istituti:</span>
                      <span>{verificationStatus.nlp_stats.istituti}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Province:</span>
                      <span>{verificationStatus.nlp_stats.province}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Model Selection */}
          {verificationStatus?.openai_available && (
            <div className="mt-4">
              <label className="label">Modello OpenAI</label>
              <select
                className="input w-full md:w-auto"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
              >
                {openaiModels.map((model) => (
                  <option key={model.id} value={model.id}>
                    {model.name}
                  </option>
                ))}
              </select>
            </div>
          )}
        </div>

        {/* Email Selection with Verification Types */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Search className="w-5 h-5" />
            Verifica Email Selezionate
          </h3>

          {/* Verification Type Checkboxes */}
          <div className="mb-4 p-3 bg-gray-50 rounded-lg">
            <label className="label mb-2">Tipi di Verifica</label>
            <div className="flex gap-4 flex-wrap">
              {[
                { id: 'categorizzazione', label: 'Categorizzazione' },
                { id: 'interpello', label: 'Estrazione Interpello' },
                { id: 'calendario', label: 'Estrazione Convocazione' },
              ].map((type) => (
                <label key={type.id} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={verifyTypes[type.id as keyof typeof verifyTypes]}
                    onChange={() => toggleVerifyType(type.id as keyof typeof verifyTypes)}
                    className="w-4 h-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm">{type.label}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Filter and Actions */}
          <div className="flex flex-wrap gap-3 mb-4">
            <input
              type="text"
              className="input flex-1 min-w-48"
              placeholder="Filtra per oggetto o mittente..."
              value={emailFilter}
              onChange={(e) => setEmailFilter(e.target.value)}
            />
            <button
              onClick={runSelectedVerification}
              disabled={verifying || !verificationStatus?.openai_available || selectedEmails.size === 0}
              className="btn-primary flex items-center gap-2"
            >
              {verifying ? <Loader className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
              Verifica {selectedEmails.size > 0 ? `(${selectedEmails.size})` : ''}
            </button>
          </div>

          {/* Email List */}
          <div className="border rounded-lg overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left w-10">
                    <input
                      type="checkbox"
                      checked={selectedEmails.size === emails.length && emails.length > 0}
                      onChange={toggleAllEmails}
                      className="w-4 h-4 rounded"
                    />
                  </th>
                  <th className="px-3 py-2 text-left w-16">ID</th>
                  <th className="px-3 py-2 text-left">Oggetto</th>
                  <th className="px-3 py-2 text-left w-32">Categoria</th>
                  <th className="px-3 py-2 text-left w-40">Mittente</th>
                </tr>
              </thead>
              <tbody>
                {emailsLoading ? (
                  <tr>
                    <td colSpan={5} className="px-3 py-8 text-center">
                      <Loader className="w-5 h-5 animate-spin mx-auto" />
                    </td>
                  </tr>
                ) : filteredEmails.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-3 py-8 text-center text-gray-500">
                      Nessuna email trovata
                    </td>
                  </tr>
                ) : (
                  filteredEmails.map((email) => (
                    <tr
                      key={email.id}
                      className={`border-t cursor-pointer hover:bg-gray-50 ${
                        selectedEmails.has(email.id) ? 'bg-primary-50' : ''
                      }`}
                      onClick={() => toggleEmailSelection(email.id)}
                    >
                      <td className="px-3 py-2">
                        <input
                          type="checkbox"
                          checked={selectedEmails.has(email.id)}
                          onChange={() => {}}
                          className="w-4 h-4 rounded"
                        />
                      </td>
                      <td className="px-3 py-2 text-gray-500">#{email.id}</td>
                      <td className="px-3 py-2 truncate max-w-xs" title={email.oggetto}>
                        {email.oggetto}
                      </td>
                      <td className="px-3 py-2">
                        <span className="px-2 py-1 text-xs rounded-full bg-gray-100">
                          {email.categoria}
                        </span>
                      </td>
                      <td className="px-3 py-2 truncate max-w-40 text-gray-600" title={email.mittente}>
                        {email.mittente?.split('<')[0]?.trim()}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex justify-between items-center mt-3">
            <span className="text-sm text-gray-500">
              {selectedEmails.size} selezionate
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage(p => Math.max(0, p - 1))}
                disabled={page === 0}
                className="btn-secondary text-sm"
              >
                ← Precedente
              </button>
              <span className="px-3 py-1 text-sm">Pagina {page + 1}</span>
              <button
                onClick={() => setPage(p => p + 1)}
                disabled={emails.length < pageSize}
                className="btn-secondary text-sm"
              >
                Successiva →
              </button>
            </div>
          </div>
        </div>

        {/* Results Section */}
        {verifyResults.length > 0 && (
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">Risultati Verifica</h3>
            <div className="space-y-4 max-h-[600px] overflow-y-auto">
              {verifyResults.map((result, idx) => (
                <div key={idx} className="border rounded-lg p-4">
                  <h4 className="font-medium mb-3">Email #{result.emailId}</h4>
                  {result.verifications.map((v: any, vIdx: number) => (
                    <div key={vIdx} className={`mb-3 p-3 rounded ${
                      v.error ? 'bg-red-50' :
                      v.data?.discrepancies?.length > 0 ? 'bg-yellow-50' : 'bg-green-50'
                    }`}>
                      <div className="flex justify-between items-center mb-2">
                        <span className="font-medium capitalize">{v.type}</span>
                        {v.error ? (
                          <span className="text-red-600 text-sm">Errore</span>
                        ) : (
                          <span className={`text-sm ${v.data?.discrepancies?.length > 0 ? 'text-yellow-600' : 'text-green-600'}`}>
                            {v.data?.discrepancies?.length || 0} discrepanze
                          </span>
                        )}
                      </div>
                      {v.error && <p className="text-sm text-red-600">{v.error}</p>}

                      {/* Extraction Sources Comparison */}
                      {v.data?.extractions && (
                        <div className="mt-3 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-2">
                          {['regex', 'ollama', 'hybrid', 'nlp', 'openai'].map((source) => {
                            const extraction = v.data.extractions[source]
                            if (!extraction) return null
                            return (
                              <div key={source} className={`p-2 rounded text-xs ${
                                extraction.error ? 'bg-red-100' : 'bg-white border'
                              }`}>
                                <div className="font-semibold mb-1 flex items-center justify-between">
                                  <span className="uppercase">{source}</span>
                                  {extraction.time_ms && (
                                    <span className="text-gray-400 font-normal">{Math.round(extraction.time_ms)}ms</span>
                                  )}
                                </div>
                                {extraction.confidence !== undefined && (
                                  <div className={`mb-1 ${extraction.confidence >= 0.7 ? 'text-green-600' : extraction.confidence >= 0.5 ? 'text-yellow-600' : 'text-red-600'}`}>
                                    Confidence: {(extraction.confidence * 100).toFixed(0)}%
                                  </div>
                                )}
                                {extraction.error ? (
                                  <span className="text-red-600">{extraction.error}</span>
                                ) : extraction.data ? (
                                  <div className="space-y-0.5">
                                    {Object.entries(extraction.data).map(([k, val]) => (
                                      <div key={k} className="truncate" title={String(val)}>
                                        <span className="text-gray-500">{k}:</span> {String(val)}
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <span className="text-gray-400">Nessun dato</span>
                                )}
                                {extraction.warnings?.length > 0 && (
                                  <div className="mt-1 text-orange-600">
                                    {extraction.warnings.map((w: any, i: number) => (
                                      <div key={i}>⚠️ {JSON.stringify(w)}</div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            )
                          })}
                        </div>
                      )}

                      {/* Discrepancies */}
                      {v.data?.discrepancies?.length > 0 && (
                        <div className="mt-3 p-2 bg-yellow-100 rounded">
                          <div className="font-semibold text-sm mb-1 text-yellow-800">Discrepanze:</div>
                          <ul className="text-sm space-y-1">
                            {v.data.discrepancies.map((d: any, dIdx: number) => (
                              <li key={dIdx}>• <strong>{d.field}:</strong> {JSON.stringify(d.values)}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Batch Verification Section */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <RefreshCw className="w-5 h-5" />
            Verifica Batch (ultimi 10 record)
          </h3>

          <div className="flex gap-3 flex-wrap">
            <button
              onClick={() => runBatchVerification('categorizzazione')}
              disabled={batchLoading || !verificationStatus?.openai_available}
              className="btn-secondary flex items-center gap-2"
            >
              {batchLoading ? <Loader className="w-4 h-4 animate-spin" /> : <Tag className="w-4 h-4" />}
              Categorizzazione
            </button>
            <button
              onClick={() => runBatchVerification('interpelli')}
              disabled={batchLoading || !verificationStatus?.openai_available}
              className="btn-secondary flex items-center gap-2"
            >
              {batchLoading ? <Loader className="w-4 h-4 animate-spin" /> : <FileText className="w-4 h-4" />}
              Interpelli
            </button>
            <button
              onClick={() => runBatchVerification('calendari')}
              disabled={batchLoading || !verificationStatus?.openai_available}
              className="btn-secondary flex items-center gap-2"
            >
              {batchLoading ? <Loader className="w-4 h-4 animate-spin" /> : <CalendarIcon className="w-4 h-4" />}
              Eventi Calendario
            </button>
          </div>

          {/* Batch Results */}
          {batchResults && (
            <div className="mt-6 border-t pt-4">
              <h4 className="font-semibold mb-3">
                Risultati Batch {batchResults.type}: {batchResults.count} elementi,{' '}
                <span className={batchResults.total_discrepancies > 0 ? 'text-red-600' : 'text-green-600'}>
                  {batchResults.total_discrepancies} discrepanze
                </span>
              </h4>

              <div className="space-y-3 max-h-96 overflow-y-auto">
                {batchResults.results?.map((result: any, idx: number) => (
                  <div
                    key={idx}
                    className={`p-3 rounded-lg border ${
                      result.discrepancies?.length > 0 ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <span className="font-medium">
                        {result.interpello_id ? `Interpello #${result.interpello_id}` :
                         result.evento_id ? `Evento #${result.evento_id}` :
                         `Email #${result.email_id}`}
                      </span>
                      <span className={`text-sm ${result.discrepancies?.length > 0 ? 'text-red-600' : 'text-green-600'}`}>
                        {result.discrepancies?.length || 0} discrepanze
                      </span>
                    </div>
                    {result.oggetto && (
                      <p className="text-sm text-gray-600 truncate">{result.oggetto}</p>
                    )}
                    {result.discrepancies?.length > 0 && (
                      <ul className="mt-2 text-sm text-red-700">
                        {result.discrepancies.map((d: any, i: number) => (
                          <li key={i}>• {d.field}: {d.message}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
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
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">Configurazioni</h1>
          <p className="mt-1 text-sm text-gray-500">
            Gestisci le configurazioni di sistema, credenziali e parametri
          </p>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-primary flex items-center justify-center gap-2 whitespace-nowrap"
        >
          <Save className="w-4 h-4" />
          {saving ? 'Salvataggio...' : 'Salva Modifiche'}
        </button>
      </div>

      {/* Tabs - Scrollable on mobile */}
      <div className="border-b border-gray-200 overflow-x-auto">
        <nav className="flex gap-2 sm:gap-4 min-w-max sm:min-w-0">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-3 sm:px-4 py-2 border-b-2 font-medium text-xs sm:text-sm transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <tab.icon className="w-4 h-4 flex-shrink-0" />
              <span className="hidden sm:inline">{tab.name}</span>
              <span className="sm:hidden">{tab.name.split(' ')[0]}</span>
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

            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800">
                <strong>ℹ️ Info:</strong> Il sistema utilizza modelli LLM per categorizzare email, estrarre informazioni e generare risposte.
                Puoi scegliere tra <strong>Ollama</strong> (modelli locali, gratuiti) o <strong>OpenAI</strong> (cloud, a pagamento ma più potenti).
              </p>
            </div>

            <div>
              <label className="label">Provider LLM</label>
              <select
                className="input"
                value={settings.llm_provider}
                onChange={(e) => setSettings({ ...settings, llm_provider: e.target.value as 'ollama' | 'openai' })}
              >
                <option value="ollama">Ollama (Locale - Gratuito)</option>
                <option value="openai">OpenAI (Cloud - A pagamento)</option>
              </select>
              <p className="mt-1 text-sm text-gray-500">
                {settings.llm_provider === 'ollama'
                  ? '🟢 Ollama: Modelli eseguiti localmente, nessun costo, privacy completa'
                  : '🌐 OpenAI: API esterne, maggiore qualità, costo per token'}
              </p>
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
                  <p className="mt-1 text-xs text-gray-500">
                    URL del servizio Ollama (default: http://ollama:11434 in Docker)
                  </p>
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
                  <p className="mt-1 text-xs text-gray-500">
                    Modello leggero per categorizzare velocemente le email (es: llama3.2:3b)
                  </p>
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
                  <p className="mt-1 text-xs text-gray-500">
                    Modello per estrarre informazioni strutturate (es: mistral:7b, llama3.1:8b)
                  </p>
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
                  <p className="mt-1 text-xs text-gray-500">
                    Modello per generare risposte automatiche (es: mistral:7b, qwen2.5:7b)
                  </p>
                </div>

                <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                  <p className="text-sm text-green-800">
                    <strong>💡 Suggerimento:</strong> Puoi scaricare nuovi modelli con <code className="px-1 py-0.5 bg-green-100 rounded">ollama pull &lt;modello&gt;</code>
                  </p>
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
                  <p className="mt-1 text-xs text-gray-500">
                    Ottieni la tua API key da <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline">platform.openai.com</a>
                  </p>
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
                  <p className="mt-1 text-xs text-gray-500">
                    Modelli consigliati: gpt-4o (migliore qualità), gpt-4o-mini (economico)
                  </p>
                </div>

                <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-sm text-yellow-800">
                    <strong>⚠️ Attenzione:</strong> L'uso delle API OpenAI comporta costi. Monitora il tuo utilizzo su <a href="https://platform.openai.com/usage" target="_blank" rel="noopener noreferrer" className="text-yellow-900 underline">platform.openai.com/usage</a>
                  </p>
                </div>
              </div>
            )}

            {/* API Stats Section */}
            <div className="border-t border-gray-200 pt-6 mt-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-md font-semibold text-gray-900">Statistiche Chiamate API</h3>
                <div className="flex items-center gap-2">
                  <button
                    onClick={loadApiStats}
                    disabled={loadingApiStats}
                    className="btn-secondary text-sm px-3 py-1"
                  >
                    {loadingApiStats ? 'Caricamento...' : 'Aggiorna'}
                  </button>
                  <button
                    onClick={handleResetApiStats}
                    className="text-sm text-red-600 hover:text-red-800"
                  >
                    Reset
                  </button>
                </div>
              </div>

              {loadingApiStats ? (
                <div className="flex items-center justify-center h-32">
                  <Loader className="w-6 h-6 animate-spin text-primary-600" />
                </div>
              ) : apiStats ? (
                <div className="space-y-4">
                  {/* Summary Cards */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-blue-50 rounded-lg p-4 border border-blue-200">
                      <div className="text-2xl font-bold text-blue-700">{apiStats.llm?.total_calls || 0}</div>
                      <div className="text-sm text-blue-600">Chiamate Totali</div>
                    </div>
                    <div className="bg-green-50 rounded-lg p-4 border border-green-200">
                      <div className="text-2xl font-bold text-green-700">{(apiStats.llm?.total_tokens || 0).toLocaleString()}</div>
                      <div className="text-sm text-green-600">Token Totali</div>
                    </div>
                    <div className="bg-purple-50 rounded-lg p-4 border border-purple-200">
                      <div className="text-2xl font-bold text-purple-700">{(apiStats.llm?.total_input_tokens || 0).toLocaleString()}</div>
                      <div className="text-sm text-purple-600">Token Input</div>
                    </div>
                    <div className="bg-orange-50 rounded-lg p-4 border border-orange-200">
                      <div className="text-2xl font-bold text-orange-700">{(apiStats.llm?.total_output_tokens || 0).toLocaleString()}</div>
                      <div className="text-sm text-orange-600">Token Output</div>
                    </div>
                  </div>

                  {/* Breakdown by Type */}
                  {apiStats.llm?.calls_by_type && Object.keys(apiStats.llm.calls_by_type).length > 0 && (
                    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                      <h4 className="text-sm font-medium text-gray-700 mb-3">Chiamate per Tipo</h4>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {Object.entries(apiStats.llm.calls_by_type).map(([type, count]) => (
                          <div key={type} className="flex items-center justify-between bg-white rounded px-3 py-2 border">
                            <span className="text-sm text-gray-600 capitalize">{type}</span>
                            <span className="font-semibold text-gray-900">{count as number}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Breakdown by Model */}
                  {apiStats.llm?.calls_by_model && Object.keys(apiStats.llm.calls_by_model).length > 0 && (
                    <div className="bg-gray-50 rounded-lg p-4 border border-gray-200">
                      <h4 className="text-sm font-medium text-gray-700 mb-3">Chiamate per Modello</h4>
                      <div className="space-y-2">
                        {Object.entries(apiStats.llm.calls_by_model).map(([model, count]) => (
                          <div key={model} className="flex items-center justify-between bg-white rounded px-3 py-2 border">
                            <span className="text-sm font-mono text-gray-600">{model}</span>
                            <span className="font-semibold text-gray-900">{count as number}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Error Rate */}
                  {apiStats.llm?.errors !== undefined && apiStats.llm.errors > 0 && (
                    <div className="bg-red-50 rounded-lg p-4 border border-red-200">
                      <div className="flex items-center gap-2">
                        <AlertCircle className="w-5 h-5 text-red-600" />
                        <span className="text-sm text-red-700">
                          <strong>{apiStats.llm.errors}</strong> errori ({apiStats.llm.error_rate})
                        </span>
                      </div>
                    </div>
                  )}

                  {/* Uptime Info */}
                  <div className="text-xs text-gray-500 flex items-center justify-between">
                    <span>Dati dal: {apiStats.llm?.last_reset ? new Date(apiStats.llm.last_reset).toLocaleString('it-IT') : 'N/A'}</span>
                    <span>Uptime: {apiStats.llm?.uptime_hours?.toFixed(1) || 0} ore</span>
                  </div>
                </div>
              ) : (
                <div className="text-center py-8 text-gray-500">
                  <p>Nessuna statistica disponibile</p>
                  <p className="text-sm mt-1">Le statistiche saranno visibili dopo le prime chiamate API</p>
                </div>
              )}
            </div>
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

              {/* Google Drive rimosso - non disponibile con account Gmail personale */}
              {/* <div>
                <label className="label">ID Cartella Google Drive UST</label>
                <input type="text" className="input" value={settings.google_drive_folder_ust} .../>
              </div> */}

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

              {/* Test Buttons */}
              <div className="pt-6 space-y-4">
                <h3 className="text-md font-semibold text-gray-900">Test Connessione</h3>

                <button
                  onClick={handleTestGoogleCalendar}
                  disabled={testingCalendar}
                  className="btn-secondary flex items-center gap-2"
                >
                  {testingCalendar ? (
                    <>
                      <div className="animate-spin h-4 w-4 border-2 border-primary-600 border-t-transparent rounded-full" />
                      Testing...
                    </>
                  ) : (
                    'Test Google Calendar'
                  )}
                </button>

                {testResultCalendar && (
                  <div className={`p-4 rounded-lg ${testResultCalendar.success ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
                    <p className="font-semibold">Google Calendar:</p>
                    {testResultCalendar.success ? (
                      <>
                        <p>✅ {testResultCalendar.message}</p>
                        {testResultCalendar.calendars && testResultCalendar.calendars.length > 0 && (
                          <div className="mt-2 text-sm">
                            <p>Calendari trovati:</p>
                            <ul className="list-disc pl-5">
                              {testResultCalendar.calendars.map((cal: any, idx: number) => (
                                <li key={idx}>{cal.summary} ({cal.id})</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </>
                    ) : (
                      <p>❌ {testResultCalendar.error}</p>
                    )}
                  </div>
                )}

                {/* Google Drive test rimosso - non disponibile */}
              </div>
            </div>
          </div>
        )}

        {/* Categories */}
        {activeTab === 'categories' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Gestione Categorie Email</h2>
              {categoriesSubTab === 'config' && (
                <button
                  onClick={handleResetCategories}
                  disabled={loadingCategories}
                  className="btn-secondary text-sm"
                >
                  Reset a Default
                </button>
              )}
            </div>

            {/* Sub-tabs */}
            <div className="border-b border-gray-200">
              <nav className="-mb-px flex space-x-8">
                <button
                  onClick={() => setCategoriesSubTab('config')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                    categoriesSubTab === 'config'
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Configura Categorie
                </button>
                <button
                  onClick={() => setCategoriesSubTab('proposals')}
                  className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors flex items-center gap-2 ${
                    categoriesSubTab === 'proposals'
                      ? 'border-primary-500 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                  }`}
                >
                  Proposte Sottocategorie
                  {proposals.length > 0 && (
                    <span className="inline-flex items-center justify-center px-2 py-0.5 text-xs font-bold leading-none text-white bg-red-600 rounded-full">
                      {proposals.length}
                    </span>
                  )}
                </button>
              </nav>
            </div>

            {/* Config Tab */}
            {categoriesSubTab === 'config' && (
              <>
                {/* Info Banner */}
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <div className="text-blue-600 mt-0.5">ℹ️</div>
                    <div className="flex-1 text-sm text-blue-900">
                      <p className="font-medium mb-1">Come funziona la categorizzazione</p>
                      <ul className="list-disc list-inside space-y-1 text-blue-800">
                        <li>Le <strong>categorie base</strong> sono fisse e definite dal sistema (non si possono aggiungere o rimuovere)</li>
                        <li>Puoi personalizzare <strong>label, icona, descrizione e priorità</strong> per adattare le categorie alle tue esigenze</li>
                        <li>Le <strong>parole chiave e pattern</strong> aiutano il sistema a riconoscere automaticamente la categoria corretta</li>
                        <li>Le <strong>sottocategorie</strong> sono validate contro quelle predefinite - proposte nuove per approvazione</li>
                      </ul>
                    </div>
                  </div>
                </div>

            {loadingCategories ? (
              <div className="flex items-center justify-center h-64">
                <Loader className="w-8 h-8 animate-spin text-primary-600" />
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                {/* Category List */}
                <div className="space-y-2">
                  <h3 className="text-sm font-semibold text-gray-700 uppercase">Categorie</h3>
                  <div className="space-y-1">
                    {Object.entries(categories).map(([key, cat]) => (
                      <button
                        key={key}
                        onClick={() => {
                          setSelectedCategory(key)
                          setEditingCategory(cat)
                        }}
                        className={`w-full text-left px-4 py-3 rounded-lg border transition-colors ${
                          selectedCategory === key
                            ? 'bg-primary-50 border-primary-300 text-primary-900'
                            : 'bg-white border-gray-200 hover:bg-gray-50'
                        }`}
                      >
                        <div className="flex items-center gap-2">
                          <span className="text-xl">{cat.icon}</span>
                          <div className="flex-1">
                            <div className="font-medium text-sm">{cat.label}</div>
                            <div className="text-xs text-gray-500">Priorità: {cat.priority}</div>
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Category Editor */}
                {selectedCategory && editingCategory && (
                  <div className="md:col-span-2 space-y-4">
                    <div className="flex items-center justify-between">
                      <h3 className="text-sm font-semibold text-gray-700 uppercase">
                        Modifica Categoria: {editingCategory.label}
                      </h3>
                      <button
                        onClick={handleSaveCategory}
                        disabled={savingCategory === selectedCategory}
                        className="btn-primary text-sm"
                      >
                        {savingCategory === selectedCategory ? 'Salvataggio...' : 'Salva'}
                      </button>
                    </div>

                    <div className="space-y-4">
                      {/* Label & Icon */}
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="label">Nome Visualizzato</label>
                          <input
                            type="text"
                            className="input"
                            value={editingCategory.label}
                            onChange={(e) =>
                              setEditingCategory({ ...editingCategory, label: e.target.value })
                            }
                          />
                        </div>
                        <div>
                          <label className="label">Icona (Emoji)</label>
                          <input
                            type="text"
                            className="input"
                            value={editingCategory.icon}
                            onChange={(e) =>
                              setEditingCategory({ ...editingCategory, icon: e.target.value })
                            }
                            placeholder="📧"
                          />
                        </div>
                      </div>

                      {/* Description */}
                      <div>
                        <label className="label">Descrizione</label>
                        <textarea
                          className="input"
                          rows={2}
                          value={editingCategory.description}
                          onChange={(e) =>
                            setEditingCategory({ ...editingCategory, description: e.target.value })
                          }
                        />
                      </div>

                      {/* Priority */}
                      <div>
                        <label className="label">
                          Priorità (più alto = più importante nella categorizzazione)
                        </label>
                        <input
                          type="number"
                          min="0"
                          max="10"
                          className="input"
                          value={editingCategory.priority}
                          onChange={(e) =>
                            setEditingCategory({ ...editingCategory, priority: Number(e.target.value) })
                          }
                        />
                      </div>

                      {/* Keywords */}
                      <div>
                        <label className="label">Parole Chiave (una per riga)</label>
                        <textarea
                          className="input font-mono text-sm"
                          rows={4}
                          value={editingCategory.keywords.join('\n')}
                          onChange={(e) =>
                            setEditingCategory({
                              ...editingCategory,
                              keywords: e.target.value.split('\n').filter(k => k.trim())
                            })
                          }
                          placeholder="convocazione&#10;riunione&#10;assemblea"
                        />
                        <p className="mt-1 text-xs text-gray-500">
                          Parole che caratterizzano questa categoria
                        </p>
                      </div>

                      {/* Sender Patterns */}
                      <div>
                        <label className="label">Pattern Mittenti (regex, una per riga)</label>
                        <textarea
                          className="input font-mono text-sm"
                          rows={3}
                          value={editingCategory.sender_patterns.join('\n')}
                          onChange={(e) =>
                            setEditingCategory({
                              ...editingCategory,
                              sender_patterns: e.target.value.split('\n').filter(p => p.trim())
                            })
                          }
                          placeholder="uspta@&#10;info@snals\.it&#10;.*@istruzione\.it"
                        />
                        <p className="mt-1 text-xs text-gray-500">
                          Pattern regex per riconoscere i mittenti di questa categoria
                        </p>
                      </div>

                      {/* Subject Patterns */}
                      <div>
                        <label className="label">Pattern Oggetto (regex, una per riga)</label>
                        <textarea
                          className="input font-mono text-sm"
                          rows={3}
                          value={editingCategory.subject_patterns.join('\n')}
                          onChange={(e) =>
                            setEditingCategory({
                              ...editingCategory,
                              subject_patterns: e.target.value.split('\n').filter(p => p.trim())
                            })
                          }
                          placeholder="GPS.*&#10;convocazione&#10;graduatoria"
                        />
                        <p className="mt-1 text-xs text-gray-500">
                          Pattern regex per riconoscere gli oggetti di questa categoria
                        </p>
                      </div>

                      {/* Subcategories */}
                      <div>
                        <label className="label">Sottocategorie Predefinite</label>
                        <p className="text-xs text-amber-600 mb-2 flex items-center gap-1">
                          <span>⚠️</span>
                          <span>Queste sono le sottocategorie di riferimento. Il sistema può generarne altre automaticamente in base al contenuto.</span>
                        </p>

                        {/* Tags visualization */}
                        {editingCategory.subcategories.length > 0 && (
                          <div className="flex flex-wrap gap-2 mb-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                            {editingCategory.subcategories.map((subcat, idx) => (
                              <span
                                key={idx}
                                className="inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium bg-blue-100 text-blue-800 border border-blue-200"
                              >
                                <span>📂 {subcat}</span>
                                <button
                                  onClick={() => {
                                    const newSubcats = [...editingCategory.subcategories]
                                    newSubcats.splice(idx, 1)
                                    setEditingCategory({
                                      ...editingCategory,
                                      subcategories: newSubcats
                                    })
                                  }}
                                  className="ml-1 text-blue-600 hover:text-blue-800"
                                >
                                  ×
                                </button>
                              </span>
                            ))}
                          </div>
                        )}

                        {/* Add new subcategory */}
                        <div className="flex gap-2">
                          <input
                            type="text"
                            className="input flex-1 text-sm"
                            placeholder="Aggiungi sottocategoria (es: GPS 25/26, Interpello, ecc.)"
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                const value = (e.target as HTMLInputElement).value.trim()
                                if (value && !editingCategory.subcategories.includes(value)) {
                                  setEditingCategory({
                                    ...editingCategory,
                                    subcategories: [...editingCategory.subcategories, value]
                                  })
                                  ;(e.target as HTMLInputElement).value = ''
                                }
                              }
                            }}
                          />
                          <button
                            onClick={(e) => {
                              const input = (e.currentTarget.previousElementSibling as HTMLInputElement)
                              const value = input.value.trim()
                              if (value && !editingCategory.subcategories.includes(value)) {
                                setEditingCategory({
                                  ...editingCategory,
                                  subcategories: [...editingCategory.subcategories, value]
                                })
                                input.value = ''
                              }
                            }}
                            className="px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
                          >
                            Aggiungi
                          </button>
                        </div>

                        <p className="mt-2 text-xs text-gray-500">
                          💡 Le sottocategorie vengono estratte automaticamente dal contenuto dell'email.
                          Definire qui quelle comuni per facilitare la selezione manuale.
                        </p>

                        {/* Bulk edit option */}
                        <details className="mt-3">
                          <summary className="text-xs text-gray-600 cursor-pointer hover:text-gray-900">
                            Modifica avanzata (testo)
                          </summary>
                          <textarea
                            className="input font-mono text-xs mt-2"
                            rows={4}
                            value={editingCategory.subcategories.join('\n')}
                            onChange={(e) =>
                              setEditingCategory({
                                ...editingCategory,
                                subcategories: e.target.value.split('\n').filter(s => s.trim())
                              })
                            }
                            placeholder="GPS&#10;Convocazioni supplenze&#10;Utilizzazioni"
                          />
                        </details>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

                {/* Info Box */}
                <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
                  <p className="text-sm text-blue-800">
                    <strong>ℹ️ Come funziona:</strong> Le categorie definite qui vengono utilizzate
                    dal sistema di categorizzazione per classificare automaticamente le email in arrivo.
                    I pattern regex sui mittenti e oggetti hanno priorità sul LLM. Le sottocategorie
                    vengono validate contro quelle predefinite.
                  </p>
                </div>
              </>
            )}

            {/* Proposals Tab */}
            {categoriesSubTab === 'proposals' && (
              <div className="space-y-4">
                {/* Info Banner */}
                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <Info className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
                    <div className="flex-1 text-sm text-amber-900">
                      <p className="font-medium mb-1">Come funziona</p>
                      <ul className="list-disc list-inside space-y-1 text-amber-800">
                        <li>Il sistema propone nuove sottocategorie quando rileva contenuti non classificati</li>
                        <li><strong>Approva</strong>: la nuova sottocategoria viene applicata all'email e aggiunta a quelle predefinite</li>
                        <li><strong>Rifiuta</strong>: viene mantenuta la sottocategoria scelta automaticamente dal sistema</li>
                      </ul>
                    </div>
                  </div>
                </div>

                {loadingProposals ? (
                  <div className="flex items-center justify-center h-64">
                    <Loader className="w-8 h-8 animate-spin text-primary-600" />
                  </div>
                ) : proposals.length === 0 ? (
                  <div className="bg-white rounded-lg shadow p-12 text-center">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-green-100 rounded-full mb-4">
                      <CheckCircle className="w-8 h-8 text-green-600" />
                    </div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">
                      Nessuna proposta in attesa
                    </h3>
                    <p className="text-gray-500">
                      Tutte le proposte di sottocategorie sono state revisionate
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {proposals.map((email: any) => (
                      <div
                        key={email.id}
                        className="bg-white rounded-lg shadow hover:shadow-md transition-shadow"
                      >
                        <div className="p-4">
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 min-w-0">
                              {/* Email Info */}
                              <div className="flex items-center gap-2 mb-2">
                                <Mail className="w-4 h-4 text-gray-400 flex-shrink-0" />
                                <Link
                                  to={`/emails/${email.id}`}
                                  className="text-sm text-blue-600 hover:underline truncate"
                                >
                                  {email.oggetto}
                                </Link>
                              </div>

                              <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-gray-600 mb-3">
                                <span>Da: {email.mittente}</span>
                                <span>{formatDate(email.data_ricezione)}</span>
                                <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded text-xs font-medium">
                                  {email.categoria}
                                </span>
                              </div>

                              {/* Proposal Box */}
                              <div className="p-3 bg-amber-50 border border-amber-200 rounded-lg">
                                <div className="flex items-start gap-3">
                                  <Tags className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2 mb-1">
                                      <span className="text-sm font-medium text-amber-900">
                                        Sottocategoria proposta:
                                      </span>
                                      <span className="px-2 py-0.5 bg-amber-200 text-amber-900 rounded text-sm font-semibold">
                                        {email.sottocategoria_proposta}
                                      </span>
                                    </div>

                                    {email.sottocategoria && (
                                      <div className="text-sm text-amber-700 mb-2">
                                        Attuale: <span className="font-medium">{email.sottocategoria}</span>
                                      </div>
                                    )}

                                    {email.motivo_proposta && (
                                      <div className="text-sm text-amber-800">
                                        <strong>Motivo:</strong> {email.motivo_proposta}
                                      </div>
                                    )}
                                  </div>
                                </div>
                              </div>
                            </div>

                            {/* Action Buttons */}
                            <div className="flex items-center gap-2 flex-shrink-0">
                              <button
                                onClick={() => handleApproveProposal(email.id)}
                                className="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg transition-colors"
                              >
                                <Check className="w-4 h-4" />
                                <span className="hidden sm:inline">Approva</span>
                              </button>

                              <button
                                onClick={() => handleRejectProposal(email.id)}
                                className="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
                              >
                                <X className="w-4 h-4" />
                                <span className="hidden sm:inline">Rifiuta</span>
                              </button>
                            </div>
                          </div>

                          {/* Expandable Details */}
                          <button
                            onClick={() => setExpandedProposalId(expandedProposalId === email.id ? null : email.id)}
                            className="mt-3 text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
                          >
                            {expandedProposalId === email.id ? '▼' : '▶'} Mostra contenuto email
                          </button>

                          {expandedProposalId === email.id && (
                            <div className="mt-3 p-3 bg-gray-50 rounded-lg">
                              <h4 className="text-sm font-medium text-gray-700 mb-2">Contenuto:</h4>
                              <div className="text-sm text-gray-600 whitespace-pre-wrap max-h-64 overflow-y-auto">
                                {email.corpo || 'Nessun contenuto disponibile'}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
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

            </div>
          </div>
        )}

        {/* Automation */}
        {activeTab === 'automation' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Processamento Automatico Email</h2>
              {loadingAutomation && <Loader className="w-5 h-5 animate-spin text-primary-600" />}
            </div>

            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800">
                <strong>ℹ️ Info:</strong> Il processamento automatico scarica le nuove email a intervalli regolari e le processa automaticamente (categorizzazione, interpretazione, creazione azioni).
              </p>
            </div>

            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <input
                  type="checkbox"
                  id="auto_process_enabled"
                  checked={autoProcessEnabled}
                  onChange={(e) => {
                    setAutoProcessEnabled(e.target.checked)
                    updateAutomationSetting('auto_process_enabled', e.target.checked, 'bool')
                  }}
                  className="w-4 h-4 text-primary-600 border-gray-300 rounded focus:ring-primary-500 mt-1"
                />
                <div className="flex-1">
                  <label htmlFor="auto_process_enabled" className="text-sm font-medium text-gray-700 cursor-pointer">
                    Abilita processamento automatico
                  </label>
                  <p className="text-xs text-gray-500 mt-1">
                    Quando abilitato, il sistema scaricherà e processerà automaticamente le email in arrivo
                  </p>
                </div>
              </div>

              <div>
                <label className="label">Intervallo Processamento (minuti)</label>
                <input
                  type="number"
                  min="1"
                  max="60"
                  className="input"
                  value={autoProcessInterval}
                  onChange={(e) => {
                    const value = Number(e.target.value)
                    setAutoProcessInterval(value)
                  }}
                  onBlur={() => {
                    updateAutomationSetting('auto_process_interval', autoProcessInterval, 'int')
                  }}
                />
                <p className="mt-1 text-sm text-gray-500">
                  Ogni quanti minuti scaricare e processare le nuove email (default: 10 minuti)
                </p>
                <p className="mt-1 text-xs text-orange-600">
                  ⚠️ Nota: Riavviare Celery Beat per applicare il nuovo intervallo
                </p>
              </div>

              <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                <h3 className="text-sm font-semibold text-green-800 mb-2">Cosa fa il processamento automatico?</h3>
                <ul className="text-sm text-green-700 space-y-1 list-disc list-inside">
                  <li>Scarica nuove email da entrambi gli account (normale e PEC)</li>
                  <li>Categorizza automaticamente le email usando LLM</li>
                  <li>Interpreta il contenuto e estrae informazioni strutturate</li>
                  <li>Crea azioni da eseguire (eventi calendario, invio email, ecc.)</li>
                  <li>Esegue le azioni automaticamente quando possibile</li>
                </ul>
              </div>
            </div>
          </div>
        )}

        {/* Delegati & Zone */}
        {activeTab === 'delegati' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold text-gray-900">Gestione Delegati e Zone</h2>
              {loadingDelegati && <Loader className="w-5 h-5 animate-spin text-primary-600" />}
            </div>

            <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-blue-800">
                <strong>ℹ️ Info:</strong> Le zone raggruppano comuni. I delegati sono assegnati a zone specifiche per gestire le contrattazioni di quelle aree.
              </p>
            </div>

            {/* Grid con Zone e Delegati */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* ZONE */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-md font-semibold text-gray-800">Zone Territoriali</h3>
                  <button
                    onClick={() => {
                      setEditingZona({ nome: '', descrizione: '', comuni: [] })
                      setShowZonaModal(true)
                    }}
                    className="btn-primary text-sm px-3 py-1"
                  >
                    + Nuova Zona
                  </button>
                </div>

                <div className="space-y-2">
                  {zone.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                      <p>Nessuna zona definita</p>
                      <p className="text-sm">Crea la prima zona per iniziare</p>
                    </div>
                  ) : (
                    zone.map((zona) => (
                      <div key={zona.id} className="p-4 border rounded-lg hover:bg-gray-50">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h4 className="font-medium text-gray-900">{zona.nome}</h4>
                            {zona.descrizione && (
                              <p className="text-sm text-gray-600 mt-1">{zona.descrizione}</p>
                            )}
                            <div className="mt-2 flex flex-wrap gap-1">
                              {zona.comuni?.length > 0 ? (
                                zona.comuni.map((comune: string, idx: number) => (
                                  <span key={idx} className="text-xs px-2 py-1 bg-blue-100 text-blue-800 rounded">
                                    {comune}
                                  </span>
                                ))
                              ) : (
                                <span className="text-xs text-gray-400">Nessun comune assegnato</span>
                              )}
                            </div>
                            <p className="text-xs text-gray-500 mt-2">
                              {zona.num_delegati || 0} delegati
                            </p>
                          </div>
                          <div className="flex gap-2 ml-2">
                            <button
                              onClick={() => {
                                setEditingZona(zona)
                                setShowZonaModal(true)
                              }}
                              className="text-blue-600 hover:text-blue-800 text-sm"
                            >
                              Modifica
                            </button>
                            <button
                              onClick={() => handleDeleteZona(zona.id)}
                              className="text-red-600 hover:text-red-800 text-sm"
                            >
                              Elimina
                            </button>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              {/* DELEGATI */}
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-md font-semibold text-gray-800">Delegati</h3>
                  <button
                    onClick={() => {
                      setEditingDelegato({ nome: '', cognome: '', email: '', telefono: '', zone_ids: [] })
                      setShowDelegatoModal(true)
                    }}
                    className="btn-primary text-sm px-3 py-1"
                  >
                    + Nuovo Delegato
                  </button>
                </div>

                <div className="space-y-2">
                  {delegati.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                      <p>Nessun delegato definito</p>
                      <p className="text-sm">Aggiungi il primo delegato</p>
                    </div>
                  ) : (
                    delegati.map((delegato) => (
                      <div key={delegato.id} className="p-4 border rounded-lg hover:bg-gray-50">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h4 className="font-medium text-gray-900">{delegato.nome_completo}</h4>
                            <p className="text-sm text-gray-600">{delegato.email}</p>
                            {delegato.telefono && (
                              <p className="text-sm text-gray-600">{delegato.telefono}</p>
                            )}
                            <div className="mt-2 flex flex-wrap gap-1">
                              {delegato.zone?.length > 0 ? (
                                delegato.zone.map((zona: any) => (
                                  <span key={zona.id} className="text-xs px-2 py-1 bg-green-100 text-green-800 rounded">
                                    {zona.nome}
                                  </span>
                                ))
                              ) : (
                                <span className="text-xs text-gray-400">Nessuna zona assegnata</span>
                              )}
                            </div>
                          </div>
                          <div className="flex gap-2 ml-2">
                            <button
                              onClick={() => {
                                setEditingDelegato({
                                  ...delegato,
                                  zone_ids: delegato.zone?.map((z: any) => z.id) || []
                                })
                                setShowDelegatoModal(true)
                              }}
                              className="text-blue-600 hover:text-blue-800 text-sm"
                            >
                              Modifica
                            </button>
                            <button
                              onClick={() => handleDeleteDelegato(delegato.id)}
                              className="text-red-600 hover:text-red-800 text-sm"
                            >
                              Elimina
                            </button>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>

            {/* Modal Zona */}
            {showZonaModal && (
              <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                  <h3 className="text-lg font-semibold mb-4">
                    {editingZona?.id ? 'Modifica Zona' : 'Nuova Zona'}
                  </h3>

                  <div className="space-y-4">
                    <div>
                      <label className="label">Nome Zona *</label>
                      <input
                        type="text"
                        className="input"
                        value={editingZona?.nome || ''}
                        onChange={(e) => setEditingZona({ ...editingZona, nome: e.target.value })}
                        placeholder="Es: Laterza-Ginosa"
                      />
                    </div>

                    <div>
                      <label className="label">Descrizione</label>
                      <textarea
                        className="input"
                        rows={2}
                        value={editingZona?.descrizione || ''}
                        onChange={(e) => setEditingZona({ ...editingZona, descrizione: e.target.value })}
                        placeholder="Descrizione della zona..."
                      />
                    </div>

                    <div>
                      <label className="label">Comuni (uno per riga)</label>
                      <textarea
                        className="input font-mono"
                        rows={8}
                        value={editingZona?.comuni?.join('\n') || ''}
                        onChange={(e) => {
                          // Mantieni TUTTI i newline durante editing, incluse righe vuote
                          // Filtreremo le righe vuote solo al salvataggio
                          const lines = e.target.value.split('\n')
                          setEditingZona({
                            ...editingZona,
                            comuni: lines  // Non filtrare qui - mantieni righe vuote per editing fluido
                          })
                        }}
                        placeholder="LATERZA&#10;GINOSA&#10;PALAGIANO&#10;CASTELLANETA&#10;MOTTOLA"
                        style={{
                          whiteSpace: 'pre-wrap',
                          overflowWrap: 'break-word',
                          resize: 'vertical'
                        }}
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        ✅ Premi INVIO per andare a capo e inserire più comuni (uno per riga, in MAIUSCOLO)
                      </p>
                      {editingZona?.comuni && editingZona.comuni.filter((c: string) => c.trim().length > 0).length > 0 && (
                        <p className="text-xs text-green-600 mt-1">
                          📍 {editingZona.comuni.filter((c: string) => c.trim().length > 0).length} {editingZona.comuni.filter((c: string) => c.trim().length > 0).length === 1 ? 'comune' : 'comuni'} inserito/i
                        </p>
                      )}
                    </div>
                  </div>

                  <div className="flex gap-3 mt-6">
                    <button onClick={handleSaveZona} className="btn-primary flex-1">
                      Salva
                    </button>
                    <button
                      onClick={() => {
                        setShowZonaModal(false)
                        setEditingZona(null)
                      }}
                      className="btn-secondary flex-1"
                    >
                      Annulla
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Modal Delegato */}
            {showDelegatoModal && (
              <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                <div className="bg-white rounded-lg p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
                  <h3 className="text-lg font-semibold mb-4">
                    {editingDelegato?.id ? 'Modifica Delegato' : 'Nuovo Delegato'}
                  </h3>

                  <div className="space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="label">Nome *</label>
                        <input
                          type="text"
                          className="input"
                          value={editingDelegato?.nome || ''}
                          onChange={(e) => setEditingDelegato({ ...editingDelegato, nome: e.target.value })}
                        />
                      </div>

                      <div>
                        <label className="label">Cognome *</label>
                        <input
                          type="text"
                          className="input"
                          value={editingDelegato?.cognome || ''}
                          onChange={(e) => setEditingDelegato({ ...editingDelegato, cognome: e.target.value })}
                        />
                      </div>
                    </div>

                    <div>
                      <label className="label">Email *</label>
                      <input
                        type="email"
                        className="input"
                        value={editingDelegato?.email || ''}
                        onChange={(e) => setEditingDelegato({ ...editingDelegato, email: e.target.value })}
                      />
                    </div>

                    <div>
                      <label className="label">Telefono</label>
                      <input
                        type="tel"
                        className="input"
                        value={editingDelegato?.telefono || ''}
                        onChange={(e) => setEditingDelegato({ ...editingDelegato, telefono: e.target.value })}
                      />
                    </div>

                    <div>
                      <label className="label">Zone Assegnate</label>
                      <div className="space-y-2 max-h-40 overflow-y-auto border rounded p-2">
                        {zone.map((zona) => (
                          <label key={zona.id} className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={editingDelegato?.zone_ids?.includes(zona.id) || false}
                              onChange={(e) => {
                                const zoneIds = editingDelegato?.zone_ids || []
                                if (e.target.checked) {
                                  setEditingDelegato({ ...editingDelegato, zone_ids: [...zoneIds, zona.id] })
                                } else {
                                  setEditingDelegato({ ...editingDelegato, zone_ids: zoneIds.filter((id: number) => id !== zona.id) })
                                }
                              }}
                              className="w-4 h-4"
                            />
                            <span className="text-sm">{zona.nome}</span>
                          </label>
                        ))}
                      </div>
                      {zone.length === 0 && (
                        <p className="text-sm text-gray-500 mt-2">Crea prima delle zone</p>
                      )}
                    </div>

                    <div>
                      <label className="label">Note</label>
                      <textarea
                        className="input"
                        rows={2}
                        value={editingDelegato?.note || ''}
                        onChange={(e) => setEditingDelegato({ ...editingDelegato, note: e.target.value })}
                      />
                    </div>
                  </div>

                  <div className="flex gap-3 mt-6">
                    <button onClick={handleSaveDelegato} className="btn-primary flex-1">
                      Salva
                    </button>
                    <button
                      onClick={() => {
                        setShowDelegatoModal(false)
                        setEditingDelegato(null)
                      }}
                      className="btn-secondary flex-1"
                    >
                      Annulla
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab Verifiche */}
        {activeTab === 'verifiche' && (
          <VerificheTab />
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
// HMR trigger
