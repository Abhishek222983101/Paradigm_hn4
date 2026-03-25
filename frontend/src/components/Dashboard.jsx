import React from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell, Legend } from 'recharts'
import { Package, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react'

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']

function Dashboard({ data }) {
  if (!data) return null

  const { summary, material_breakdown, stage_flow, status_summary } = data

  const lossData = stage_flow
    .filter(s => s.loss > 0)
    .map(s => ({ name: s.stage, loss: s.loss }))

  const pieData = material_breakdown.map(m => ({ name: m.material, value: m.total_kg }))

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-emerald-500/20 rounded-lg">
              <Package className="w-6 h-6 text-emerald-400" />
            </div>
            <div>
              <p className="text-slate-400 text-sm">Total Batches</p>
              <p className="text-2xl font-bold">{summary.total_batches}</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-blue-500/20 rounded-lg">
              <TrendingUp className="w-6 h-6 text-blue-400" />
            </div>
            <div>
              <p className="text-slate-400 text-sm">Total Input</p>
              <p className="text-2xl font-bold">{summary.total_input_kg?.toLocaleString()} kg</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-purple-500/20 rounded-lg">
              <CheckCircle className="w-6 h-6 text-purple-400" />
            </div>
            <div>
              <p className="text-slate-400 text-sm">Overall Yield</p>
              <p className="text-2xl font-bold">{summary.overall_yield_percent}%</p>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="flex items-center gap-3">
            <div className="p-3 bg-red-500/20 rounded-lg">
              <AlertTriangle className="w-6 h-6 text-red-400" />
            </div>
            <div>
              <p className="text-slate-400 text-sm">Total Loss</p>
              <p className="text-2xl font-bold">{summary.total_loss_kg?.toLocaleString()} kg</p>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Material Breakdown</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={pieData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                outerRadius={100}
                fill="#8884d8"
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Loss by Stage</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={lossData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="name" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', border: 'none' }}
                labelStyle={{ color: '#f1f5f9' }}
              />
              <Bar dataKey="loss" fill="#ef4444" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Stage Flow Summary</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-700">
                <th className="text-left py-3 px-4 text-slate-400">Stage</th>
                <th className="text-right py-3 px-4 text-slate-400">Input (kg)</th>
                <th className="text-right py-3 px-4 text-slate-400">Output (kg)</th>
                <th className="text-right py-3 px-4 text-slate-400">Loss (kg)</th>
              </tr>
            </thead>
            <tbody>
              {stage_flow.map((stage, idx) => (
                <tr key={idx} className="border-b border-slate-700/50">
                  <td className="py-3 px-4 capitalize">{stage.stage}</td>
                  <td className="text-right py-3 px-4">{stage.qty_in?.toLocaleString()}</td>
                  <td className="text-right py-3 px-4">{stage.qty_out?.toLocaleString()}</td>
                  <td className="text-right py-3 px-4">
                    {stage.loss > 0 ? (
                      <span className="text-red-400">{stage.loss?.toLocaleString()}</span>
                    ) : (
                      <span className="text-slate-500">-</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {status_summary && Object.keys(status_summary).length > 0 && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Transaction Status</h3>
          <div className="flex gap-4">
            {Object.entries(status_summary).map(([status, count]) => (
              <div key={status} className="flex items-center gap-2">
                <span className={`badge ${
                  status === 'APPROVED' ? 'badge-success' :
                  status === 'REJECTED' ? 'badge-error' : 'badge-warning'
                }`}>
                  {status}
                </span>
                <span>{count}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard
