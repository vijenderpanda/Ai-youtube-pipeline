import { useState, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { getToken, clearToken, setUnauthorizedHandler } from './api'
import { useVersionWatch } from './useVersionWatch'
import Sidebar from './components/Sidebar'
import LockScreen from './components/LockScreen'
import Overview from './pages/Overview'
import Analytics from './pages/Analytics'
import Calendar from './pages/Calendar'
import Channels from './pages/Channels'
import ChannelWizard from './pages/ChannelWizard'
import ChannelDetail from './pages/ChannelDetail'
import ChannelAnalysis from './pages/ChannelAnalysis'
import Jobs from './pages/Jobs'
import Renders from './pages/Renders'
import Posts from './pages/Posts'
import Generators from './pages/Generators'
import Workers from './pages/Workers'
import Studio from './pages/Studio'
import StudioBoard from './pages/StudioBoard'
import Piece from './pages/Piece'
import Make from './pages/Make'
import Today from './pages/Today'
import Looks from './pages/Looks'
import Scoreboard from './pages/Scoreboard'
import TemplateLibrary from './pages/TemplateLibrary'
import TemplateDetail from './pages/TemplateDetail'
import Assets from './pages/Assets'

export default function App() {
  const [authed, setAuthed] = useState(() => !!getToken())
  const [authError, setAuthError] = useState('')
  const staleBuild = useVersionWatch()

  useEffect(() => {
    setUnauthorizedHandler((err) => {
      clearToken()
      setAuthError(err.message || 'Token rejected — enter it again')
      setAuthed(false)
    })
    return () => setUnauthorizedHandler(null)
  }, [])

  const lock = () => {
    clearToken()
    setAuthError('')
    setAuthed(false)
  }

  if (!authed) {
    return (
      <LockScreen
        initialError={authError}
        onUnlock={() => {
          setAuthError('')
          setAuthed(true)
        }}
      />
    )
  }

  return (
    <div className="shell">
      {staleBuild && (
        <div className="update-banner" role="status">
          <span>A newer dashboard version is live — reload to see the latest episodes &amp; features.</span>
          <button className="btn btn-primary btn-sm" onClick={() => window.location.reload()}>
            Reload now
          </button>
        </div>
      )}
      <Sidebar onLock={lock} />
      <main className="main">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/studio" element={<Studio />} />
          {/* Template Library routes MUST precede /studio/:calendarId so the
              literal "templates" segment isn't captured as a calendarId. */}
          <Route path="/studio/templates" element={<TemplateLibrary />} />
          <Route path="/studio/templates/:key" element={<TemplateDetail />} />
          <Route path="/studio/:calendarId" element={<StudioBoard />} />
          {/* One Desk slice 1 — the piece's own page, beside the old board
              while it's proven on real production. */}
          <Route path="/piece/:calendarId" element={<Piece />} />
          {/* One Desk · Make — the on-demand proposer (no overnight daemon). */}
          <Route path="/make" element={<Make />} />
          <Route path="/make/:channelKey" element={<Make />} />
          {/* One Desk · Today — triage that can reach zero. */}
          <Route path="/today" element={<Today />} />
          {/* One Desk · Looks — the locked design + its frames. */}
          <Route path="/looks" element={<Looks />} />
          <Route path="/looks/:templateKey" element={<Looks />} />
          {/* One Desk · Scoreboard — the verdict, once the clock allows one. */}
          <Route path="/scoreboard" element={<Scoreboard />} />
          <Route path="/channels" element={<Channels />} />
          <Route path="/channels/new" element={<ChannelWizard />} />
          <Route path="/channels/:channelKey" element={<ChannelDetail />} />
          <Route path="/channels/:channelKey/analysis" element={<ChannelAnalysis />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/renders" element={<Renders />} />
          <Route path="/posts" element={<Posts />} />
          {/* Archived 2026-08-19 — folded into Templates + Library. Redirect to keep
              old links working; page components (Generators/Assets) kept for history. */}
          <Route path="/generators" element={<Navigate to="/studio/templates" replace />} />
          <Route path="/assets" element={<Navigate to="/renders" replace />} />
          <Route path="/workers" element={<Workers />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
