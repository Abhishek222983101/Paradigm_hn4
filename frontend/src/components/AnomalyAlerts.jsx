import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { AlertTriangle, AlertCircle, Info, X, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react'

const API_BASE = 'http://localhost:8000/api'

function AnomalyAlerts({ batchId = null }) {
  const [anomalies, setAnomalies] = useState([])
  const [statistics, setStatistics] = useState({})
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState(null)
  const [filter, setFilter] = useState('all')

  useEffect(() => {
    fetchAnomalies()
  }, [batchId])

  const fetchAnomalies = async () => {
    setLoading(true)
    try {
      const endpoint = batchId 
        ? `${API_BASE}/anomalies/batch/${batchId}`
        : `${API_BASE}/anomalies`
      
      const response = await axios.get(endpoint)
      setAnomalies(response.data.anomalies || [])
      setStatistics(response.data.statistics || {})
    } catch (error) {
      console.error('Failed to fetch anomalies:', error)
    } finally {
      setLoading(false)
    }
  }

  const getSeverityIcon = (severity) => {
    switch (severity) {
      case 'critical':
        return <AlertCircle className="w-5 h-5 text-red-500" />
      case 'high':
        return <AlertTriangle className="w-5 h-5 text-orange-500" />
      case 'medium':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />
      default:
        return <Info className="w-5 h-5 text-blue-500" />
    }
  }

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500/20 border-red-500'
      case 'high':
        return 'bg-orange-500/20 border-orange-500'
      case 'medium':
        return 'bg-yellow-500/20 border-yellow-500'
      default:
        return 'bg-blue-500/20 border-blue-500'
    }
  }

  const filteredAnomalies = anomalies.filter(a => {
    if (filter === 'all') return true
    return a.severity === filter
  })

  if (loading) {
    return (
      <div className="card">
        <div className="flex items-center justify-center h-32">
          <RefreshCw className="w-6 h-6 text-emerald-500 animate-spin" />
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Anomaly Detection</h3>
          <button 
            onClick={fetchAnomalies}
            className="p-2 hover:bg-slate-700 rounded-lg transition-colors"
          >
            <RefreshCw className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        <div className="grid grid-cols-4 gap-4 mb-4">
          <div className="text-center p-3 bg-red-500/10 rounded-lg">
            <p className="text-2xl font-bold text-red-400">{statistics.critical_count || 0}</p>
            <p className="text-xs text-slate-400">Critical</p>
          </div>
          <div className="text-center p-3 bg-orange-500/10 rounded-lg">
            <p className="text-2xl font-bold text-orange-400">{statistics.high_count || 0}</p>
            <p className="text-xs text-slate-400">High</p>
          </div>
          <div className="text-center p-3 bg-yellow-500/10 rounded-lg">
            <p className="text-2xl font-bold text-yellow-400">{statistics.medium_count || 0}</p>
            <p className="text-xs text-slate-400">Medium</p>
          </div>
          <div className="text-center p-3 bg-blue-500/10 rounded-lg">
            <p className="text-2xl font-bold text-blue-400">{statistics.low_count || 0}</p>
            <p className="text-xs text-slate-400">Low</p>
          </div>
        </div>

        <div className="flex gap-2 mb-4">
          {['all', 'critical', 'high', 'medium', 'low'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 rounded-full text-sm ${
                filter === f
                  ? 'bg-emerald-500 text-white'
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {filteredAnomalies.length === 0 ? (
        <div className="card">
          <div className="text-center py-8">
            <div className="inline-flex items-center justify-center w-16 h-16 bg-emerald-500/20 rounded-full mb-4">
              <CheckCircle className="w-8 h-8 text-emerald-400" />
            </div>
            <p className="text-slate-400">No anomalies detected</p>
          </div>
        </div>
      ) : (
        <div className="space-y-2">
          {filteredAnomalies.map((anomaly) => (
            <div
              key={anomaly.anomaly_id}
              className={`card border-l-4 ${getSeverityColor(anomaly.severity)}`}
            >
              <div 
                className="flex items-start justify-between cursor-pointer"
                onClick={() => setExpandedId(expandedId === anomaly.anomaly_id ? null : anomaly.anomaly_id)}
              >
                <div className="flex items-start gap-3">
                  {getSeverityIcon(anomaly.severity)}
                  <div>
                    <p className="font-medium">{anomaly.message}</p>
                    <div className="flex gap-3 mt-1 text-sm text-slate-400">
                      <span>Batch: {anomaly.batch_id}</span>
                      {anomaly.stage && <span>Stage: {anomaly.stage}</span>}
                      <span className="capitalize">{anomaly.severity}</span>
                    </div>
                  </div>
                </div>
                {expandedId === anomaly.anomaly_id ? (
                  <ChevronUp className="w-5 h-5 text-slate-400" />
                ) : (
                  <ChevronDown className="w-5 h-5 text-slate-400" />
                )}
              </div>

              {expandedId === anomaly.anomaly_id && (
                <div className="mt-4 pt-4 border-t border-slate-700">
                  <div className="grid grid-cols-2 gap-4 mb-3">
                    {anomaly.details && Object.entries(anomaly.details).map(([key, value]) => (
                      <div key={key}>
                        <p className="text-xs text-slate-400">{key.replace(/_/g, ' ')}</p>
                        <p className="font-medium">{typeof value === 'number' ? value.toLocaleString() : value}</p>
                      </div>
                    ))}
                  </div>
                  <div className="p-3 bg-slate-700/50 rounded-lg">
                    <p className="text-sm text-slate-300">
                      <span className="font-semibold text-emerald-400">Recommendation:</span>{' '}
                      {anomaly.recommendation}
                    </p>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default AnomalyAlerts

function CheckCircle(props) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
      <polyline points="22 4 12 14.01 9 11.01"/>
    </svg>
  )
}
