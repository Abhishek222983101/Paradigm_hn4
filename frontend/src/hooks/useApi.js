import React from 'react'
import axios from 'axios'

const API_BASE = 'http://localhost:8000/api'

function useApi() {
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState(null)

  const request = React.useCallback(async (method, endpoint, data = null) => {
    setLoading(true)
    setError(null)
    
    try {
      const config = {
        method,
        url: `${API_BASE}${endpoint}`,
        headers: { 'Content-Type': 'application/json' }
      }
      
      if (data) {
        config.data = data
      }
      
      const response = await axios(config)
      return response.data
    } catch (err) {
      const errorMessage = err.response?.data?.detail || err.message || 'Request failed'
      setError(errorMessage)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const get = React.useCallback((endpoint) => request('GET', endpoint), [request])
  const post = React.useCallback((endpoint, data) => request('POST', endpoint, data), [request])

  return { loading, error, request, get, post }
}

export default useApi
