import React, { useState, useEffect } from 'react'
import axios from 'axios'
import { Search, ChevronRight, AlertCircle, CheckCircle, Clock } from 'lucide-react'

const API_BASE = 'http://localhost:8000/api'

function BatchList() {
  const [batches, setBatches] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedBatch, setSelectedBatch] = useState(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [filterMaterial, setFilterMaterial] = useState('')

  useEffect(() => {
    fetchBatches()
  }, [filterMaterial])

  const fetchBatches = async () => {
    try {
      const params = filterMaterial ? { material_type: filterMaterial } : {}
      const response = await axios.get(`${API_BASE}/batches`, { params })
      setBatches(response.data.batches)
    } catch (error) {
      console.error('Failed to fetch batches:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchBatchDetail = async (batchId) => {
    try {
      const response = await axios.get(`${API_BASE}/batches/${batchId}`)
      setSelectedBatch(response.data)
    } catch (error) {
      console.error('Failed to fetch batch details:', error)
    }
  }

  const filteredBatches = batches.filter(batch =>
    batch.batch_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
    batch.material_type?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    batch.source_vendor?.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const getConfidenceColor = (score) => {
    if (score >= 80) return 'text-emerald-400'
    if (score >= 50) return 'text-yellow-400'
    return 'text-red-400'
  }

  const getStatusIcon = (status) => {
    switch (status) {
      case 'APPROVED':
        return <CheckCircle className="w-4 h-4 text-emerald-400" />
      case 'REJECTED':
        return <AlertCircle className="w-4 h-4 text-red-400" />
      default:
        return <Clock className="w-4 h-4 text-yellow-400" />
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-emerald-500"></div>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-1">
        <div className="card">
          <div className="mb-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                placeholder="Search batches..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white"
              />
            </div>
          </div>

          <div className="flex gap-2 mb-4 flex-wrap">
            {['', 'PET', 'HDPE', 'PP', 'Mixed'].map(mat => (
              <button
                key={mat}
                onClick={() => setFilterMaterial(mat)}
                className={`px-3 py-1 rounded-full text-sm ${
                  filterMaterial === mat
                    ? 'bg-emerald-500 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                {mat || 'All'}
              </button>
            ))}
          </div>

          <div className="space-y-2 max-h-[calc(100vh-350px)] overflow-y-auto">
            {filteredBatches.map(batch => (
              <div
                key={batch.batch_id}
                onClick={() => fetchBatchDetail(batch.batch_id)}
                className={`p-3 rounded-lg cursor-pointer transition-all ${
                  selectedBatch?.batch?.batch_id === batch.batch_id
                    ? 'bg-emerald-500/20 border border-emerald-500'
                    : 'bg-slate-700/50 hover:bg-slate-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-semibold">{batch.batch_id}</p>
                    <p className="text-sm text-slate-400">{batch.material_type}</p>
                  </div>
                  <div className="text-right">
                    <p className={`text-sm font-medium ${getConfidenceColor(batch.confidence_score)}`}>
                      {batch.confidence_score}%
                    </p>
                    <p className="text-xs text-slate-400">{batch.transaction_count} txns</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="lg:col-span-2">
        {selectedBatch ? (
          <div className="space-y-4">
            <div className="card">
              <h2 className="text-xl font-bold mb-4">{selectedBatch.batch?.batch_id}</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div>
                  <p className="text-slate-400 text-sm">Material Type</p>
                  <p className="font-semibold">{selectedBatch.batch?.material_type}</p>
                </div>
                <div>
                  <p className="text-slate-400 text-sm">Source Vendor</p>
                  <p className="font-semibold">{selectedBatch.batch?.source_vendor || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-slate-400 text-sm">Input</p>
                  <p className="font-semibold">{selectedBatch.batch?.total_input_kg?.toLocaleString()} kg</p>
                </div>
                <div>
                  <p className="text-slate-400 text-sm">Output</p>
                  <p className="font-semibold">{selectedBatch.batch?.total_output_kg?.toLocaleString()} kg</p>
                </div>
              </div>
            </div>

            {selectedBatch.analysis && (
              <div className="card">
                <h3 className="font-semibold mb-3">AI Analysis</h3>
                <p className="text-slate-300">{selectedBatch.analysis.summary}</p>
                {selectedBatch.analysis.alerts?.length > 0 && (
                  <div className="mt-4 space-y-2">
                    {selectedBatch.analysis.alerts.map((alert, idx) => (
                      <div
                        key={idx}
                        className={`p-3 rounded-lg ${
                          alert.type === 'critical' ? 'bg-red-500/20' :
                          alert.type === 'warning' ? 'bg-yellow-500/20' : 'bg-blue-500/20'
                        }`}
                      >
                        <p className="text-sm">{alert.message}</p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="card">
              <h3 className="font-semibold mb-3">Transaction History</h3>
              <div className="space-y-2">
                {selectedBatch.transactions?.map((tx, idx) => (
                  <div
                    key={idx}
                    className="flex items-center justify-between p-3 bg-slate-700/50 rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      {getStatusIcon(tx.status)}
                      <div>
                        <p className="font-medium capitalize">{tx.stage}</p>
                        <p className="text-xs text-slate-400">{tx.transaction_id}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm">
                        {tx.qty_in?.toLocaleString() || '-'} kg
                        {tx.qty_out && ` → ${tx.qty_out?.toLocaleString()} kg`}
                      </p>
                      <p className="text-xs text-slate-400">{tx.timestamp?.split('T')[0]}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <div className="card flex items-center justify-center h-64">
            <div className="text-center text-slate-400">
              <ChevronRight className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>Select a batch to view details</p>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default BatchList
