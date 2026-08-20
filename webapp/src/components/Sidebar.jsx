import { NavLink } from 'react-router-dom'
import { api } from '../api'
import { usePoll } from '../hooks'
import { resolveStage } from '../pipeline'

function Icon({ name }) {
  const paths = {
    overview: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1.5" />
        <rect x="14" y="3" width="7" height="7" rx="1.5" />
        <rect x="3" y="14" width="7" height="7" rx="1.5" />
        <rect x="14" y="14" width="7" height="7" rx="1.5" />
      </>
    ),
    analytics: (
      <>
        <path d="M3 3v18h18" />
        <path d="M7 15l4-5 3 3 5-7" />
      </>
    ),
    calendar: (
      <>
        <rect x="3" y="5" width="18" height="16" rx="2" />
        <path d="M8 3v4M16 3v4M3 10h18" />
      </>
    ),
    channels: (
      <>
        <rect x="2" y="7" width="20" height="14" rx="2" />
        <path d="M8 2l4 4 4-4" />
      </>
    ),
    studio: (
      <>
        <path d="M12 3l9 5-9 5-9-5 9-5z" />
        <path d="M3 13l9 5 9-5" />
      </>
    ),
    jobs: (
      <>
        <path d="M4 6h16" />
        <path d="M4 12h16" />
        <path d="M4 18h10" />
      </>
    ),
    renders: (
      <>
        <rect x="3" y="4" width="18" height="16" rx="2" />
        <path d="M7 4v16M17 4v16M3 9h4M3 15h4M17 9h4M17 15h4" />
      </>
    ),
    posts: (
      <>
        <path d="M22 2L11 13" />
        <path d="M22 2l-7 20-4-9-9-4 20-7z" />
      </>
    ),
    generators: (
      <>
        <rect x="5" y="5" width="14" height="14" rx="2" />
        <path d="M9 2v3M15 2v3M9 19v3M15 19v3M2 9h3M2 15h3M19 9h3M19 15h3" />
      </>
    ),
    workers: (
      <>
        <rect x="4" y="4" width="16" height="8" rx="1.5" />
        <rect x="4" y="14" width="16" height="6" rx="1.5" />
        <path d="M8 8h.01M8 17h.01" />
      </>
    ),
    lock: (
      <>
        <rect x="4" y="11" width="16" height="10" rx="2" />
        <path d="M8 11V7a4 4 0 0 1 8 0v4" />
      </>
    ),
  }
  return (
    <svg
      width="17"
      height="17"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name]}
    </svg>
  )
}

/**
 * Workflow-spine navigation (global IA redesign): Today, then CREATE → GROW,
 * with machine internals dimmed under BEHIND THE SCENES. Routes never change —
 * only labels, grouping and emphasis. Max two badges in the whole sidebar:
 * Today (things waiting on the creator) and Activity (failed tasks).
 */
const NAV_GROUPS = [
  {
    label: null,
    items: [
      { to: '/', label: 'Today', icon: 'overview', end: true, badge: 'today' },
      { to: '/make', label: 'Make', icon: 'studio' },
      { to: '/plan', label: 'Plan', icon: 'calendar' },
      { to: '/looks', label: 'Looks', icon: 'renders' },
      { to: '/scoreboard', label: 'Scoreboard', icon: 'analytics' },
      { to: '/machines', label: 'Machines', icon: 'workers' },
    ],
  },
]

export default function Sidebar({ onLock }) {
  // Badge data rides the endpoints the app already polls elsewhere.
  const stagedQ = usePoll(() => api.get('?r=staged'), 15000)
  const jobsQ = usePoll(() => api.get('?r=jobs&limit=100'), 30000)

  const items = (stagedQ.data && stagedQ.data.items) || []
  const counts = (stagedQ.data && stagedQ.data.counts) || {}
  const allJobs = (jobsQ.data && jobsQ.data.jobs) || []
  // A piece mid-produce is the factory working, not a decision — counting it
  // here is the same lie the old Overview told by dropping this flag.
  const producingIds = new Set(
    allJobs
      .filter((j) => j.type === 'produce_preview' && (j.status === 'queued' || j.status === 'running'))
      .map((j) => j.meta && j.meta.calendar_id)
      .filter(Boolean)
  )
  const todayCount = items.filter(
    (it) => resolveStage(it, counts[it.id] || {}, { producing: producingIds.has(it.id) }).action
  ).length
  const failedCount = allJobs.filter((j) => j.status === 'failed').length

  const badge = (kind) => {
    if (kind === 'today' && todayCount > 0)
      return <span className="nav-badge nav-badge-today">{todayCount}</span>
    if (kind === 'failed' && failedCount > 0)
      return <span className="nav-badge nav-badge-failed">{failedCount}</span>
    return null
  }

  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-dot" />
        <div className="brand-text">
          <div className="brand-name">THE FACTORY</div>
          <div className="brand-sub">control room</div>
        </div>
      </div>
      <nav className="nav">
        {NAV_GROUPS.map((g, gi) => (
          <div key={gi} className={'nav-group' + (g.quiet ? ' nav-group-quiet' : '')}>
            {g.label && <div className="nav-group-label">{g.label}</div>}
            {g.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) => 'nav-item' + (isActive ? ' active' : '')}
              >
                <Icon name={item.icon} />
                <span className="nav-label">{item.label}</span>
                {item.badge && badge(item.badge)}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
      <div className="sidebar-foot">
        <button className="nav-item nav-btn" onClick={onLock} title="Forget token and lock">
          <Icon name="lock" />
          <span className="nav-label">Lock</span>
        </button>
      </div>
    </aside>
  )
}
