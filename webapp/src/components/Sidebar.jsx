import { NavLink } from 'react-router-dom'

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

const NAV = [
  { to: '/', label: 'Overview', icon: 'overview', end: true },
  { to: '/analytics', label: 'Analytics', icon: 'analytics' },
  { to: '/calendar', label: 'Calendar', icon: 'calendar' },
  { to: '/studio', label: 'Studio', icon: 'studio' },
  { to: '/channels', label: 'Channels', icon: 'channels' },
  { to: '/jobs', label: 'Jobs', icon: 'jobs' },
  { to: '/renders', label: 'Renders', icon: 'renders' },
  { to: '/posts', label: 'Posts', icon: 'posts' },
  { to: '/generators', label: 'Generators', icon: 'generators' },
  { to: '/workers', label: 'Workers', icon: 'workers' },
]

export default function Sidebar({ onLock }) {
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
        {NAV.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => 'nav-item' + (isActive ? ' active' : '')}
          >
            <Icon name={item.icon} />
            <span className="nav-label">{item.label}</span>
          </NavLink>
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
