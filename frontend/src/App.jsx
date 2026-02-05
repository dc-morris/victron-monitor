import { useState, useEffect, useMemo } from 'react'
import { voltageToSOC, getStateLabel, getSOCColor, formatTime } from './utils'

const API_BASE = import.meta.env.VITE_API_URL || (import.meta.env.PROD ? '' : 'http://localhost:8000')

// Circular Gauge Component
function CircularGauge({ value, max = 100, size = 140, strokeWidth = 12, color, bgColor = '#e5e7eb' }) {
  const radius = (size - strokeWidth) / 2
  const circumference = radius * 2 * Math.PI
  const percent = value !== null ? Math.min(value / max, 1) : 0
  const offset = circumference - percent * circumference

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={bgColor}
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-all duration-300 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-3xl font-bold text-gray-800 dark:text-gray-100">
          {value !== null ? `${value}%` : '--'}
        </span>
      </div>
    </div>
  )
}

// Icons
const BatteryIcon = () => (
  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M21 10V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2h14a2 2 0 002-2v-2m-9-4v4m-3-2h6" />
  </svg>
)

const SunIcon = () => (
  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
  </svg>
)

const ThermometerIcon = () => (
  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 11V5a3 3 0 116 0v6m-6 0a4 4 0 106 0m-6 0h6" />
  </svg>
)

const RefreshIcon = ({ spinning }) => (
  <svg className={`w-5 h-5 ${spinning ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
  </svg>
)

const PlayIcon = () => (
  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
    <path d="M8 5v14l11-7z" />
  </svg>
)

const TimeTravelIcon = () => (
  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
    <path strokeLinecap="round" strokeLinejoin="round" d="M3 12h2M4 9l1.5 1.5M4 15l1.5-1.5" />
  </svg>
)

const MoonIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
  </svg>
)

const LightModeIcon = () => (
  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
  </svg>
)

function BatteryCard({ data, timeRemaining }) {
  const voltage = data?.battery_voltage ?? null
  const current = data?.battery_current ?? 0
  const power = data?.battery_power ?? 0
  const state = data?.battery_state ?? 'unknown'
  const soc = voltageToSOC(voltage)

  const getStateColor = (state) => {
    if (state === 'charging' || state === '1' || state === 1) return 'text-emerald-500 bg-emerald-50 dark:bg-emerald-900/30'
    if (state === 'discharging' || state === '2' || state === 2) return 'text-rose-500 bg-rose-50 dark:bg-rose-900/30'
    return 'text-gray-500 bg-gray-100 dark:bg-gray-700'
  }

  const formatHours = (hours) => {
    if (hours === null || hours === undefined) return '--'
    if (hours >= 24) {
      const days = Math.floor(hours / 24)
      const remainingHours = Math.round(hours % 24)
      return `${days}d ${remainingHours}h`
    }
    if (hours >= 1) {
      const wholeHours = Math.floor(hours)
      const minutes = Math.round((hours - wholeHours) * 60)
      return `${wholeHours}h ${minutes}m`
    }
    return `${Math.round(hours * 60)}m`
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg shadow-emerald-100/50 dark:shadow-none p-6 border border-gray-100 dark:border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-emerald-100 dark:bg-emerald-900/50 rounded-lg text-emerald-600 dark:text-emerald-400">
            <BatteryIcon />
          </div>
          <h3 className="font-semibold text-gray-700 dark:text-gray-200">Battery</h3>
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStateColor(state)}`}>
          {getStateLabel(state)}
        </span>
      </div>

      <div className="flex justify-center my-6">
        <CircularGauge value={soc} color={getSOCColor(soc)} />
      </div>

      {/* Time remaining/charging info */}
      {timeRemaining && (
        <div className={`rounded-xl p-3 mb-4 ${
          timeRemaining.is_discharging
            ? 'bg-gradient-to-r from-rose-50 to-orange-50 dark:from-rose-900/30 dark:to-orange-900/30'
            : timeRemaining.is_charging
            ? 'bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-900/30 dark:to-teal-900/30'
            : 'bg-gray-50 dark:bg-gray-700/50'
        }`}>
          {timeRemaining.is_discharging ? (
            <div className="flex justify-between items-center">
              <div className="text-center flex-1">
                <p className="text-xs text-gray-500 dark:text-gray-400">To 50%</p>
                <p className="text-lg font-bold text-rose-600 dark:text-rose-400">{formatHours(timeRemaining.hours_to_min)}</p>
              </div>
              <div className="w-px h-8 bg-gray-200 dark:bg-gray-600"></div>
              <div className="text-center flex-1">
                <p className="text-xs text-gray-500 dark:text-gray-400">To Empty</p>
                <p className="text-lg font-bold text-rose-600 dark:text-rose-400">{formatHours(timeRemaining.hours_to_empty)}</p>
              </div>
            </div>
          ) : timeRemaining.is_charging ? (
            <div className="flex justify-between items-center">
              <div className="text-center flex-1">
                <p className="text-xs text-gray-500 dark:text-gray-400">Charging at</p>
                <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400">{Math.abs(timeRemaining.net_power)}W</p>
              </div>
              <div className="w-px h-8 bg-gray-200 dark:bg-gray-600"></div>
              <div className="text-center flex-1">
                <p className="text-xs text-gray-500 dark:text-gray-400">To Full</p>
                <p className="text-lg font-bold text-emerald-600 dark:text-emerald-400">{formatHours(timeRemaining.hours_to_full)}</p>
              </div>
            </div>
          ) : (
            <div className="text-center">
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {soc >= 100 ? 'Fully charged' : 'Idle'}
              </p>
            </div>
          )}
        </div>
      )}

      <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-100 dark:border-gray-700">
        <div className="text-center">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Voltage</p>
          <p className="text-lg font-semibold text-gray-700 dark:text-gray-200">{voltage?.toFixed(2) ?? '--'}V</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Current</p>
          <p className="text-lg font-semibold text-gray-700 dark:text-gray-200">{current?.toFixed(1) ?? '--'}A</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Power</p>
          <p className={`text-lg font-semibold ${power > 0 ? 'text-emerald-500' : power < 0 ? 'text-rose-500' : 'text-gray-700 dark:text-gray-200'}`}>
            {power?.toFixed(0) ?? '--'}W
          </p>
        </div>
      </div>
    </div>
  )
}

function SolarCard({ data }) {
  const power = data?.solar_power ?? 0
  const voltage = data?.solar_voltage ?? 0
  const current = data?.solar_current ?? 0
  const yieldToday = data?.solar_yield_today ?? 0

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg shadow-amber-100/50 dark:shadow-none p-6 border border-gray-100 dark:border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-amber-100 dark:bg-amber-900/50 rounded-lg text-amber-600 dark:text-amber-400">
            <SunIcon />
          </div>
          <h3 className="font-semibold text-gray-700 dark:text-gray-200">Solar</h3>
        </div>
      </div>

      <div className="flex flex-col items-center my-6">
        <div className="text-5xl font-bold text-amber-500">{power?.toFixed(0) ?? '--'}</div>
        <div className="text-gray-400 text-sm mt-1">watts</div>
      </div>

      <div className="bg-gradient-to-r from-amber-50 to-orange-50 dark:from-amber-900/30 dark:to-orange-900/30 rounded-xl p-4 mb-4">
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-500 dark:text-gray-400">Today's Yield</span>
          <span className="text-xl font-bold text-amber-600 dark:text-amber-400">{yieldToday?.toFixed(2) ?? '--'} kWh</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-100 dark:border-gray-700">
        <div className="text-center">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Voltage</p>
          <p className="text-lg font-semibold text-gray-700 dark:text-gray-200">{voltage?.toFixed(1) ?? '--'}V</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Current</p>
          <p className="text-lg font-semibold text-gray-700 dark:text-gray-200">{current?.toFixed(1) ?? '--'}A</p>
        </div>
      </div>
    </div>
  )
}

function EnvironmentCard({ data }) {
  const temp = data?.temperature ?? null
  const humidity = data?.humidity ?? null

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg shadow-cyan-100/50 dark:shadow-none p-6 border border-gray-100 dark:border-gray-700">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-cyan-100 dark:bg-cyan-900/50 rounded-lg text-cyan-600 dark:text-cyan-400">
            <ThermometerIcon />
          </div>
          <h3 className="font-semibold text-gray-700 dark:text-gray-200">Environment</h3>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6 my-6">
        <div className="text-center">
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Temperature</p>
          <div className="text-4xl font-bold text-cyan-500">{temp?.toFixed(1) ?? '--'}</div>
          <div className="text-gray-400 text-sm mt-1">°C</div>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-400 uppercase tracking-wide mb-2">Humidity</p>
          <div className="text-4xl font-bold text-blue-400">{humidity?.toFixed(0) ?? '--'}</div>
          <div className="text-gray-400 text-sm mt-1">%</div>
        </div>
      </div>
    </div>
  )
}

function TimeSlider({ history, selectedIndex, onIndexChange, isLive, onLiveToggle }) {
  const readings = history?.readings ?? []

  if (readings.length === 0) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg dark:shadow-none p-4 border border-gray-100 dark:border-gray-700">
        <p className="text-gray-400 text-center text-sm">No historical data yet. Data is collected every minute.</p>
      </div>
    )
  }

  const selectedReading = readings[selectedIndex]
  const selectedTime = selectedReading ? new Date(selectedReading.timestamp) : null

  const formatDateTime = (date) => {
    const today = new Date()
    const isToday = date.toDateString() === today.toDateString()
    if (isToday) {
      return `Today ${formatTime(date)}`
    }
    return date.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric', month: 'short' }) + ' ' + formatTime(date)
  }

  const oldestTime = readings.length > 0 ? new Date(readings[0].timestamp) : null
  const newestTime = readings.length > 0 ? new Date(readings[readings.length - 1].timestamp) : null

  return (
    <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-lg dark:shadow-none p-4 border border-gray-100 dark:border-gray-700">
      {/* Header: Icon/title and Live button */}
      <div className="flex items-center justify-between gap-4 mb-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-violet-100 dark:bg-violet-900/50 rounded-lg text-violet-600 dark:text-violet-400">
            <TimeTravelIcon />
          </div>
          <div>
            <div className={`text-xl font-bold ${isLive ? 'text-emerald-500' : 'text-violet-500'}`}>
              {isLive ? 'Live' : selectedTime ? formatTime(selectedTime) : '--:--'}
            </div>
            <div className="text-xs text-gray-400">
              {isLive ? 'Real-time' : selectedTime ? formatDateTime(selectedTime) : ''}
            </div>
          </div>
        </div>

        <button
          onClick={onLiveToggle}
          className={`flex items-center gap-2 px-3 py-2 rounded-xl font-medium transition-all shrink-0 ${
            isLive
              ? 'bg-emerald-500 text-white shadow-lg shadow-emerald-200 dark:shadow-none'
              : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
          }`}
        >
          <PlayIcon />
          <span className="hidden sm:inline">Live</span>
        </button>
      </div>

      {/* Slider - full width below header */}
      <div>
        <input
          type="range"
          min={0}
          max={readings.length - 1}
          value={selectedIndex}
          onChange={(e) => onIndexChange(parseInt(e.target.value))}
          onMouseDown={() => { if (isLive) onLiveToggle() }}
          onTouchStart={() => { if (isLive) onLiveToggle() }}
          className="w-full h-2 rounded-lg appearance-none cursor-pointer"
          style={{
            background: isLive
              ? '#d1fae5'
              : `linear-gradient(to right, #8b5cf6 0%, #8b5cf6 ${(selectedIndex / (readings.length - 1)) * 100}%, #ddd6fe ${(selectedIndex / (readings.length - 1)) * 100}%, #ddd6fe 100%)`
          }}
        />
        <div className="flex justify-between mt-1 text-xs text-gray-400">
          <span>{oldestTime ? formatTime(oldestTime) : ''}</span>
          <span className="text-gray-300 dark:text-gray-500">{readings.length} readings</span>
          <span>{newestTime ? formatTime(newestTime) : ''}</span>
        </div>
      </div>
    </div>
  )
}

function App() {
  const [current, setCurrent] = useState(null)
  const [history, setHistory] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [isLive, setIsLive] = useState(true)
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [darkMode, setDarkMode] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('darkMode')
      if (saved !== null) return JSON.parse(saved)
      return window.matchMedia('(prefers-color-scheme: dark)').matches
    }
    return false
  })

  useEffect(() => {
    localStorage.setItem('darkMode', JSON.stringify(darkMode))
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [darkMode])

  const fetchData = async () => {
    setRefreshing(true)
    try {
      const [currentRes, historyRes] = await Promise.all([
        fetch(`${API_BASE}/api/current`),
        fetch(`${API_BASE}/api/history?hours=24`)
      ])

      if (currentRes.ok) {
        const data = await currentRes.json()
        if (!data.error) {
          setCurrent(data)
          setLastUpdate(new Date())
          setError(null)
        }
      }

      if (historyRes.ok) {
        const data = await historyRes.json()
        setHistory(data)
        // If live mode, keep slider at the end
        if (isLive && data.readings?.length > 0) {
          setSelectedIndex(data.readings.length - 1)
        }
      }
    } catch (e) {
      setError('Failed to connect')
      console.error(e)
    }
    setRefreshing(false)
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [])

  // When new data arrives and we're in live mode, update selected index
  useEffect(() => {
    if (isLive && history?.readings?.length > 0) {
      setSelectedIndex(history.readings.length - 1)
    }
  }, [history, isLive])

  // Get the display data based on mode
  const displayData = useMemo(() => {
    if (isLive || !history?.readings?.length) {
      // Live mode - use current data
      return current ? {
        battery_voltage: current.battery?.voltage,
        battery_current: current.battery?.current,
        battery_power: current.battery?.power,
        battery_state: current.battery?.state,
        time_remaining: current.battery?.time_remaining,
        solar_power: current.solar?.power,
        solar_voltage: current.solar?.voltage,
        solar_current: current.solar?.current,
        solar_yield_today: current.solar?.yield_today,
        temperature: current.environment?.temperature,
        humidity: current.environment?.humidity,
      } : null
    } else {
      // Historical mode - use selected reading (no time_remaining for historical)
      return history.readings[selectedIndex]
    }
  }, [isLive, current, history, selectedIndex])

  const handleLiveToggle = () => {
    const newIsLive = !isLive
    setIsLive(newIsLive)
    if (newIsLive && history?.readings?.length > 0) {
      // Switching to live - jump to end
      setSelectedIndex(history.readings.length - 1)
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-900 dark:to-gray-800 p-4 md:p-8 transition-colors">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">Victron Monitor</h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">Energy Dashboard</p>
          </div>
          <div className="flex items-center gap-3">
            {!isLive && (
              <span className="px-3 py-1 bg-violet-100 dark:bg-violet-900/50 text-violet-600 dark:text-violet-400 rounded-full text-sm font-medium">
                Viewing History
              </span>
            )}
            {lastUpdate && isLive && (
              <span className="text-sm text-gray-400">
                Updated {lastUpdate.toLocaleTimeString()}
              </span>
            )}
            <button
              onClick={() => setDarkMode(!darkMode)}
              className="p-2 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 rounded-xl shadow-sm hover:shadow-md dark:shadow-none transition-all border border-gray-200 dark:border-gray-700"
              title={darkMode ? 'Switch to light mode' : 'Switch to dark mode'}
            >
              {darkMode ? <LightModeIcon /> : <MoonIcon />}
            </button>
            <button
              onClick={fetchData}
              disabled={refreshing}
              className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 rounded-xl shadow-sm hover:shadow-md dark:shadow-none transition-all border border-gray-200 dark:border-gray-700 disabled:opacity-50"
            >
              <RefreshIcon spinning={refreshing} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl text-red-600 dark:text-red-400">
            {error}
          </div>
        )}

        {/* Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-6">
          <BatteryCard data={displayData} timeRemaining={displayData?.time_remaining} />
          <SolarCard data={displayData} />
          <EnvironmentCard data={displayData} />
        </div>

        {/* Time Slider */}
        <TimeSlider
          history={history}
          selectedIndex={selectedIndex}
          onIndexChange={setSelectedIndex}
          isLive={isLive}
          onLiveToggle={handleLiveToggle}
        />

        {/* Footer */}
        <div className="mt-8 text-center text-gray-400 dark:text-gray-500 text-sm space-y-1">
          <p>Data refreshes automatically every 30 seconds</p>
          <p>Built with <a href="https://claude.ai" target="_blank" rel="noopener noreferrer" className="text-violet-500 hover:text-violet-600 dark:text-violet-400 dark:hover:text-violet-300">Claude</a></p>
        </div>
      </div>
    </main>
  )
}

export default App
