import { useState, useEffect } from 'react'
import axios from 'axios'

const API_URL = import.meta.env.PROD ? '/api' : 'http://localhost:8000/api'

export function useFlightData() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const fetchData = async () => {
    try {
      const res = await axios.get(`${API_URL}/dashboard`)
      setData(res.data)
    } catch (err) {
      console.error("Failed to fetch data", err)
    } finally {
      setLoading(false)
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    try {
      await axios.post(`${API_URL}/refresh`)
      await fetchData()
    } catch (err) {
      console.error("Refresh failed", err)
    } finally {
      setRefreshing(false)
    }
  }

  useEffect(() => {
    fetchData()
    // Poll every minute
    const interval = setInterval(fetchData, 60000)
    return () => clearInterval(interval)
  }, [])

  return { data, loading, refreshing, handleRefresh }
}
