/**
 * marketHours.js
 * NYSE market hours checker.
 * NYSE operates 9:30am - 4:00pm ET (UTC-4 EDT / UTC-5 EST)
 * Lagos is WAT (UTC+1) so NYSE is:
 *   Open:  2:30pm Lagos time
 *   Close: 9:00pm Lagos time
 */

export function getMarketStatus(symbol) {
  // Crypto is always open
  if (!symbol || symbol.includes("/")) {
    return {
      isOpen: true,
      label: "Crypto — 24/7",
      sublabel: "Markets never close",
      color: "#10b981",
      dotColor: "#10b981",
    }
  }

  const now = new Date()

  // Convert to ET (UTC-4 during EDT, UTC-5 during EST)
  // Simple approach: use fixed UTC-4 (EDT) — works for most of year
  const etOffset = -4
  const etNow = new Date(now.getTime() + etOffset * 60 * 60 * 1000)

  const day     = etNow.getUTCDay()    // 0=Sun, 6=Sat
  const hour    = etNow.getUTCHours()
  const minute  = etNow.getUTCMinutes()
  const time    = hour + minute / 60

  const isWeekend  = day === 0 || day === 6
  const isDaySession = time >= 9.5 && time < 16
  const isOpen     = !isWeekend && isDaySession

  // Calculate Lagos time (UTC+1)
  const lagosOffset = 1
  const lagosNow = new Date(
    now.getTime() + lagosOffset * 60 * 60 * 1000
  )
  const lagosHour = lagosNow.getUTCHours()
  const lagosMin  = lagosNow.getUTCMinutes()
  const lagosTime = `${String(lagosHour).padStart(2,"0")}:${String(lagosMin).padStart(2,"0")}`

  // Next open time
  let nextOpen = ""
  if (isWeekend) {
    const daysUntilMon = day === 6 ? 2 : 1
    nextOpen = `Opens Monday 2:30 PM Lagos`
  } else if (time < 9.5) {
    nextOpen = `Opens today at 2:30 PM Lagos`
  } else if (time >= 16) {
    if (day === 5) {
      nextOpen = `Opens Monday 2:30 PM Lagos`
    } else {
      nextOpen = `Opens tomorrow 2:30 PM Lagos`
    }
  }

  return {
    isOpen,
    label: isOpen ? "NYSE Open" : "NYSE Closed",
    sublabel: isOpen
      ? `Closes 9:00 PM Lagos · Now ${lagosTime} WAT`
      : nextOpen || `Closed · Now ${lagosTime} WAT`,
    color: isOpen ? "#10b981" : "#ef4444",
    dotColor: isOpen ? "#10b981" : "#ef4444",
    lagosTime,
  }
}
