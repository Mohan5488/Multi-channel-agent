import React, { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

export default function ThreadList() {
  const [threads, setThreads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const { id } = useParams();

  const refresh = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8000/v1/threads/');
      const data = await res.json();
      setThreads(Array.isArray(data?.threads) ? data.threads : []);
    } catch (e) {
      console.error(e);
      setThreads([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const filtered = useMemo(() => {
    if (!query.trim()) return threads;
    const q = query.trim().toLowerCase();
    return threads.filter((t) => String(t).toLowerCase().includes(q));
  }, [threads, query]);

  const renderId = (tid) => {
    const s = String(tid);
    const short = s.slice(-6) || s;
    return `conv-${short}`;
  };

  const iconFor = (tid) => {
    const s = String(tid);
    let hash = 0;
    for (let i = 0; i < s.length; i++) {
      hash = (hash * 31 + s.charCodeAt(i)) >>> 0;
    }
    const icons = ['📩', '🤖', '💡'];
    return icons[hash % icons.length];
  };

  return (
    <div style={{ width: 240, borderRight: '1px solid #e5e7eb', background: '#f8fafc', height: '100%', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: 14, borderBottom: '1px solid #e5e7eb', display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ fontWeight: 700, color: '#0b1220', flex: 1 }}>Threads</div>
        <button onClick={refresh} title="Refresh" style={{ border: '1px solid #e5e7eb', background: '#fff', borderRadius: 6, padding: '4px 8px', cursor: 'pointer', fontSize: 12 }}>↻</button>
        <Link to="/" style={{ fontSize: 12, marginLeft: 4, textDecoration: 'none', background: '#4f46e5', color: '#fff', padding: '4px 8px', borderRadius: 6 }}>New</Link>
      </div>
      <div style={{ padding: 10, borderBottom: '1px solid #e5e7eb' }}>
        <input
          placeholder="Search threads…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid #e2e8f0', outline: 'none', fontSize: 13, background: '#fff' }}
        />
      </div>
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {loading ? (
          <div style={{ padding: 14, color: '#64748b' }}>Loading…</div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 14, color: '#64748b' }}>No threads</div>
        ) : (
          <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
            {filtered.map((tid) => {
              const isActive = id === tid;
              return (
                <li key={tid}>
                  <Link
                    to={`/${tid}`}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: 10,
                      padding: '10px 14px',
                      textDecoration: 'none',
                      color: isActive ? '#111827' : '#334155',
                      background: isActive ? '#eef2ff' : 'transparent',
                      borderLeft: isActive ? '3px solid #6366f1' : '3px solid transparent'
                    }}
                  >
                    <span style={{ fontSize: 18 }}>{iconFor(tid)}</span>
                    <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{renderId(tid)}</span>
                    {isActive ? <span style={{ marginLeft: 'auto', fontSize: 12, color: '#6366f1' }}>active</span> : null}
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}


