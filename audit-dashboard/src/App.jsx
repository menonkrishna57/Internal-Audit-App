import { useState, useEffect, useCallback, useRef } from 'react'

// ── Nav Icons (inline SVG, no external icon lib needed) ──────────────────────
const Icons = {
  Dashboard: () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="1" y="1" width="6" height="6" rx="1"/><rect x="9" y="1" width="6" height="6" rx="1"/>
      <rect x="1" y="9" width="6" height="6" rx="1"/><rect x="9" y="9" width="6" height="6" rx="1"/>
    </svg>
  ),
  Rules: () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M2 4h12M2 8h8M2 12h10"/>
    </svg>
  ),
  Findings: () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="7" cy="7" r="5"/><path d="M11 11l3 3"/>
    </svg>
  ),
  Reports: () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="2" y="1" width="12" height="14" rx="1"/>
      <path d="M5 5h6M5 8h6M5 11h4"/>
    </svg>
  ),
  Settings: () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="8" cy="8" r="2"/>
      <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.05 3.05l1.41 1.41M11.54 11.54l1.41 1.41M3.05 12.95l1.41-1.41M11.54 4.46l1.41-1.41"/>
    </svg>
  ),
  Loader: () => (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" className="animate-spin">
      <path d="M8 1.5A6.5 6.5 0 1 1 1.5 8"/>
    </svg>
  ),
}

// ── Severity helpers ──────────────────────────────────────────────────────────
const SEV_ORDER = { critical: 0, high: 1, medium: 2, low: 3 }

function severityStampClass(sev) {
  const s = sev?.toLowerCase()
  if (s === 'critical' || s === 'high') return 'stamp stamp-critical'
  return 'stamp stamp-medium'
}

function severityLabel(sev) {
  return sev?.toUpperCase() ?? 'UNKNOWN'
}

function sortBySeverity(results) {
  return [...results].sort((a, b) => {
    const ao = SEV_ORDER[a.severity?.toLowerCase()] ?? 99
    const bo = SEV_ORDER[b.severity?.toLowerCase()] ?? 99
    return ao - bo
  })
}

// ── Generate a run ID from today's date ──────────────────────────────────────
function makeRunId() {
  const d = new Date()
  const ymd = d.toISOString().slice(0, 10).replace(/-/g, '-')
  const seq = String(Math.floor(Math.random() * 9000) + 1000)
  return `#${ymd}-${seq}`
}

// ── Removed SVG roughen filter (simplified badge design) ──────────────────────

// ── NavRail ───────────────────────────────────────────────────────────────────
const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard', Icon: Icons.Dashboard },
  { id: 'rules',     label: 'Rules',     Icon: Icons.Rules     },
  { id: 'findings',  label: 'Findings',  Icon: Icons.Findings  },
  { id: 'reports',   label: 'Reports',   Icon: Icons.Reports   },
  { id: 'settings',  label: 'Settings',  Icon: Icons.Settings  },
]

function NavRail({ active, setActive }) {
  return (
    <nav
      className="nav-rail"
      style={{
        width: 220,
        minWidth: 220,
        background: '#1E2C3A',
        height: '100vh',
        position: 'fixed',
        left: 0,
        top: 0,
        display: 'flex',
        flexDirection: 'column',
        zIndex: 10,
        borderRight: '1px solid #2a3e52',
      }}
    >
      {/* Wordmark */}
      <div style={{ padding: '22px 20px 24px' }}>
        <div style={{
          fontFamily: 'Newsreader, Georgia, serif',
          fontSize: '1.1rem',
          color: '#B08F4F',
          letterSpacing: '0.02em',
          lineHeight: 1.2,
        }}>
          Vault<span style={{ color: '#DCD3B8', fontWeight: 400 }}>Audit</span>
        </div>
        <div style={{
          fontFamily: 'Inter, sans-serif',
          fontSize: '0.65rem',
          color: '#4a6070',
          marginTop: 2,
          letterSpacing: '0.08em',
          textTransform: 'uppercase',
        }}>
          Compliance Case File
        </div>
      </div>

      {/* Nav items */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 2, paddingRight: 12 }}>
        {NAV_ITEMS.map(({ id, label, Icon }) => (
          <button
            key={id}
            id={`nav-${id}`}
            className={`nav-item${active === id ? ' active' : ''}`}
            onClick={() => setActive(id)}
            aria-current={active === id ? 'page' : undefined}
          >
            <Icon />
            <span>{label}</span>
          </button>
        ))}
      </div>

      {/* Version footer */}
      <div style={{
        padding: '16px 20px',
        fontSize: '0.65rem',
        color: '#2f4455',
        fontFamily: 'JetBrains Mono, monospace',
        borderTop: '1px solid #2a3e52',
      }}>
        v0.1.0 · audit-engine
      </div>
    </nav>
  )
}

// ── Bottom nav (mobile) ───────────────────────────────────────────────────────
function BottomNav({ active, setActive }) {
  return (
    <nav
      className="bottom-nav"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        background: '#1E2C3A',
        borderTop: '1px solid #2a3e52',
        zIndex: 20,
        justifyContent: 'space-around',
        padding: '8px 0',
      }}
    >
      {NAV_ITEMS.map(({ id, label, Icon }) => (
        <button
          key={id}
          id={`bottom-nav-${id}`}
          onClick={() => setActive(id)}
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 4,
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: active === id ? '#B08F4F' : '#4a6070',
            fontSize: '0.6rem',
            fontFamily: 'Inter, sans-serif',
            padding: '4px 12px',
          }}
          aria-current={active === id ? 'page' : undefined}
        >
          <Icon />
          <span>{label}</span>
        </button>
      ))}
    </nav>
  )
}

// ── Tally strip ───────────────────────────────────────────────────────────────
function TallyStrip({ results }) {
  const counts = { critical: 0, high: 0, medium: 0, low: 0 }
  results.forEach(r => {
    const s = r.severity?.toLowerCase()
    if (s in counts) counts[s] += r.finding_count ?? 0
  })

  const items = [
    { key: 'critical', label: 'Critical', color: '#A23B2C' },
    { key: 'high',     label: 'High',     color: '#A23B2C' },
    { key: 'medium',   label: 'Medium',   color: '#B08F4F' },
    { key: 'low',      label: 'Low',      color: '#6b7f8c' },
  ]

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(4, 1fr)',
        gap: '0 24px',
        padding: '20px 32px',
        borderBottom: '1px solid #1E2C3A',
      }}
      className="sm:grid-cols-4 grid-cols-2"
    >
      {items.map(({ key, label, color }) => (
        <div key={key} style={{ minWidth: 60 }}>
          <div
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '2rem',
              fontWeight: 500,
              color,
              lineHeight: 1,
            }}
          >
            {String(counts[key]).padStart(2, '0')}
          </div>
          <div
            style={{
              fontFamily: 'Inter, sans-serif',
              fontSize: '0.62rem',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              color: '#4a6070',
              marginTop: 4,
            }}
          >
            {label}
          </div>
          <span className="tally-rule" style={{ opacity: 0.4 }} />
        </div>
      ))}
    </div>
  )
}

// ── Finding card tabs (Query / Narrative / Raw rows) ──────────────────────────
function FindingTabs({ finding, rule }) {
  const [activeTab, setActiveTab] = useState(null) // null = collapsed

  const tabs = [
    { id: 'query',     label: 'View query' },
    { id: 'narrative', label: 'Narrative'  },
    { id: 'rawrows',   label: 'Raw rows'   },
  ]

  // Build a representive SQL from the rule title (real SQL unknown client-side)
  const sqlSnippet = rule.query_hint
    ?? `-- Rule: ${rule.title}\n-- Run the audit to execute the live query against the database.\n-- Check /audits/${rule.rule_id} for the full execution result.`

  const narrative = finding?.narrative ?? rule.narrative ?? null

  // Build raw rows columns
  const rows = rule.findings ?? []
  const cols = rows.length > 0 ? Object.keys(rows[0]) : []

  return (
    <div style={{ borderTop: '1px solid #c9bf9e', marginTop: 14 }}>
      {/* Tab triggers */}
      <div style={{ display: 'flex', gap: 0 }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            id={`tab-${rule.rule_id}-${tab.id}`}
            onClick={() => setActiveTab(activeTab === tab.id ? null : tab.id)}
            aria-expanded={activeTab === tab.id}
            style={{
              padding: '7px 14px',
              fontSize: '0.75rem',
              fontFamily: 'Inter, sans-serif',
              fontWeight: 500,
              background: 'none',
              border: 'none',
              borderBottom: activeTab === tab.id ? '2px solid #B08F4F' : '2px solid transparent',
              color: activeTab === tab.id ? '#211C16' : '#6b5d42',
              cursor: 'pointer',
              transition: 'color 0.1s, border-color 0.1s',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'query' && (
        <div style={{ padding: '12px 0 4px' }}>
          <pre className="code-block">{sqlSnippet}</pre>
        </div>
      )}

      {activeTab === 'narrative' && (
        <div style={{
          padding: '14px 0 4px',
          fontFamily: 'Inter, sans-serif',
          fontSize: '0.85rem',
          lineHeight: 1.6,
          color: '#3d322a',
        }}>
          {narrative
            ? <div className="markdown-body" dangerouslySetInnerHTML={{ __html: window.marked ? window.marked.parse(narrative) : narrative }} />
            : (
              <p style={{ color: '#7a6a55', fontStyle: 'italic' }}>
                Narrative not yet available. The AI summarizer may still be processing — re-run the audit to request an updated report.
              </p>
            )
          }
        </div>
      )}

      {activeTab === 'rawrows' && (
        <div style={{ padding: '12px 0 4px', overflowX: 'auto' }}>
          {rows.length === 0 ? (
            <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.75rem', color: '#7a6a55' }}>
              No rows returned for this rule.
            </p>
          ) : (
            <table className="raw-table">
              <thead>
                <tr>{cols.map(c => <th key={c}>{c}</th>)}</tr>
              </thead>
              <tbody>
                {rows.map((row, ri) => (
                  <tr key={ri}>
                    {cols.map(c => (
                      <td key={c}>
                        {row[c] === null ? <span style={{ opacity: 0.4 }}>null</span>
                          : String(row[c])}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}

// ── Single finding card ───────────────────────────────────────────────────────
function FindingCard({ rule, index }) {
  const sev = rule.severity?.toLowerCase() ?? 'low'

  // Build a one-line summary using real data if available
  const topRow = rule.findings?.[0]
  let summary = null
  if (topRow) {
    const user = topRow.user_name ?? topRow.employee_id ?? topRow.full_name ?? topRow.username ?? null
    const detail = topRow.total_bytes != null
      ? `${(topRow.total_bytes / 1e9).toFixed(1)} GB transferred`
      : topRow.event_count != null
        ? `${topRow.event_count} events in window`
        : topRow.role_1 && topRow.role_2
          ? `${topRow.role_1} + ${topRow.role_2} conflict`
          : topRow.days_since_login != null
            ? `${topRow.days_since_login}d since last login`
            : null

    if (user && detail) summary = { user, detail }
    else if (user) summary = { user, detail: `${rule.finding_count} finding${rule.finding_count !== 1 ? 's' : ''}` }
  }

  return (
    <article
      className="stamp-land"
      style={{
        background: '#DCD3B8',
        color: '#211C16',
        borderRadius: 6,
        boxShadow: '0 2px 8px rgba(0,0,0,0.22), 0 1px 2px rgba(0,0,0,0.12)',
        padding: '18px 20px',
        position: 'relative',
        animationDelay: `${index * 60}ms`,
      }}
    >
      {/* Severity stamp — top-right corner */}
      <div className={`${severityStampClass(sev)} stamp-absolute`}>
        {severityLabel(sev)}
      </div>

      {/* Rule title */}
      <h2 style={{
        fontFamily: 'Inter, sans-serif',
        fontWeight: 600,
        fontSize: '0.95rem',
        color: '#211C16',
        paddingRight: 80, // avoid stamp overlap
        lineHeight: 1.3,
      }}>
        {rule.title}
      </h2>

      {/* One-line data summary */}
      {summary ? (
        <p style={{ marginTop: 6, fontSize: '0.83rem', display: 'flex', flexWrap: 'wrap', gap: '0 6px' }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', color: '#3d2e1a' }}>
            {summary.user}
          </span>
          <span style={{ color: '#6b5d42' }}>—</span>
          <span style={{ fontFamily: 'JetBrains Mono, monospace', color: '#3d2e1a' }}>
            {summary.detail}
          </span>
          {rule.finding_count > 1 && (
            <span style={{ color: '#7a6a55', fontFamily: 'Inter, sans-serif', fontSize: '0.78rem' }}>
              + {rule.finding_count - 1} more
            </span>
          )}
        </p>
      ) : (
        <p style={{ marginTop: 6, fontSize: '0.83rem', color: '#7a6a55', fontFamily: 'Inter, sans-serif' }}>
          <span style={{ fontFamily: 'JetBrains Mono, monospace' }}>{rule.finding_count}</span>
          {' '}finding{rule.finding_count !== 1 ? 's' : ''} identified
        </p>
      )}

      {/* Remediation note */}
      {rule.remediation && (
        <p style={{
          marginTop: 8,
          fontSize: '0.78rem',
          color: '#5a4c3c',
          fontFamily: 'Inter, sans-serif',
          lineHeight: 1.5,
          borderLeft: '2px solid #b8ad8c',
          paddingLeft: 10,
        }}>
          {rule.remediation.length > 160 ? rule.remediation.slice(0, 157) + '…' : rule.remediation}
        </p>
      )}

      {/* Tabs */}
      <FindingTabs finding={null} rule={rule} />
    </article>
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────
function EmptyState({ onRun, loading }) {
  return (
    <div style={{
      flex: 1,
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 12,
      padding: 48,
      textAlign: 'center',
    }}>
      <p style={{
        fontFamily: 'Newsreader, Georgia, serif',
        fontSize: '1.5rem',
        color: '#4a6070',
        lineHeight: 1.3,
      }}>
        No findings yet.
      </p>
      <p style={{
        fontFamily: 'Inter, sans-serif',
        fontSize: '0.88rem',
        color: '#2f4455',
        maxWidth: 320,
      }}>
        Run the audit to open this case. Findings will appear here sorted by severity.
      </p>
      <RunButton onRun={onRun} loading={loading} id="empty-run-btn" />
    </div>
  )
}

// ── Error state ───────────────────────────────────────────────────────────────
function ErrorState({ message, onRun, loading }) {
  return (
    <div style={{
      margin: '32px',
      padding: '20px 24px',
      background: '#1E2C3A',
      border: '1px solid #A23B2C',
      borderRadius: 6,
      maxWidth: 560,
    }}>
      <p style={{ fontFamily: 'Inter, sans-serif', fontWeight: 600, color: '#DCD3B8', marginBottom: 6 }}>
        Audit failed to run
      </p>
      <p style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: '0.78rem', color: '#8fa3b8', lineHeight: 1.6 }}>
        {message}
      </p>
      <p style={{ fontFamily: 'Inter, sans-serif', fontSize: '0.82rem', color: '#4a6070', marginTop: 12 }}>
        Check that the FastAPI server is running at localhost:8000, then try again.
      </p>
      <div style={{ marginTop: 16 }}>
        <RunButton onRun={onRun} loading={loading} id="error-run-btn" />
      </div>
    </div>
  )
}

// ── Run Audit button ──────────────────────────────────────────────────────────
function RunButton({ onRun, loading, id = 'run-audit-btn', label = 'Run Audit' }) {
  const btnRef = useRef(null)

  function handleClick() {
    if (loading) return
    const el = btnRef.current
    if (el) {
      el.classList.remove('btn-press')
      void el.offsetWidth // reflow
      el.classList.add('btn-press')
    }
    onRun()
  }

  return (
    <button
      ref={btnRef}
      id={id}
      onClick={handleClick}
      disabled={loading}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 8,
        padding: '9px 20px',
        background: loading ? '#7a6030' : '#B08F4F',
        color: '#211C16',
        fontFamily: 'Inter, sans-serif',
        fontSize: '0.85rem',
        fontWeight: 600,
        border: 'none',
        borderRadius: 4,
        cursor: loading ? 'not-allowed' : 'pointer',
        letterSpacing: '0.02em',
        transition: 'background 0.15s',
      }}
      onAnimationEnd={() => btnRef.current?.classList.remove('btn-press')}
    >
      {loading ? <Icons.Loader /> : null}
      {loading ? 'Running…' : label}
    </button>
  )
}

// ── Dashboard view ────────────────────────────────────────────────────────────
function Dashboard({ runId, env, results, loading, error, onRun, executedAt, health }) {
  const sorted = sortBySeverity(results)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
      {/* Top header bar */}
      <header style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '16px 32px',
        borderBottom: '1px solid #1E2C3A',
        flexWrap: 'wrap',
        gap: 12,
      }}>
        {/* Left: eyebrow + run ID */}
        <div>
          <div style={{
            fontFamily: 'Inter, sans-serif',
            fontSize: '0.65rem',
            textTransform: 'uppercase',
            letterSpacing: '0.12em',
            color: '#4a6070',
            marginBottom: 2,
          }}>
            Case File
          </div>
          <div style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '0.95rem',
            color: '#DCD3B8',
          }}>
            {runId}
          </div>
          {executedAt && (
            <div style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '0.65rem',
              color: '#2f4455',
              marginTop: 2,
            }}>
              {executedAt}
            </div>
          )}
        </div>

        {/* Center-right: environment chip + Health + Run Audit */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', gap: 8, marginRight: 8 }}>
            <div title="API Status" style={{ display: 'flex', alignItems: 'center', gap: 4, fontFamily: 'Inter, sans-serif', fontSize: '0.65rem', color: '#8fa3b8' }}>
               <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: health.api === 'ok' ? '#4CAF50' : health.api === 'error' ? '#A23B2C' : '#B08F4F' }} />
               API
            </div>
            <div title="DB Status" style={{ display: 'flex', alignItems: 'center', gap: 4, fontFamily: 'Inter, sans-serif', fontSize: '0.65rem', color: '#8fa3b8' }}>
               <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: health.db === 'ok' ? '#4CAF50' : health.db === 'error' ? '#A23B2C' : '#B08F4F' }} />
               DB
            </div>
          </div>
          <div style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '0.72rem',
            color: '#B08F4F',
            border: '1px solid #B08F4F',
            borderRadius: 3,
            padding: '3px 10px',
            letterSpacing: '0.05em',
          }}>
            {env}
          </div>
          <RunButton onRun={onRun} loading={loading} id="header-run-btn" />
        </div>
      </header>

      {/* Tally strip */}
      <TallyStrip results={results} />

      {/* Main content */}
      <main
        className="main-area"
        style={{ flex: 1, padding: '28px 32px', display: 'flex', flexDirection: 'column', gap: 16 }}
      >
        {error && <ErrorState message={error} onRun={onRun} loading={loading} />}

        {!error && results.length === 0 && !loading && (
          <EmptyState onRun={onRun} loading={loading} />
        )}

        {!error && loading && results.length === 0 && (
          <div style={{
            flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
            color: '#2f4455', fontFamily: 'JetBrains Mono, monospace', fontSize: '0.82rem',
          }}>
            Executing audit rules…
          </div>
        )}

        {sorted.map((rule, i) => (
          <FindingCard key={rule.rule_id} rule={rule} index={i} />
        ))}
      </main>
    </div>
  )
}

// ── Rules view ─────────────────────────────────────────────────────────────────
function RulesView({ results }) {
  if (results.length === 0) {
    return (
      <div style={{ padding: '48px', textAlign: 'center' }}>
        <p style={{ fontFamily: 'Newsreader, Georgia, serif', fontSize: '1.5rem', color: '#4a6070' }}>No rules loaded</p>
        <p style={{ fontFamily: 'Inter, sans-serif', fontSize: '0.88rem', color: '#2f4455', marginTop: 12 }}>Run an audit to discover configured rules.</p>
      </div>
    )
  }
  return (
    <div style={{ padding: '32px', display: 'flex', flexDirection: 'column', gap: 16 }}>
      <h1 style={{ fontFamily: 'Newsreader, Georgia, serif', fontSize: '1.5rem', color: '#DCD3B8' }}>Configured Rules</h1>
      <div style={{ overflowX: 'auto', background: '#DCD3B8', borderRadius: 6, padding: '16px' }}>
        <table className="raw-table">
          <thead>
            <tr>
              <th>Rule ID</th>
              <th>Title</th>
              <th>Severity</th>
              <th>Remediation</th>
            </tr>
          </thead>
          <tbody>
            {results.map(r => (
              <tr key={r.rule_id}>
                <td style={{ fontFamily: 'JetBrains Mono, monospace' }}>{r.rule_id}</td>
                <td style={{ fontFamily: 'Inter, sans-serif', fontWeight: 500 }}>{r.title}</td>
                <td><span className={severityStampClass(r.severity)}>{severityLabel(r.severity)}</span></td>
                <td style={{ fontSize: '0.7rem' }}>{r.remediation || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// ── Findings view ──────────────────────────────────────────────────────────────
function FindingsView({ results }) {
  const withFindings = results.filter(r => r.finding_count > 0)
  const sorted = sortBySeverity(withFindings)
  
  if (sorted.length === 0) {
    return (
      <div style={{ padding: '48px', textAlign: 'center' }}>
        <p style={{ fontFamily: 'Newsreader, Georgia, serif', fontSize: '1.5rem', color: '#4a6070' }}>No active findings</p>
        <p style={{ fontFamily: 'Inter, sans-serif', fontSize: '0.88rem', color: '#2f4455', marginTop: 12 }}>Run an audit. Findings will appear here if any rule conditions are met.</p>
      </div>
    )
  }

  return (
    <div style={{ padding: '28px 32px', display: 'flex', flexDirection: 'column', gap: 16 }}>
      <h1 style={{ fontFamily: 'Newsreader, Georgia, serif', fontSize: '1.5rem', color: '#DCD3B8', marginBottom: 8 }}>Active Findings</h1>
      {sorted.map((rule, i) => (
        <FindingCard key={rule.rule_id} rule={rule} index={i} />
      ))}
    </div>
  )
}

// ── Reports view ───────────────────────────────────────────────────────────────
function ReportsView({ runId }) {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const generateReport = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/audits/report?format=json')
      if (!res.ok) throw new Error('Failed to generate report')
      const data = await res.json()
      setReport(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: '32px', display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 800 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h1 style={{ fontFamily: 'Newsreader, Georgia, serif', fontSize: '1.5rem', color: '#DCD3B8' }}>Executive Narrative Report</h1>
        <RunButton onRun={generateReport} loading={loading} id="generate-report-btn" label="Generate Narrative" />
      </div>
      
      {error && <div style={{ color: '#A23B2C', fontFamily: 'Inter, sans-serif' }}>Error: {error}</div>}
      
      {report && (
        <div style={{ background: '#DCD3B8', padding: '24px', borderRadius: 6, color: '#211C16' }}>
          <div style={{ marginBottom: 16, fontFamily: 'JetBrains Mono, monospace', fontSize: '0.75rem', color: '#6b5d42' }}>
            Case {runId} — Generated {report.executed_at} via {report.narrative_model}
          </div>
          <div className="markdown-body" style={{ fontFamily: 'Inter, sans-serif', fontSize: '0.9rem', lineHeight: 1.6 }}>
            {report.narrative 
              ? <div dangerouslySetInnerHTML={{ __html: window.marked ? window.marked.parse(report.narrative) : report.narrative }} />
              : <p>No narrative generated. Ensure the AI provider is configured correctly.</p>
            }
          </div>
        </div>
      )}
      {!report && !loading && !error && (
        <p style={{ fontFamily: 'Inter, sans-serif', color: '#4a6070', fontSize: '0.9rem' }}>Click "Generate Narrative" above to run the checks and generate an AI-powered executive narrative.</p>
      )}
    </div>
  )
}

// ── Placeholder view for settings ──────────────────────────────────────────────
function PlaceholderView({ label }) {
  return (
    <div style={{
      flex: 1, display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center', gap: 8, minHeight: '100vh',
    }}>
      <p style={{ fontFamily: 'Newsreader, Georgia, serif', fontSize: '1.3rem', color: '#4a6070' }}>
        {label}
      </p>
      <p style={{ fontFamily: 'Inter, sans-serif', fontSize: '0.82rem', color: '#2f4455' }}>
        This section is not yet implemented.
      </p>
    </div>
  )
}

// ── Root App ──────────────────────────────────────────────────────────────────
export default function App() {
  const [activeNav, setActiveNav] = useState('dashboard')
  const [results, setResults]     = useState([])
  const [loading, setLoading]     = useState(false)
  const [error, setError]         = useState(null)
  const [executedAt, setExecutedAt] = useState(null)
  const [runId]                   = useState(makeRunId)

  const [health, setHealth]       = useState({ api: 'checking', db: 'checking' })

  // Read environment from Vite env or fallback
  const env = import.meta.env.VITE_ENV ?? 'development'

  const checkHealth = useCallback(async () => {
    try {
      const res = await fetch('/health')
      if (res.ok) {
        const data = await res.json()
        setHealth({ api: data.status === 'healthy' ? 'ok' : 'error', db: data.db_status === 'ok' ? 'ok' : 'error' })
      } else {
        setHealth({ api: 'error', db: 'error' })
      }
    } catch {
      setHealth({ api: 'error', db: 'error' })
    }
  }, [])

  useEffect(() => {
    checkHealth()
    const interval = setInterval(checkHealth, 30000)
    return () => clearInterval(interval)
  }, [checkHealth])

  const runAudit = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/audits/run')
      if (!res.ok) {
        const text = await res.text()
        throw new Error(`Server returned ${res.status}: ${text.slice(0, 200)}`)
      }
      const data = await res.json()
      setResults(data.results ?? [])
      setExecutedAt(data.executed_at ?? null)
    } catch (err) {
      // Distinguish network failure from server error
      if (err instanceof TypeError) {
        setError('Could not reach the audit server. Check that FastAPI is running on localhost:8000.')
      } else {
        setError(err.message)
      }
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [])

  // Auto-run on mount
  useEffect(() => {
    runAudit()
  }, [runAudit])

  return (
    <>
      <div style={{ display: 'flex', minHeight: '100vh' }}>
        {/* Fixed left nav rail */}
        <NavRail active={activeNav} setActive={setActiveNav} />

        {/* Main scrollable content area (offset by nav width on desktop) */}
        <div
          style={{
            marginLeft: 220,
            flex: 1,
            minHeight: '100vh',
            display: 'flex',
            flexDirection: 'column',
          }}
          className="main-area"
        >
          {activeNav === 'dashboard' && (
            <Dashboard
              runId={runId}
              env={env}
              results={results}
              loading={loading}
              error={error}
              onRun={runAudit}
              executedAt={executedAt}
              health={health}
            />
          )}
          {activeNav === 'rules'    && <RulesView results={results} />}
          {activeNav === 'findings' && <FindingsView results={results} />}
          {activeNav === 'reports'  && <ReportsView runId={runId} />}
          {activeNav === 'settings' && <PlaceholderView label="Settings" />}
        </div>

        {/* Mobile bottom nav */}
        <BottomNav active={activeNav} setActive={setActiveNav} />
      </div>
    </>
  )
}
