import { useState, useRef, useCallback } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

/* ── icons ── */
const IconUpArrow = () => (
  <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
    <path d="M18 26V12M12 18l6-6 6 6" stroke="url(#uag)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M7 28h22" stroke="url(#uag)" strokeWidth="2.2" strokeLinecap="round"/>
    <defs>
      <linearGradient id="uag" x1="7" y1="12" x2="29" y2="28" gradientUnits="userSpaceOnUse">
        <stop stopColor="#6366f1"/><stop offset="1" stopColor="#8b5cf6"/>
      </linearGradient>
    </defs>
  </svg>
)
const IconPDF = () => (
  <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
    <path d="M5 5C5 3.895 5.895 3 7 3h10l8 8v13c0 1.105-.895 2-2 2H7c-1.105 0-2-.895-2-2V5z" fill="rgba(239,68,68,.15)"/>
    <path d="M17 3l8 8h-5a2 2 0 01-2-2V3z" fill="rgba(239,68,68,.3)"/>
    <text x="8" y="21" fontFamily="Inter,sans-serif" fontWeight="700" fontSize="7" fill="#f87171">PDF</text>
  </svg>
)
const IconX = () => (
  <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
    <path d="M2 2l11 11M13 2L2 13" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"/>
  </svg>
)
const IconCheck = () => (
  <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
    <path d="M2 7l4 4 6-6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)
const IconAnalyze = () => (
  <svg width="17" height="17" viewBox="0 0 17 17" fill="none">
    <circle cx="8.5" cy="8.5" r="6.5" stroke="currentColor" strokeWidth="1.4"/>
    <path d="M5.5 8.5l2 2 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)
const IconReset = () => (
  <svg width="15" height="15" viewBox="0 0 15 15" fill="none">
    <path d="M2 7.5C2 4.5 4.5 2 7.5 2c2 0 3.7.9 4.8 2.3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
    <path d="M13 7.5C13 10.5 10.5 13 7.5 13c-2 0-3.7-.9-4.8-2.3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round"/>
    <path d="M11 2.5l1.8 1.8-1.8 0" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
    <path d="M4 12.5l-1.8-1.8 1.8 0" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round"/>
  </svg>
)

function fmtBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

const STEPS = ['Upload', 'Extract', 'AI Map', 'Validate', 'Done']

/* simulate staged progress during the real API call */
function useProgress() {
  const [step, setStep]     = useState(-1)   // index into STEPS
  const [pct, setPct]       = useState(0)
  const [label, setLabel]   = useState('')
  const timerRef = useRef(null)

  function startProgress() {
    setStep(0); setPct(5); setLabel('Uploading PDF…')
    let s = 0
    const schedule = [
      [1200, 1, 'Extracting text…',        25],
      [3500, 2, 'AI clause mapping…',      50],
      [6000, 3, 'Running validation…',     80],
    ]
    schedule.forEach(([delay, stepIdx, lbl, p]) => {
      const id = setTimeout(() => { setStep(stepIdx); setLabel(lbl); setPct(p) }, delay)
      timerRef.current = id
    })
  }

  function finishProgress() {
    if (timerRef.current) clearTimeout(timerRef.current)
    setStep(4); setLabel('Done!'); setPct(100)
  }

  function resetProgress() {
    setStep(-1); setPct(0); setLabel('')
  }

  return { step, pct, label, startProgress, finishProgress, resetProgress }
}

export default function UploadPanel() {
  const fileInputRef = useRef(null)
  const [file, setFile]       = useState(null)
  const [dragging, setDragging] = useState(false)
  const [phase, setPhase]     = useState('idle')   // idle | loading | success | error
  const [result, setResult]   = useState(null)
  const [errorMsg, setErrorMsg] = useState('')
  const { step, pct, label, startProgress, finishProgress, resetProgress } = useProgress()

  /* ── file helpers ── */
  function acceptFile(f) {
    if (!f || !f.name.toLowerCase().endsWith('.pdf')) {
      alert('Only PDF files are accepted.')
      return
    }
    if (f.size > 50 * 1024 * 1024) {
      alert('File exceeds 50 MB limit.')
      return
    }
    setFile(f)
  }

  const onDrop = useCallback(e => {
    e.preventDefault(); setDragging(false)
    acceptFile(e.dataTransfer.files[0])
  }, [])

  const onDragOver = e => { e.preventDefault(); setDragging(true) }
  const onDragLeave = () => setDragging(false)

  function onFileChange(e) { acceptFile(e.target.files[0]) }

  function removeFile() {
    setFile(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  /* ── analysis ── */
  async function runAnalysis() {
    if (!file) return
    setPhase('loading')
    setErrorMsg('')
    startProgress()

    const formData = new FormData()
    formData.append('pdf', file)

    try {
      const res = await fetch(`${API_BASE}/api/analyze`, {
        method: 'POST',
        body: formData,
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || `Server error ${res.status}`)
      finishProgress()
      setTimeout(() => {
        setResult(data)
        setPhase('success')
      }, 600)
    } catch (err) {
      finishProgress()
      setErrorMsg(err.message || 'Unknown error')
      setTimeout(() => setPhase('error'), 400)
    }
  }

  function reset() {
    setFile(null)
    setPhase('idle')
    setResult(null)
    setErrorMsg('')
    resetProgress()
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  /* ── render ── */
  if (phase === 'success' && result) {
    return <ResultsPanel result={result} onReset={reset} />
  }

  if (phase === 'error') {
    return (
      <div className="error-card">
        <svg width="36" height="36" viewBox="0 0 36 36" fill="none"><circle cx="18" cy="18" r="16" stroke="#f87171" strokeWidth="1.5"/><path d="M18 11v9M18 23v1.5" stroke="#f87171" strokeWidth="2.2" strokeLinecap="round"/></svg>
        <h4>Analysis failed</h4>
        <p>{errorMsg}</p>
        <button className="btn-secondary" onClick={reset}><IconReset /> Try again</button>
      </div>
    )
  }

  if (phase === 'loading') {
    return (
      <div className="progress-card">
        <div className="progress-header-row">
          <span style={{ color: 'var(--text-2)', fontSize: 14, fontWeight: 500 }}>{label}</span>
          <span className="progress-pct">{pct}%</span>
        </div>
        <div className="progress-track">
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
        <div className="steps-row">
          {STEPS.map((s, i) => (
            <>
              <div key={s} className={`step${step === i ? ' active' : step > i ? ' done' : ''}`}>
                <div className="step-dot">
                  {step > i ? <IconCheck /> : i + 1}
                </div>
                <span className="step-label">{s}</span>
              </div>
              {i < STEPS.length - 1 && (
                <div key={`l${i}`} className={`step-line${step > i ? ' done' : ''}`} />
              )}
            </>
          ))}
        </div>
      </div>
    )
  }

  /* idle */
  return (
    <div>
      {/* drop zone */}
      <div
        className={`drop-zone${dragging ? ' drag-over' : ''}`}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onClick={() => !file && fileInputRef.current?.click()}
        tabIndex={0}
        onKeyDown={e => e.key === 'Enter' && fileInputRef.current?.click()}
        role="button"
        aria-label="Upload PDF"
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf"
          hidden
          onChange={onFileChange}
        />
        <div className="drop-icon"><IconUpArrow /></div>
        <p className="drop-title">Drop your contract PDF here</p>
        <p className="drop-sub">
          or <span onClick={e => { e.stopPropagation(); fileInputRef.current?.click() }}>browse files</span>
        </p>
        <p className="drop-hint">Supports: PDF · Max 50 MB</p>
      </div>

      {/* file preview */}
      {file && (
        <div className="file-preview">
          <div className="file-pdf-icon"><IconPDF /></div>
          <div className="file-meta">
            <span className="file-meta-name">{file.name}</span>
            <span className="file-meta-size">{fmtBytes(file.size)}</span>
          </div>
          <button className="file-remove" onClick={removeFile} aria-label="Remove">
            <IconX />
          </button>
        </div>
      )}

      {/* analyze button */}
      {file && (
        <div className="analyze-row">
          <button className="btn-analyze" onClick={runAnalysis}>
            <IconAnalyze /> Run Analysis
          </button>
        </div>
      )}
    </div>
  )
}

/* ── Results sub-panel ── */
function ResultsPanel({ result, onReset }) {
  const [search, setSearch]     = useState('')
  const [filter, setFilter]     = useState('all')

  const clauses     = result.clauses || []
  const foundCount  = result.found_count  ?? clauses.filter(c => c.status === 'found').length
  const missingCount = result.missing_count ?? clauses.filter(c => c.final_status === 'truly_missing').length
  const total       = result.total_gcc_clauses ?? clauses.length
  const pages       = result.page_count ?? '—'

  const filtered = clauses.filter(c => {
    const matchFilter =
      filter === 'all' ||
      (filter === 'found'         && (c.status === 'found' || c.final_status === 'found')) ||
      (filter === 'present_fuzzy' && (c.status === 'present_fuzzy' || c.final_status === 'present_fuzzy')) ||
      (filter === 'missing'       && (c.final_status === 'truly_missing' || c.status === 'missing'))

    const q = search.toLowerCase()
    const matchSearch =
      !search ||
      (c.clause_id || '').toLowerCase().includes(q) ||
      (c.clause_title || '').toLowerCase().includes(q)

    return matchFilter && matchSearch
  })

  const foundPct   = total ? Math.round((foundCount / total) * 100) : 0
  const missingPct = total ? Math.round((missingCount / total) * 100) : 0

  const statusLabel = s => {
    if (!s) return 'Unknown'
    if (s === 'found')          return 'Found'
    if (s === 'present_fuzzy')  return 'Fuzzy'
    if (s === 'truly_missing')  return 'Missing'
    if (s === 'needs_review')   return 'Review'
    return s
  }
  const statusCls = s => {
    if (!s) return ''
    if (s === 'found')          return 'found'
    if (s === 'present_fuzzy')  return 'present_fuzzy'
    if (s === 'truly_missing')  return 'missing'
    if (s === 'needs_review')   return 'needs_review'
    return ''
  }

  return (
    <div className="results-section">
      <div className="results-header">
        <h3>Analysis Complete</h3>
        <span className="results-badge">✓ {result.filename || 'Contract'}</span>
      </div>

      {/* stat cards */}
      <div className="stat-grid">
        <div className="stat-card found">
          <div className="stat-label">Clauses Found</div>
          <div className="stat-value">{foundCount}</div>
          <div className="stat-bar"><div className="stat-bar-fill" style={{ width: `${foundPct}%` }} /></div>
        </div>
        <div className="stat-card missing">
          <div className="stat-label">Missing</div>
          <div className="stat-value">{missingCount}</div>
          <div className="stat-bar"><div className="stat-bar-fill" style={{ width: `${missingPct}%` }} /></div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Total GCC Clauses</div>
          <div className="stat-value">{total}</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">Pages Scanned</div>
          <div className="stat-value">{pages}</div>
        </div>
      </div>

      {/* clause table */}
      <div className="table-card">
        <div className="table-controls">
          <div className="search-wrap">
            <span className="search-icon">
              <svg width="15" height="15" viewBox="0 0 15 15" fill="none"><circle cx="6.5" cy="6.5" r="5" stroke="currentColor" strokeWidth="1.3"/><path d="M10.5 10.5l3 3" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round"/></svg>
            </span>
            <input
              className="table-search"
              placeholder="Search clauses…"
              value={search}
              onChange={e => setSearch(e.target.value)}
            />
          </div>
          <div className="filter-tabs">
            {['all','found','present_fuzzy','missing'].map(f => (
              <button
                key={f}
                className={`filter-tab${filter === f ? ' active' : ''}`}
                onClick={() => setFilter(f)}
              >
                {f === 'all' ? 'All' : f === 'present_fuzzy' ? 'Fuzzy' : f.charAt(0).toUpperCase() + f.slice(1)}
              </button>
            ))}
          </div>
        </div>

        <div className="table-scroll">
          {filtered.length === 0 ? (
            <div className="no-rows">No clauses match your filter.</div>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Clause ID</th>
                  <th>Title</th>
                  <th>Risk</th>
                  <th>Status</th>
                  <th>Page</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((c, i) => {
                  const st = c.final_status || c.status || ''
                  const risk = (c.risk_category || '').toLowerCase()
                  return (
                    <tr key={c.clause_id || i}>
                      <td>{c.clause_id || '—'}</td>
                      <td style={{ maxWidth: 260, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{c.clause_title || '—'}</td>
                      <td><span className={`pill ${risk}`}>{c.risk_category || '—'}</span></td>
                      <td><span className={`pill ${statusCls(st)}`}>{statusLabel(st)}</span></td>
                      <td>{c.page_number ?? '—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          )}
        </div>
      </div>

      <button className="btn-secondary" onClick={onReset}>
        <IconReset /> Analyze another
      </button>
    </div>
  )
}

