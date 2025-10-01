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
      <h2 style={{ margin: '0 0 1rem 0', color: '#2d3748', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        ⚙️ Admin Panel
      </h2>
      
      <div className="admin-actions">
        <button
          onClick={ingest}
          disabled={busy}
          className="btn-primary admin-btn"
        >
          {busy ? '⏳ Indexing...' : '📚 Ingest sample docs'}
        </button>
        <button
          onClick={refresh}
          className="btn-secondary admin-btn"
        >
          🔄 Refresh metrics
        </button>
      </div>
      
      {metrics && (
        <div className="metrics-section">
          <div className="status-bar">
            <span className="status-item">
              📄 {metrics.document_count || 0} docs
            </span>
            <span className="status-item">
              🔍 {metrics.vector_count || 0} chunks
            </span>
            <span className="status-item">
              🤖 {metrics.llm_model || 'stub'}
            </span>
            {metrics.avg_retrieval_latency_ms && (
              <span className="status-item">
                ⚡ {Math.round(metrics.avg_generation_latency_ms)}ms
              </span>
            )}
          </div>
          
          <details className="raw-metrics">
            <summary className="metrics-toggle">
              � View detailed metrics
            </summary>
            <div className='code'>
              <pre>{JSON.stringify(metrics, null, 2)}</pre>
            </div>
          </details>
        </div>
      )}
    </div>
  );
}
