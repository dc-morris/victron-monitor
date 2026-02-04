// Lead-acid/AGM 12V battery voltage to SOC lookup table
export const VOLTAGE_SOC_TABLE = [
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

export function voltageToSOC(voltage) {
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

export function formatTime(date) {
  return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })
}

export function getStateLabel(state) {
  if (state === 'charging' || state === '1' || state === 1) return 'Charging'
  if (state === 'discharging' || state === '2' || state === 2) return 'Discharging'
  if (state === 'idle' || state === '0' || state === 0) return 'Idle'
  return 'Unknown'
}

export function getSOCColor(soc) {
  if (soc === null) return '#9ca3af'
  if (soc >= 80) return '#10b981'
  if (soc >= 50) return '#f59e0b'
  if (soc >= 20) return '#f97316'
  return '#ef4444'
}
