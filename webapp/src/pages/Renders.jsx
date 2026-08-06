import { useState } from 'react'
import { api } from '../api'
import { usePoll } from '../hooks'
import Chips, { ChipSearch, ChipsGroup } from '../components/Chips'
import RenderCard from '../components/RenderCard'
import EmptyState from '../components/EmptyState'

const ORIGIN_OPTIONS = [
  { value: '', label: 'All' },
  { value: 'job', label: 'From jobs' },
  { value: 'historical', label: 'Historical' },
]

export default function Renders() {
  const [channel, setChannel] = useState('')
  const [origin, setOrigin] = useState('')
  const [generator, setGenerator] = useState('')
  const [search, setSearch] = useState('')

  const chansQ = usePoll(() => api.get('?r=channels'), 0)
  const gensQ = usePoll(() => api.get('?r=generators'), 0)

  const params = []
  if (channel) params.push(`channel=${encodeURIComponent(channel)}`)
  if (origin) params.push(`origin=${encodeURIComponent(origin)}`)
  if (generator) params.push(`generator=${encodeURIComponent(generator)}`)
  const query = '?r=renders' + (params.length ? '&' + params.join('&') : '')
  const rendersQ = usePoll(() => api.get(query), 0, [query])

  const channels = (chansQ.data && chansQ.data.channels) || []
  const generators = (gensQ.data && gensQ.data.generators) || []
  const renders = (rendersQ.data && rendersQ.data.renders) || []

  const q = search.trim().toLowerCase()
  const filtered = q
    ? renders.filter((r) =>
        [r.title, r.filename, r.storage_path, r.generator, r.channel_key]
          .filter(Boolean)
          .join(' ')
          .toLowerCase()
          .includes(q)
      )
    : renders

  const channelOptions = [
    { value: '', label: 'All channels' },
    ...channels.map((c) => ({ value: c.key, label: c.name || c.key })),
  ]
  const generatorOptions = [
    { value: '', label: 'All generators' },
    ...generators.map((g) => ({ value: g.name, label: g.name })),
  ]

  return (
    <div className="page">
      <header className="page-head">
        <div>
          <h1>Renders</h1>
          <p className="sub">Finished videos, images and audio from the pipeline</p>
        </div>
      </header>

      {rendersQ.error && <div className="error-bar">{rendersQ.error.message}</div>}

      <div className="chips-bar">
        <ChipsGroup label="Origin">
          <Chips options={ORIGIN_OPTIONS} value={origin} onChange={setOrigin} ariaLabel="Origin" />
        </ChipsGroup>
        <ChipsGroup label="Channel">
          <Chips
            options={channelOptions}
            value={channel}
            onChange={setChannel}
            ariaLabel="Channel"
          />
        </ChipsGroup>
        <ChipsGroup label="Generator">
          <Chips
            options={generatorOptions}
            value={generator}
            onChange={setGenerator}
            ariaLabel="Generator"
          />
        </ChipsGroup>
        <ChipSearch value={search} onChange={setSearch} placeholder="Search renders…" />
      </div>

      {rendersQ.loading && rendersQ.data == null ? (
        <p className="dim">Loading…</p>
      ) : filtered.length === 0 ? (
        <EmptyState
          message={
            origin === 'historical'
              ? 'No historical renders yet'
              : 'No renders match these filters'
          }
        />
      ) : (
        <div className="render-grid">
          {filtered.map((r) => (
            <RenderCard key={r.id || r.storage_path} render={r} />
          ))}
        </div>
      )}
    </div>
  )
}
