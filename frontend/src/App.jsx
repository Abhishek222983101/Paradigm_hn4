import React, { useState, useEffect } from 'react'
import axios from 'axios'
import ChatPanel from './components/ChatPanel'
import Dashboard from './components/Dashboard'
import BatchList from './components/BatchList'
import { Recycle, BarChart3, MessageCircle, Database } from 'lucide-react'

const API_BASE = 'http://localhost:8000/api'

function App() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [dashboardData, setDashboardData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchDashboardData()
  }, [])

  const fetchDashboardData = async () => {
    try {
      const response = await axios.get(`${API_BASE}/dashboard`)
      setDashboardData(response.data)
    } catch (error) {
      console.error('Failed to fetch dashboard data:', error)
    } finally {
      setLoading(false)
    }
  }

  const tabs = [
    { id: 'dashboard', label: 'Dashboard', icon: BarChart3 },
    { id: 'chat', label: 'Chat', icon: MessageCircle },
    { id: 'batches', label: 'Batches', icon: Database },
  ]

  return (
    <div className="min-h-screen gradient-bg">
      <header className="border-b border-slate-700 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-emerald-500/20 rounded-lg">
              <Recycle className="w-8 h-8 text-emerald-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">TraceLoop</h1>
              <p className="text-sm text-slate-400">Intelligent Traceability for Recycled Materials</p>
            </div>
          </div>
          
          <nav className="flex gap-2">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-all ${
                  activeTab === tab.id
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : 'text-slate-400 hover:bg-slate-700'
                }`}
              >
                <tab.icon className="w-5 h-5" />
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="max-w-7xl mx-auto p-6">
        {loading ? (
          <div className="flex items-center justify-center h-64">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
          </div>
        ) : (
          <>
            {activeTab === 'dashboard' && (
              <Dashboard data={dashboardData} />
            )}
            {activeTab === 'chat' && (
              <ChatPanel onMessage={fetchDashboardData} />
            )}
            {activeTab === 'batches' && (
              <BatchList />
            )}
          </>
        )}
      </main>
    </div>
  )
}

export default App
