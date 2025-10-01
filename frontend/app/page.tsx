import AdminPanel from '@/components/AdminPanel';
import Chat from '@/components/Chat';

export default function Page() {
  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-content">
          <h1 className="app-title">🤖 AI Policy Helper</h1>
          <p className="app-subtitle">
            Local-first RAG system for customer support queries
          </p>
        </div>
      </header>
      
      <main className="main-content">
        <div className="content-grid">
          <div className="admin-section">
            <AdminPanel />
          </div>
          
          <div className="chat-section">
            <Chat />
          </div>
          
          <div className="instructions-section">
            <div className='instruction-card'>
              <h3>🚀 Quick Start</h3>
              <ol className="test-steps">
                <li>
                  Click <strong>Ingest sample docs</strong> to load the knowledge base
                </li>
                <li>
                  Try: <em>"Can a customer return a damaged blender after 20 days?"</em>
                </li>
                <li>
                  Try: <em>"What's the shipping SLA to East Malaysia for bulky items?"</em>
                </li>
              </ol>
              <div className="tip">
                💡 <strong>Tip:</strong> Click citation badges to see source documents
              </div>
            </div>
          </div>
        </div>
      </main>
      
      <footer className="app-footer">
        <p>Built with FastAPI, Next.js, and Qdrant • Local-first RAG architecture</p>
      </footer>
    </div>
  );
}
