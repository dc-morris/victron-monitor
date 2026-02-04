import { useState, useEffect } from 'react'

const API_BASE = import.meta.env.PROD ? '' : 'http://localhost:8000'

// Lead-acid/AGM 12V battery voltage to SOC lookup table
const VOLTAGE_SOC_TABLE = [
  { voltage: 12.70, soc: 100 },
  { voltage: 12.50, soc: 90 },
  { voltage: 12.42, soc: 80 },
  { voltage: 12.32, soc: 70 },
  { voltage: 12.20, soc: 60 },
  { voltage: 12.06, soc: 50 },
  { voltage: 11.90, soc: 40 },
  { voltage: 11.75, soc: 30 },
  { voltage: 11.58, soc: 20 },
  { voltage: 11.31, soc: 10 },
  { voltage: 10.50, soc: 0 },
]

function voltageToSOC(voltage) {
  if (voltage === null || voltage === undefined) return null
  if (voltage >= VOLTAGE_SOC_TABLE[0].voltage) return 100
  if (voltage <= VOLTAGE_SOC_TABLE[VOLTAGE_SOC_TABLE.length - 1].voltage) return 0

  for (let i = 0; i < VOLTAGE_SOC_TABLE.length - 1; i++) {
    const upper = VOLTAGE_SOC_TABLE[i]
    const lower = VOLTAGE_SOC_TABLE[i + 1]
    if (voltage <= upper.voltage && voltage > lower.voltage) {
      const ratio = (voltage - lower.voltage) / (upper.voltage - lower.voltage)
      return Math.round(lower.soc + ratio * (upper.soc - lower.soc))
    }
  }
  return null
}

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
          className="transition-all duration-500 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-3xl font-bold text-gray-800">
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

function BatteryCard({ battery }) {
  const voltage = battery?.voltage ?? null
  const current = battery?.current ?? 0
  const power = battery?.power ?? 0
  const state = battery?.state ?? 'unknown'
  const soc = voltageToSOC(voltage)

  const getSOCColor = (soc) => {
    if (soc === null) return '#9ca3af'
    if (soc >= 80) return '#10b981'
    if (soc >= 50) return '#f59e0b'
    if (soc >= 20) return '#f97316'
    return '#ef4444'
  }

  const getStateLabel = (state) => {
    if (state === 'charging' || state === '1' || state === 1) return 'Charging'
    if (state === 'discharging' || state === '2' || state === 2) return 'Discharging'
    if (state === 'idle' || state === '0' || state === 0) return 'Idle'
    return 'Unknown'
  }

  const getStateColor = (state) => {
    if (state === 'charging' || state === '1' || state === 1) return 'text-emerald-500 bg-emerald-50'
    if (state === 'discharging' || state === '2' || state === 2) return 'text-rose-500 bg-rose-50'
    return 'text-gray-500 bg-gray-100'
  }

  return (
    <div className="bg-white rounded-2xl shadow-lg shadow-emerald-100/50 p-6 border border-gray-100">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-emerald-100 rounded-lg text-emerald-600">
            <BatteryIcon />
          </div>
          <h3 className="font-semibold text-gray-700">Battery</h3>
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${getStateColor(state)}`}>
          {getStateLabel(state)}
        </span>
      </div>

      <div className="flex justify-center my-6">
        <CircularGauge value={soc} color={getSOCColor(soc)} />
      </div>

      <div className="grid grid-cols-3 gap-4 pt-4 border-t border-gray-100">
        <div className="text-center">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Voltage</p>
          <p className="text-lg font-semibold text-gray-700">{voltage?.toFixed(2) ?? '--'}V</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Current</p>
          <p className="text-lg font-semibold text-gray-700">{current?.toFixed(1) ?? '--'}A</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Power</p>
          <p className={`text-lg font-semibold ${power > 0 ? 'text-emerald-500' : power < 0 ? 'text-rose-500' : 'text-gray-700'}`}>
            {power?.toFixed(0) ?? '--'}W
          </p>
        </div>
      </div>
    </div>
  )
}

function SolarCard({ solar }) {
  const power = solar?.power ?? 0
  const voltage = solar?.voltage ?? 0
  const current = solar?.current ?? 0
  const yieldToday = solar?.yield_today ?? 0

  return (
    <div className="bg-white rounded-2xl shadow-lg shadow-amber-100/50 p-6 border border-gray-100">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-amber-100 rounded-lg text-amber-600">
            <SunIcon />
          </div>
          <h3 className="font-semibold text-gray-700">Solar</h3>
        </div>
      </div>

      <div className="flex flex-col items-center my-6">
        <div className="text-5xl font-bold text-amber-500">{power?.toFixed(0) ?? '--'}</div>
        <div className="text-gray-400 text-sm mt-1">watts</div>
      </div>

      <div className="bg-gradient-to-r from-amber-50 to-orange-50 rounded-xl p-4 mb-4">
        <div className="flex justify-between items-center">
          <span className="text-sm text-gray-500">Today's Yield</span>
          <span className="text-xl font-bold text-amber-600">{yieldToday?.toFixed(2) ?? '--'} kWh</span>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 pt-4 border-t border-gray-100">
        <div className="text-center">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Voltage</p>
          <p className="text-lg font-semibold text-gray-700">{voltage?.toFixed(1) ?? '--'}V</p>
        </div>
        <div className="text-center">
          <p className="text-xs text-gray-400 uppercase tracking-wide">Current</p>
          <p className="text-lg font-semibold text-gray-700">{current?.toFixed(1) ?? '--'}A</p>
        </div>
      </div>
    </div>
  )
}

function EnvironmentCard({ environment }) {
  const temp = environment?.temperature ?? null
  const humidity = environment?.humidity ?? null

  return (
    <div className="bg-white rounded-2xl shadow-lg shadow-cyan-100/50 p-6 border border-gray-100">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <div className="p-2 bg-cyan-100 rounded-lg text-cyan-600">
            <ThermometerIcon />
          </div>
          <h3 className="font-semibold text-gray-700">Environment</h3>
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

function App() {
  const [current, setCurrent] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  const fetchData = async () => {
    setRefreshing(true)
    try {
      const response = await fetch(`${API_BASE}/api/current`)
      if (response.ok) {
        const data = await response.json()
        if (!data.error) {
          setCurrent(data)
          setLastUpdate(new Date())
          setError(null)
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

  return (
    <main className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-4 md:p-8">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-8 gap-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">Campervan Monitor</h1>
            <p className="text-gray-500 mt-1">VW California Energy Dashboard</p>
          </div>
          <div className="flex items-center gap-4">
            {lastUpdate && (
              <span className="text-sm text-gray-400">
                Updated {lastUpdate.toLocaleTimeString()}
              </span>
            )}
            <button
              onClick={fetchData}
              disabled={refreshing}
              className="flex items-center gap-2 px-4 py-2 bg-white text-gray-600 rounded-xl shadow-sm hover:shadow-md transition-all border border-gray-200 disabled:opacity-50"
            >
              <RefreshIcon spinning={refreshing} />
              <span className="hidden sm:inline">Refresh</span>
            </button>
          </div>
        </div>

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-red-600">
            {error}
          </div>
        )}

        {/* Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <BatteryCard battery={current?.battery} />
          <SolarCard solar={current?.solar} />
          <EnvironmentCard environment={current?.environment} />
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-gray-400 text-sm">
          Data refreshes automatically every 30 seconds
        </div>
      </div>
    </main>
  )
}

export default App
