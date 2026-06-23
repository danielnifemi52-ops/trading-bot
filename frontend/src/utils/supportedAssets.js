/**
 * supportedAssets.js
 * Single source of truth for all tradeable symbols.
 * Only symbols confirmed working on Alpaca paper trading.
 */

export const CRYPTO_SYMBOLS = [
  "BTC/USD",
  "ETH/USD",
  "SOL/USD",
  "DOGE/USD",
  "LTC/USD",
  "BCH/USD",
  "LINK/USD",
  "AAVE/USD",
]

export const STOCK_SYMBOLS = [
  "AAPL", "MSFT", "GOOGL", "AMZN", "META",
  "NVDA", "TSLA", "AMD",   "NFLX", "V",
  "MA",   "JPM",  "BAC",   "GS",   "PYPL",
  "INTC", "CRM",  "ORCL",  "ADBE", "QCOM",
]

export const ETF_SYMBOLS = [
  "SPY", "QQQ", "IWM", "DIA", "VTI",
  "ARKK","GLD", "SLV", "TLT", "XLF",
]

export const isCrypto = (symbol) => 
  symbol?.includes("/")

export const isSupported = (symbol) => 
  CRYPTO_SYMBOLS.includes(symbol) ||
  STOCK_SYMBOLS.includes(symbol) ||
  ETF_SYMBOLS.includes(symbol)

export const ALL_SYMBOLS = [
  ...CRYPTO_SYMBOLS,
  ...STOCK_SYMBOLS,
  ...ETF_SYMBOLS,
]
