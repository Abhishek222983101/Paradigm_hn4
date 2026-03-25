import React, { useEffect, useRef, useState } from 'react'
import axios from 'axios'

const API_BASE = 'http://localhost:8000/api'

function SankeyDiagram({ batchId }) {
  const svgRef = useRef(null)
  const [flowData, setFlowData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchFlowData()
  }, [batchId])

  const fetchFlowData = async () => {
    try {
      const endpoint = batchId 
        ? `${API_BASE}/batches/${batchId}`
        : `${API_BASE}/dashboard`
      
      const response = await axios.get(endpoint)
      
      if (batchId) {
        const transactions = response.data.transactions || []
        const stages = transactions.map(tx => ({
          stage: tx.stage,
          qty_in: tx.qty_in,
          qty_out: tx.qty_out
        }))
        setFlowData({ stages, batchMode: true })
      } else {
        setFlowData({
          stages: response.data.stage_flow || [],
          batchMode: false
        })
      }
    } catch (error) {
      console.error('Failed to fetch flow data:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="card flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-emerald-500"></div>
      </div>
    )
  }

  if (!flowData || flowData.stages.length === 0) {
    return (
      <div className="card flex items-center justify-center h-64">
        <p className="text-slate-400">No flow data available</p>
      </div>
    )
  }

  const stages = flowData.stages.filter(s => s.qty_in || s.qty_out)
  const svgWidth = 800
  const svgHeight = Math.max(400, stages.length * 60)
  const nodeWidth = 20
  const nodePadding = 30
  const usableWidth = svgWidth - nodeWidth - nodePadding * 2

  const maxQty = Math.max(...stages.map(s => s.qty_in || s.qty_out || 0))
  
  const nodes = stages.map((stage, index) => {
    const y = nodePadding + (index * (svgHeight - nodePadding * 2) / (stages.length - 1 || 1))
    const height = ((stage.qty_in || stage.qty_out || 0) / maxQty) * 100 + 20
    return {
      x: nodePadding,
      y: y - height / 2,
      width: nodeWidth,
      height: height,
      label: stage.stage,
      qty: stage.qty_in || stage.qty_out
    }
  })

  const renderSankey = () => {
    let pathElements = []
    
    for (let i = 0; i < nodes.length - 1; i++) {
      const source = nodes[i]
      const target = nodes[i + 1]
      
      const loss = (stages[i].qty_in || 0) - (stages[i].qty_out || stages[i].qty_in || 0)
      const lossPercent = stages[i].qty_in ? ((loss / stages[i].qty_in) * 100).toFixed(1) : 0
      
      const x1 = source.x + source.width
      const x2 = target.x
      const y1 = source.y + source.height / 2
      const y2 = target.y + target.height / 2
      
      const path = `M ${x1} ${y1} 
                    C ${x1 + (x2 - x1) / 2} ${y1},
                      ${x1 + (x2 - x1) / 2} ${y2},
                      ${x2} ${y2}`
      
      pathElements.push(
        <g key={`path-${i}`}>
          <path
            d={path}
            fill="none"
            stroke={loss > 0 ? "#ef4444" : "#10b981"}
            strokeWidth={Math.min(source.height, target.height)}
            strokeOpacity={0.4}
          />
          {loss > 0 && (
            <g transform={`translate(${(x1 + x2) / 2}, ${Math.min(y1, y2) - 10})`}>
              <text fill="#fbbf24" fontSize="10" textAnchor="middle">
                -{lossPercent}%
              </text>
            </g>
          )}
        </g>
      )
    }
    
    return pathElements
  }

  return (
    <div className="card">
      <h3 className="text-lg font-semibold mb-4">
        {batchId ? `Material Flow: ${batchId}` : 'Overall Material Flow'}
      </h3>
      <div className="overflow-x-auto">
        <svg 
          ref={svgRef} 
          width={svgWidth} 
          height={svgHeight}
          className="w-full h-auto"
        >
          <defs>
            <linearGradient id="flowGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#10b981" />
              <stop offset="100%" stopColor="#3b82f6" />
            </linearGradient>
          </defs>
          
          {renderSankey()}
          
          {nodes.map((node, index) => (
            <g key={`node-${index}`}>
              <rect
                x={node.x}
                y={node.y}
                width={node.width}
                height={node.height}
                fill="#10b981"
                rx="4"
              />
              <text
                x={node.x + node.width + 10}
                y={node.y + node.height / 2}
                fill="#f1f5f9"
                fontSize="12"
                dominantBaseline="middle"
              >
                {node.label.charAt(0).toUpperCase() + node.label.slice(1)}
              </text>
              <text
                x={node.x + node.width + 10}
                y={node.y + node.height / 2 + 14}
                fill="#94a3b8"
                fontSize="10"
                dominantBaseline="middle"
              >
                {node.qty?.toLocaleString()} kg
              </text>
            </g>
          ))}
          
          {stages.map((stage, index) => {
            const loss = (stage.qty_in || 0) - (stage.qty_out || stage.qty_in || 0)
            if (loss <= 0 || index === stages.length - 1) return null
            
            const node = nodes[index]
            const nextNode = nodes[index + 1]
            
            return (
              <g key={`loss-${index}`}>
                <rect
                  x={node.x + node.width + 60}
                  y={node.y + node.height}
                  width={15}
                  height={Math.max(loss / maxQty * 50, 5)}
                  fill="#ef4444"
                  rx="2"
                />
                <text
                  x={node.x + node.width + 70}
                  y={node.y + node.height + Math.max(loss / maxQty * 25, 5)}
                  fill="#f87171"
                  fontSize="9"
                >
                  {loss.toFixed(0)}kg loss
                </text>
              </g>
            )
          })}
        </svg>
      </div>
      
      <div className="mt-4 flex gap-6 text-sm">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-emerald-500 rounded"></div>
          <span className="text-slate-400">Material Flow</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-red-500 rounded"></div>
          <span className="text-slate-400">Material Loss</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 bg-blue-500 rounded"></div>
          <span className="text-slate-400">Output</span>
        </div>
      </div>
    </div>
  )
}

export default SankeyDiagram
