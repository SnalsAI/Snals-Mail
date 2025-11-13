import { Settings as SettingsIcon, Mail, Calendar, Sparkles, Database } from 'lucide-react'
import PageHeader from '@/components/PageHeader'

export default function Settings() {
  return (
    <div className="p-8">
      <PageHeader
        title="Impostazioni"
        description="Configura il sistema SNALS Email Agent"
      />

      <div className="space-y-6">
        {/* Email Settings */}
        <div className="card">
          <div className="flex items-center mb-4">
            <Mail className="w-5 h-5 text-primary-600 mr-2" />
            <h2 className="text-lg font-semibold">Configurazione Email</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Intervallo Sincronizzazione (secondi)</label>
              <input type="number" defaultValue={120} className="input" />
            </div>
            <div>
              <label className="label">Ora Riepilogo Giornaliero</label>
              <input type="time" defaultValue="18:00" className="input" />
            </div>
          </div>
          <div className="mt-4">
            <h3 className="font-medium text-sm mb-2">Account Email Normale</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="label">POP3 Host</label>
                <input type="text" placeholder="pop.example.com" className="input" />
              </div>
              <div>
                <label className="label">POP3 Port</label>
                <input type="number" defaultValue={995} className="input" />
              </div>
              <div>
                <label className="label">Username</label>
                <input type="text" placeholder="user@example.com" className="input" />
              </div>
              <div>
                <label className="label">Password</label>
                <input type="password" className="input" />
              </div>
            </div>
          </div>
          <div className="mt-4">
            <h3 className="font-medium text-sm mb-2">Account Email PEC</h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="label">POP3 Host</label>
                <input type="text" placeholder="pop.pec.example.com" className="input" />
              </div>
              <div>
                <label className="label">POP3 Port</label>
                <input type="number" defaultValue={995} className="input" />
              </div>
              <div>
                <label className="label">Username</label>
                <input type="text" placeholder="user@pec.it" className="input" />
              </div>
              <div>
                <label className="label">Password</label>
                <input type="password" className="input" />
              </div>
            </div>
          </div>
        </div>

        {/* LLM Settings */}
        <div className="card">
          <div className="flex items-center mb-4">
            <Sparkles className="w-5 h-5 text-primary-600 mr-2" />
            <h2 className="text-lg font-semibold">Configurazione LLM</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Provider</label>
              <select className="input">
                <option value="ollama">Ollama (Locale)</option>
                <option value="openai">OpenAI</option>
              </select>
            </div>
            <div>
              <label className="label">Ollama Base URL</label>
              <input type="text" defaultValue="http://localhost:11434" className="input" />
            </div>
            <div>
              <label className="label">Modello Categorizzazione</label>
              <input type="text" defaultValue="llama3.2:3b" className="input" />
            </div>
            <div>
              <label className="label">Modello Interpretazione</label>
              <input type="text" defaultValue="mistral:7b" className="input" />
            </div>
            <div>
              <label className="label">Modello Generazione</label>
              <input type="text" defaultValue="mistral:7b" className="input" />
            </div>
          </div>
        </div>

        {/* RAG Settings */}
        <div className="card">
          <div className="flex items-center mb-4">
            <Database className="w-5 h-5 text-primary-600 mr-2" />
            <h2 className="text-lg font-semibold">Configurazione RAG</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Embedding Provider</label>
              <select className="input">
                <option value="sentence-transformers">Sentence Transformers (Locale)</option>
                <option value="openai">OpenAI</option>
              </select>
            </div>
            <div>
              <label className="label">Modello Embedding</label>
              <input type="text" defaultValue="all-MiniLM-L6-v2" className="input" />
            </div>
            <div>
              <label className="label">Chunk Size</label>
              <input type="number" defaultValue={1000} className="input" />
            </div>
            <div>
              <label className="label">Chunk Overlap</label>
              <input type="number" defaultValue={200} className="input" />
            </div>
            <div>
              <label className="label">Similarità Minima</label>
              <input type="number" step="0.1" min="0" max="1" defaultValue={0.7} className="input" />
            </div>
            <div className="flex items-center pt-6">
              <input type="checkbox" id="ragEnabled" defaultChecked className="mr-2" />
              <label htmlFor="ragEnabled" className="text-sm text-gray-700">
                Abilita RAG per risposte automatiche
              </label>
            </div>
          </div>
        </div>

        {/* Google Integration */}
        <div className="card">
          <div className="flex items-center mb-4">
            <Calendar className="w-5 h-5 text-primary-600 mr-2" />
            <h2 className="text-lg font-semibold">Integrazione Google</h2>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Calendar ID</label>
              <input type="text" defaultValue="primary" className="input" />
            </div>
            <div>
              <label className="label">Drive Folder UST/USR</label>
              <input type="text" placeholder="ID cartella Google Drive" className="input" />
            </div>
            <div>
              <label className="label">Drive Folder SNALS</label>
              <input type="text" placeholder="ID cartella Google Drive" className="input" />
            </div>
          </div>
          <div className="mt-4">
            <button className="btn btn-secondary">
              Riconnetti Google Account
            </button>
          </div>
        </div>

        {/* Database Settings */}
        <div className="card">
          <div className="flex items-center mb-4">
            <Database className="w-5 h-5 text-primary-600 mr-2" />
            <h2 className="text-lg font-semibold">Database</h2>
          </div>
          <div className="space-y-4">
            <div>
              <label className="label">Database URL</label>
              <input
                type="text"
                defaultValue="postgresql://user:password@localhost:5432/snals_db"
                className="input"
              />
            </div>
            <div>
              <label className="label">Redis URL</label>
              <input
                type="text"
                defaultValue="redis://localhost:6379/0"
                className="input"
              />
            </div>
          </div>
        </div>

        {/* Save Button */}
        <div className="flex justify-end">
          <button className="btn btn-primary">
            <SettingsIcon className="w-4 h-4 mr-2" />
            Salva Impostazioni
          </button>
        </div>
      </div>
    </div>
  )
}
