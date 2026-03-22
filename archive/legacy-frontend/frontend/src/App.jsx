import React, { useEffect, useMemo, useState } from 'react'
import { Upload, Play, CheckCircle2 } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, BarChart, Bar } from 'recharts'

const sliderDefs = [
  { id: 'EX_glc__D_e', label: 'Primary Carbon (Glucose)', min: 0, max: 20, step: 1, defaultValue: 10 },
  { id: 'EX_nh4_e', label: 'Primary Nitrogen (Ammonium)', min: 0, max: 10, step: 1, defaultValue: 5 },
  { id: 'EX_pi_e', label: 'Phosphate', min: 0, max: 10, step: 1, defaultValue: 3 },
  { id: 'EX_so4_e', label: 'Sulfate', min: 0, max: 10, step: 1, defaultValue: 3 },
  { id: 'EX_h2o_e', label: 'Water (unlimited)', min: 0, max: 2000, step: 10, defaultValue: 1000 },
  { id: 'EX_h_e', label: 'Protons (unlimited)', min: 0, max: 2000, step: 10, defaultValue: 1000 },
  { id: 'EX_o2_e', label: 'Oxygen', min: 0, max: 1500, step: 10, defaultValue: 1000 },
]

const initialMedia = sliderDefs.reduce((acc, s) => ({ ...acc, [s.id]: s.defaultValue }), {})

export default function App() {
  const [phase, setPhase] = useState('upload')
  const [sessionId, setSessionId] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [media, setMedia] = useState(initialMedia)
  const [history, setHistory] = useState([])
  const [finalMetrics, setFinalMetrics] = useState(null)

  useEffect(() => {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.host}/api/stream`)
    ws.onmessage = (evt) => {
      const msg = JSON.parse(evt.data)
      if (msg.type === 'metrics') {
        setHistory((prev) => [...prev, msg.payload])
      }
    }
    ws.onerror = () => console.warn('stream socket error')
    return () => ws.close()
  }, [])

  const chartData = useMemo(() => history.map((h, idx) => ({
    t: idx,
    survival: h.objective_value ?? 0,
    product: h.fluxes?.EX_citrate_e ?? 0,
    efficiency: h.fluxes?.EX_glc__D_e ?? 0,
  })), [history])

  async function handleUpload(file) {
    setUploading(true)
    const form = new FormData()
    form.append('file', file)
    const res = await fetch('/api/upload', { method: 'POST', body: form })
    const data = await res.json()
    setSessionId(data.session_id)
    setPhase('simulate')
    setUploading(false)
  }

  async function handleSimulate() {
    if (!sessionId) return
    const res = await fetch('/api/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, media }),
    })
    const data = await res.json()
    setHistory((prev) => [...prev, data])
    await fetch('/api/trajectory', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, media, metrics: data }),
    })
  }

  async function handleFinish() {
    if (!sessionId || !history.length) return
    const last = history[history.length - 1]
    await fetch('/api/finalize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, final_metrics: last }),
    })
    setFinalMetrics(last)
    setPhase('final')
  }

  return (
    <div style={{ padding: '24px', display: 'grid', gap: '16px', maxWidth: 1400, margin: '0 auto' }}>
      <header className="flex" style={{ alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <div style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: 1.4, opacity: 0.7 }}>BioX GEM Lab</div>
          <div style={{ fontSize: 26, fontWeight: 700 }}>Wet-Lab Simulation Console</div>
          <div style={{ fontSize: 14, opacity: 0.7 }}>Session: {sessionId || 'pending upload'}</div>
        </div>
        <div className="card" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{ width: 10, height: 10, borderRadius: 50, background: phase === 'simulate' ? '#34d399' : '#f59e0b' }}></div>
          <div style={{ fontSize: 14 }}>{phase === 'upload' ? 'Upload genome to start' : 'Live simulation'}</div>
        </div>
      </header>

      {phase === 'upload' && (
        <div className="card" style={{ padding: 32, textAlign: 'center', borderStyle: 'dashed' }}>
          <Upload size={32} />
          <p>Drag & drop genome (.faa) or click to select</p>
          <input type="file" accept=".faa" style={{ display: 'none' }} id="upload-input" onChange={(e) => handleUpload(e.target.files[0])} />
          <label className="button" htmlFor="upload-input" style={{ display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            {uploading ? 'Uploading...' : 'Upload Genome'}
          </label>
        </div>
      )}

      {phase === 'simulate' && (
        <div className="grid" style={{ gridTemplateColumns: '360px 1fr', alignItems: 'start' }}>
          <div className="card" style={{ position: 'sticky', top: 16 }}>
            <div style={{ fontWeight: 700, marginBottom: 8 }}>Media Controls</div>
            <div className="grid" style={{ gap: 12 }}>
              {sliderDefs.map((s) => (
                <div key={s.id}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 13 }}>
                    <span>{s.label}</span>
                    <span style={{ opacity: 0.7 }}>{media[s.id]}</span>
                  </div>
                  <input type="range" min={s.min} max={s.max} step={s.step} value={media[s.id]} onChange={(e) => setMedia({ ...media, [s.id]: Number(e.target.value) })} style={{ width: '100%' }} />
                </div>
              ))}
            </div>
            <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
              <button className="button" onClick={handleSimulate} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <Play size={16} /> Simulate
              </button>
              <button className="button" onClick={handleFinish} style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                <CheckCircle2 size={16} /> Finish Tuning
              </button>
            </div>
          </div>

          <div className="grid" style={{ gap: 16 }}>
            <div className="card" style={{ minHeight: 300 }}>
              <div style={{ fontWeight: 700, marginBottom: 8 }}>Live Signals</div>
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
                  <XAxis dataKey="t" stroke="rgba(255,255,255,0.6)" />
                  <YAxis stroke="rgba(255,255,255,0.6)" />
                  <Tooltip contentStyle={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 8 }} />
                  <Line type="monotone" dataKey="survival" stroke="#34d399" strokeWidth={2} dot={false} name="Survival" />
                  <Line type="monotone" dataKey="product" stroke="#60a5fa" strokeWidth={2} dot={false} name="Product" />
                  <Line type="monotone" dataKey="efficiency" stroke="#fbbf24" strokeWidth={2} dot={false} name="Efficiency" />
                </LineChart>
              </ResponsiveContainer>
            </div>

          </div>
        </div>
      )}

      {phase === 'final' && finalMetrics && (
        <div className="card" style={{ padding: 24 }}>
          <div style={{ fontWeight: 700, marginBottom: 12 }}>Final Report</div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={[{ label: 'TRY', ...finalMetrics.fluxes, survival: finalMetrics.objective_value }]}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
              <XAxis dataKey="label" stroke="rgba(255,255,255,0.6)" />
              <YAxis stroke="rgba(255,255,255,0.6)" />
              <Tooltip contentStyle={{ background: '#111827', border: '1px solid #1f2937', borderRadius: 8 }} />
              <Bar dataKey="survival" fill="#34d399" name="Survival" />
              <Bar dataKey="EX_citrate_e" fill="#60a5fa" name="Product (EX_citrate_e)" />
              <Bar dataKey="EX_glc__D_e" fill="#fbbf24" name="Efficiency (EX_glc__D_e)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

    </div>
  )
}
