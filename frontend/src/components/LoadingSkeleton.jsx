import React from 'react'

function LoadingSkeleton({ count = 3, type = 'card' }) {
  if (type === 'card') {
    return (
      <div className="space-y-4">
        {Array.from({ length: count }).map((_, i) => (
          <div key={i} className="card animate-pulse">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 bg-slate-700 rounded-lg"></div>
              <div className="flex-1">
                <div className="h-4 bg-slate-700 rounded w-1/3 mb-2"></div>
                <div className="h-3 bg-slate-700 rounded w-1/2"></div>
              </div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  if (type === 'table') {
    return (
      <div className="card animate-pulse">
        <div className="space-y-3">
          {Array.from({ length: count }).map((_, i) => (
            <div key={i} className="flex items-center gap-4 py-3 border-b border-slate-700">
              <div className="h-4 bg-slate-700 rounded w-1/4"></div>
              <div className="h-4 bg-slate-700 rounded w-1/4"></div>
              <div className="h-4 bg-slate-700 rounded w-1/4"></div>
              <div className="h-4 bg-slate-700 rounded w-1/4"></div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  if (type === 'chart') {
    return (
      <div className="card animate-pulse">
        <div className="h-4 bg-slate-700 rounded w-1/3 mb-4"></div>
        <div className="h-64 bg-slate-700 rounded"></div>
      </div>
    )
  }

  return (
    <div className="flex items-center justify-center h-32">
      <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-emerald-500"></div>
    </div>
  )
}

export default LoadingSkeleton
