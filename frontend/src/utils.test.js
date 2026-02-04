import { describe, it, expect } from 'vitest'
import { voltageToSOC, getStateLabel, getSOCColor } from './utils'

describe('voltageToSOC', () => {
  it('returns null for null input', () => {
    expect(voltageToSOC(null)).toBe(null)
  })

  it('returns null for undefined input', () => {
    expect(voltageToSOC(undefined)).toBe(null)
  })

  it('returns 100 for voltage at or above 12.70V', () => {
    expect(voltageToSOC(12.70)).toBe(100)
    expect(voltageToSOC(12.80)).toBe(100)
    expect(voltageToSOC(13.00)).toBe(100)
  })

  it('returns 0 for voltage at or below 10.50V', () => {
    expect(voltageToSOC(10.50)).toBe(0)
    expect(voltageToSOC(10.00)).toBe(0)
    expect(voltageToSOC(9.50)).toBe(0)
  })

  it('returns 90 for voltage at 12.50V', () => {
    expect(voltageToSOC(12.50)).toBe(90)
  })

  it('returns 50 for voltage at 12.06V', () => {
    expect(voltageToSOC(12.06)).toBe(50)
  })

  it('interpolates between table values', () => {
    // Between 12.70 (100%) and 12.50 (90%)
    const soc = voltageToSOC(12.60)
    expect(soc).toBeGreaterThan(90)
    expect(soc).toBeLessThan(100)
    expect(soc).toBe(95) // Midpoint
  })

  it('handles typical resting voltage of 12.4V', () => {
    const soc = voltageToSOC(12.40)
    expect(soc).toBeGreaterThanOrEqual(70)
    expect(soc).toBeLessThanOrEqual(80)
  })

  it('handles low battery voltage of 11.5V', () => {
    const soc = voltageToSOC(11.50)
    expect(soc).toBeGreaterThanOrEqual(10)
    expect(soc).toBeLessThanOrEqual(20)
  })
})

describe('getStateLabel', () => {
  it('returns Charging for charging states', () => {
    expect(getStateLabel('charging')).toBe('Charging')
    expect(getStateLabel('1')).toBe('Charging')
    expect(getStateLabel(1)).toBe('Charging')
  })

  it('returns Discharging for discharging states', () => {
    expect(getStateLabel('discharging')).toBe('Discharging')
    expect(getStateLabel('2')).toBe('Discharging')
    expect(getStateLabel(2)).toBe('Discharging')
  })

  it('returns Idle for idle states', () => {
    expect(getStateLabel('idle')).toBe('Idle')
    expect(getStateLabel('0')).toBe('Idle')
    expect(getStateLabel(0)).toBe('Idle')
  })

  it('returns Unknown for unrecognized states', () => {
    expect(getStateLabel('unknown')).toBe('Unknown')
    expect(getStateLabel(null)).toBe('Unknown')
    expect(getStateLabel(undefined)).toBe('Unknown')
    expect(getStateLabel(99)).toBe('Unknown')
  })
})

describe('getSOCColor', () => {
  it('returns gray for null SOC', () => {
    expect(getSOCColor(null)).toBe('#9ca3af')
  })

  it('returns green for SOC >= 80%', () => {
    expect(getSOCColor(80)).toBe('#10b981')
    expect(getSOCColor(90)).toBe('#10b981')
    expect(getSOCColor(100)).toBe('#10b981')
  })

  it('returns yellow/amber for SOC 50-79%', () => {
    expect(getSOCColor(50)).toBe('#f59e0b')
    expect(getSOCColor(65)).toBe('#f59e0b')
    expect(getSOCColor(79)).toBe('#f59e0b')
  })

  it('returns orange for SOC 20-49%', () => {
    expect(getSOCColor(20)).toBe('#f97316')
    expect(getSOCColor(35)).toBe('#f97316')
    expect(getSOCColor(49)).toBe('#f97316')
  })

  it('returns red for SOC < 20%', () => {
    expect(getSOCColor(0)).toBe('#ef4444')
    expect(getSOCColor(10)).toBe('#ef4444')
    expect(getSOCColor(19)).toBe('#ef4444')
  })
})
