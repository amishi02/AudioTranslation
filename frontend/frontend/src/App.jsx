import "./App.css";

function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Real-Time Audio Translation</h1>
        <p className="app-subtitle">Phase 1 — Foundation shell (no real-time logic yet)</p>
      </header>

      <main className="app-main">
        <section aria-labelledby="lang-heading" className="panel">
          <h2 id="lang-heading">Language Selection</h2>
          <p className="placeholder">Source and target selectors will appear here (Phase 3).</p>
        </section>

        <section aria-labelledby="transcript-heading" className="panel">
          <h2 id="transcript-heading">Source Transcript</h2>
          <p className="placeholder">Live transcript will appear here (Phases 6–7).</p>
        </section>

        <section aria-labelledby="translation-heading" className="panel">
          <h2 id="translation-heading">Translation</h2>
          <p className="placeholder">Translation will appear here (Phase 8).</p>
        </section>

        <section aria-labelledby="status-heading" className="panel status-panel">
          <h2 id="status-heading">Status</h2>
          <p className="placeholder">Connection status: idle (Phase 3–4)</p>
        </section>
      </main>

      <footer className="app-footer">
        <small>
          Frontend: React + Vite (JS/JSX) · Backend: FastAPI — see AGENTS.md &amp; docs/
        </small>
      </footer>
    </div>
  );
}

export default App;
