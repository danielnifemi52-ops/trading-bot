/**
 * App.jsx
 * Root application component. Sets up React Router and wraps every
 * page inside the shared Layout sidebar/topbar shell.
 */
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Backtest from './pages/Backtest'
import Optimizer from './pages/Optimizer'
import Trades from './pages/Trades'
import './styles/globals.css'

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/"          element={<Dashboard />} />
          <Route path="/backtest"  element={<Backtest />} />
          <Route path="/optimizer" element={<Optimizer />} />
          <Route path="/trades"    element={<Trades />} />
          <Route path="*"          element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  )
}