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
          <Route path="/channels" element={<Channels />} />
          <Route path="/channels/new" element={<ChannelWizard />} />
          <Route path="/channels/:channelKey" element={<ChannelDetail />} />
          <Route path="/channels/:channelKey/analysis" element={<ChannelAnalysis />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/renders" element={<Renders />} />
          <Route path="/posts" element={<Posts />} />
          <Route path="/generators" element={<Generators />} />
          <Route path="/workers" element={<Workers />} />
          <Route path="/assets" element={<Assets />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
