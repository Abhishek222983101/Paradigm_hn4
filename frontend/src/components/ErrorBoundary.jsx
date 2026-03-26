import React from 'react'

function ErrorBoundary({ children }) {
  const [hasError, setHasError] = React.useState(false)
  const [error, setError] = React.useState(null)

  React.useEffect(() => {
    const errorHandler = (event) => {
      setHasError(true)
      setError(event.error)
    }
    window.addEventListener('error', errorHandler)
    return () => window.removeEventListener('error', errorHandler)
  }, [])

  if (hasError) {
    return (
      <div className="min-h-screen gradient-bg flex items-center justify-center">
        <div className="card max-w-md text-center">
          <div className="w-16 h-16 bg-red-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-3xl">⚠️</span>
          </div>
          <h2 className="text-xl font-bold mb-2">Something went wrong</h2>
          <p className="text-slate-400 mb-4">
            An error occurred while loading the application.
          </p>
          <button 
            onClick={() => window.location.reload()}
            className="btn-primary"
          >
            Reload Page
          </button>
        </div>
      </div>
    )
  }

  return children
}

export default ErrorBoundary
