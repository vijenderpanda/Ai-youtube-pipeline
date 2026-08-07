import { useState, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { getToken, clearToken, setUnauthorizedHandler } from './api'
import Sidebar from './components/Sidebar'
import LockScreen from './components/LockScreen'
import Overview from './pages/Overview'
import Analytics from './pages/Analytics'
import Calendar from './pages/Calendar'
import Channels from './pages/Channels'
import ChannelDetail from './pages/ChannelDetail'
import ChannelAnalysis from './pages/ChannelAnalysis'
import Jobs from './pages/Jobs'
import Renders from './pages/Renders'
import Posts from './pages/Posts'
import Generators from './pages/Generators'
import Workers from './pages/Workers'
import Studio from './pages/Studio'
import StudioBoard from './pages/StudioBoard'

export default function App() {
  const [authed, setAuthed] = useState(() => !!getToken())
  const [authError, setAuthError] = useState('')

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
      <Sidebar onLock={lock} />
      <main className="main">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/calendar" element={<Calendar />} />
          <Route path="/studio" element={<Studio />} />
          <Route path="/studio/:calendarId" element={<StudioBoard />} />
          <Route path="/channels" element={<Channels />} />
          <Route path="/channels/:channelKey" element={<ChannelDetail />} />
          <Route path="/channels/:channelKey/analysis" element={<ChannelAnalysis />} />
          <Route path="/jobs" element={<Jobs />} />
          <Route path="/renders" element={<Renders />} />
          <Route path="/posts" element={<Posts />} />
          <Route path="/generators" element={<Generators />} />
          <Route path="/workers" element={<Workers />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
