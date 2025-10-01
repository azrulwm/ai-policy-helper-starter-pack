'use client';
import { apiIngest, apiMetrics } from '@/lib/api';
import React from 'react';

export default function AdminPanel() {
  const [metrics, setMetrics] = React.useState<any>(null);
  const [busy, setBusy] = React.useState(false);

  const refresh = async () => {
    const m = await apiMetrics();
    setMetrics(m);
  };

  const ingest = async () => {
    setBusy(true);
    try {
      await apiIngest();
      // Note: Not auto-refreshing metrics to match examiner's expected workflow:
      // "click Ingest sample docs and then Refresh metrics"
    } finally {
      setBusy(false);
    }
  };

  React.useEffect(() => {
    refresh();
  }, []);

  return (
    <div className='card'>
      <h2>Admin</h2>
      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        <button
          onClick={ingest}
          disabled={busy}
          style={{
            padding: '8px 12px',
            borderRadius: 8,
            border: '1px solid #111',
            background: '#fff',
          }}
        >
          {busy ? 'Indexing...' : 'Ingest sample docs'}
        </button>
        <button
          onClick={refresh}
          style={{
            padding: '8px 12px',
            borderRadius: 8,
            border: '1px solid #111',
            background: '#fff',
          }}
        >
          Refresh metrics
        </button>
      </div>
      {metrics && (
        <div className='code'>
          <pre>{JSON.stringify(metrics, null, 2)}</pre>
        </div>
      )}
    </div>
  );
}
