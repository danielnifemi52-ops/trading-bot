/**
 * Layout.jsx
 * Responsive sidebar layout shell. Includes navigation, top header,
 * and handles main content rendering.
 */
import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'

// Reusable Navigation Link Component with nice SVG icons
function SidebarLink({ to, label, icon, onClick }) {
  return (
    <NavLink
      to={to}
      onClick={onClick}
      style={({ isActive }) => ({
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        padding: '12px 20px',
        color: isActive ? 'var(--text)' : 'var(--muted)',
        background: isActive ? 'rgba(59, 130, 246, 0.1)' : 'transparent',
        borderLeft: isActive ? '3px solid var(--blue)' : '3px solid transparent',
        textDecoration: 'none',
        fontSize: '14px',
        fontWeight: isActive ? '600' : '500',
        transition: 'all 0.2s',
        marginBottom: '4px',
      })}
    >
      {icon}
      {label}
    </NavLink>
  )
}

export default function Layout({ children }) {
  const [mobileOpen, setMobileOpen] = useState(false)
  const location = useLocation()

  // Dynamic page title based on route
  const getPageTitle = () => {
    switch (location.pathname) {
      case '/':
        return 'Bot Dashboard'
      case '/backtest':
        return 'Strategy Backtesting'
      case '/optimizer':
        return 'Parameter Optimization'
      case '/trades':
        return 'Trade Records'
      default:
        return 'RSI Trading Bot'
    }
  }

  // Simple SVG Icons
  const icons = {
    dashboard: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <rect x="3" y="3" width="7" height="9" rx="1" />
        <rect x="14" y="3" width="7" height="5" rx="1" />
        <rect x="14" y="12" width="7" height="9" rx="1" />
        <rect x="3" y="16" width="7" height="5" rx="1" />
      </svg>
    ),
    backtest: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M3 3v18h18" />
        <path d="m19 9-5 5-4-4-3 3" />
      </svg>
    ),
    optimizer: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.1a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
        <circle cx="12" cy="12" r="3" />
      </svg>
    ),
    trades: (
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" />
      </svg>
    ),
  }

  const sidebarStyle = {
    width: '260px',
    background: 'var(--surface)',
    borderRight: '1px solid var(--border)',
    height: '100vh',
    position: 'fixed',
    top: 0,
    left: 0,
    zIndex: 100,
    display: 'flex',
    flexDirection: 'column',
    transform: mobileOpen ? 'translateX(0)' : 'translateX(-260px)',
    transition: 'transform 0.3s ease',
  }

  return (
    <div style={{ minHeight: '100vh', background: 'var(--bg)', color: 'var(--text)' }}>
      {/* Sidebar - Desktop & Mobile */}
      <aside style={{
        ...sidebarStyle,
        transform: 'translateX(0)', // Force visible on desktop
      }} className="desktop-sidebar">
        {/* Brand Header */}
        <div style={{
          padding: '24px 20px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          gap: '12px',
        }}>
          <img 
            src="/logo.png" 
            alt="RSI Bot Logo" 
            style={{ 
              width: '32px', 
              height: '32px', 
              borderRadius: '8px',
              objectFit: 'cover'
            }} 
          />
          <div>
            <h1 style={{ fontSize: '15px', fontWeight: '700', letterSpacing: '0.05em' }}>
              RSI BOT
            </h1>
            <span style={{ fontSize: '10px', color: 'var(--muted)', fontWeight: '600' }}>
              RSI TRADING SUITE
            </span>
          </div>
        </div>

        {/* Navigation */}
        <nav style={{ padding: '24px 0', flex: 1 }}>
          <SidebarLink to="/" label="Dashboard" icon={icons.dashboard} />
          <SidebarLink to="/backtest" label="Backtest Simulator" icon={icons.backtest} />
          <SidebarLink to="/optimizer" label="Parameter Optimizer" icon={icons.optimizer} />
          <SidebarLink to="/trades" label="Trades History" icon={icons.trades} />
        </nav>

        {/* Sidebar Footer */}
        <div style={{
          padding: '20px',
          borderTop: '1px solid var(--border)',
          fontSize: '12px',
          color: 'var(--muted)',
          textAlign: 'center',
        }}>
          v1.0.0 &bull; Ready
        </div>
      </aside>

      {/* Mobile Drawer Sidebar Overlay */}
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.5)',
            zIndex: 99,
          }}
        />
      )}

      {/* Mobile Sidebar */}
      <aside style={{
        ...sidebarStyle,
        transform: mobileOpen ? 'translateX(0)' : 'translateX(-260px)',
      }} className="mobile-sidebar-container">
        <div style={{
          padding: '24px 20px',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <img 
              src="/logo.png" 
              alt="RSI Bot Logo" 
              style={{ 
                width: '32px', 
                height: '32px', 
                borderRadius: '8px',
                objectFit: 'cover'
              }} 
            />
            <h1 style={{ fontSize: '15px', fontWeight: '700' }}>RSI BOT</h1>
          </div>
          <button
            onClick={() => setMobileOpen(false)}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--text)',
              fontSize: '20px',
            }}
          >
            &times;
          </button>
        </div>
        <nav style={{ padding: '24px 0', flex: 1 }}>
          <SidebarLink to="/" label="Dashboard" icon={icons.dashboard} onClick={() => setMobileOpen(false)} />
          <SidebarLink to="/backtest" label="Backtest" icon={icons.backtest} onClick={() => setMobileOpen(false)} />
          <SidebarLink to="/optimizer" label="Optimizer" icon={icons.optimizer} onClick={() => setMobileOpen(false)} />
          <SidebarLink to="/trades" label="Trades" icon={icons.trades} onClick={() => setMobileOpen(false)} />
        </nav>
      </aside>

      {/* Main Content Area */}
      <div style={{ marginLeft: '260px', minHeight: '100vh' }} className="main-content-wrapper">
        {/* Top Header Bar */}
        <header style={{
          height: '70px',
          background: 'var(--surface)',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 32px',
          position: 'sticky',
          top: 0,
          zIndex: 90,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            {/* Hamburger Button for Mobile */}
            <button
              onClick={() => setMobileOpen(true)}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text)',
                fontSize: '20px',
                display: 'none',
                cursor: 'pointer',
              }}
              className="mobile-hamburger"
            >
              &#9776;
            </button>
            <h2 style={{ fontSize: '18px', fontWeight: '600', color: 'var(--text)' }}>
              {getPageTitle()}
            </h2>
          </div>

          {/* Connection Status & Live Info */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              background: 'rgba(255,255,255,0.03)',
              padding: '6px 14px',
              borderRadius: '20px',
              border: '1px solid var(--border)',
              fontSize: '12px',
            }}>
              <span style={{
                width: '6px',
                height: '6px',
                borderRadius: '50%',
                background: 'var(--green)',
                boxShadow: '0 0 8px var(--green)',
              }} />
              <span style={{ color: 'var(--muted)' }}>WS: Connected</span>
            </div>
          </div>
        </header>

        {/* Content Body */}
        <main style={{ padding: '32px', maxWidth: '1600px', margin: '0 auto' }}>
          {children}
        </main>
      </div>

      {/* Simple media queries injection via inline style tag for responsive behaviors */}
      <style>{`
        @media (max-width: 991px) {
          .desktop-sidebar {
            display: none !important;
          }
          .main-content-wrapper {
            margin-left: 0 !important;
          }
          .mobile-hamburger {
            display: block !important;
          }
        }
        @media (min-width: 992px) {
          .mobile-sidebar-container {
            display: none !important;
          }
        }
      `}</style>
    </div>
  )
}
