import React from 'react'
import { Recycle, Sun, Moon } from 'lucide-react'

function Header({ darkMode = true }) {
  const [currentTime, setCurrentTime] = React.useState(new Date())

  React.useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  return (
    <header className="border-b border-slate-700 px-6 py-4 bg-slate-900/50 backdrop-blur-sm sticky top-0 z-50">
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
        
        <div className="flex items-center gap-6">
          <div className="text-right hidden md:block">
            <p className="text-sm text-slate-400">
              {currentTime.toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}
            </p>
            <p className="text-lg font-mono text-emerald-400">
              {currentTime.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
            </p>
          </div>
          
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
            <span className="text-sm text-slate-400">API Connected</span>
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header
