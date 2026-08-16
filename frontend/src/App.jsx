import { useState, useEffect } from 'react';

function App() {
  const [industryName, setIndustryName] = useState('');
  const [currentIndustryId, setCurrentIndustryId] = useState(null);
  const [status, setStatus] = useState('');
  const [stages, setStages] = useState([]);
  const [processes, setProcesses] = useState([]);
  const [priorities, setPriorities] = useState([]);
  const [selectedProcess, setSelectedProcess] = useState(null);
  const [processDetails, setProcessDetails] = useState(null);
  const [processEvidence, setProcessEvidence] = useState([]);

  // Chat
  const [question, setQuestion] = useState('');
  const [chatLog, setChatLog] = useState([]);
  const [isAsking, setIsAsking] = useState(false);

  // Constants
  const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const analyzeIndustry = async (e) => {
    e.preventDefault();
    if (!industryName) return;
    
    // Reset state
    setStatus('Starting pipeline...');
    setStages([]);
    setProcesses([]);
    setPriorities([]);
    setSelectedProcess(null);
    setChatLog([]);
    
    try {
      const res = await fetch(`${API_BASE}/industries`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: industryName })
      });
      const data = await res.json();
      setCurrentIndustryId(data.id);
    } catch (err) {
      console.error(err);
      setStatus('Failed to connect to backend.');
    }
  };

  useEffect(() => {
    let interval;
    if (currentIndustryId) {
      interval = setInterval(async () => {
        try {
          const res = await fetch(`${API_BASE}/industries/status/${currentIndustryId}`);
          const data = await res.json();
          setStatus(data.status || '');
          
          if (data.status === 'Completed successfully.') {
            clearInterval(interval);
            fetchData(currentIndustryId);
          }
        } catch (err) {
          console.error(err);
        }
      }, 2000);
    }
    return () => clearInterval(interval);
  }, [currentIndustryId]);

  const fetchData = async (id) => {
    try {
      const [stRes, prRes, prioRes] = await Promise.all([
        fetch(`${API_BASE}/industries/${id}/stages`),
        fetch(`${API_BASE}/industries/${id}/processes`),
        fetch(`${API_BASE}/industries/${id}/priority`)
      ]);
      setStages(await stRes.json());
      setProcesses(await prRes.json());
      setPriorities(await prioRes.json());
    } catch (err) {
      console.error(err);
    }
  };

  const handleProcessClick = async (processId) => {
    setSelectedProcess(processId);
    setProcessDetails(null);
    setProcessEvidence([]);
    try {
      const [detRes, evRes] = await Promise.all([
        fetch(`${API_BASE}/processes/${processId}`),
        fetch(`${API_BASE}/processes/${processId}/evidence`)
      ]);
      setProcessDetails(await detRes.json());
      setProcessEvidence(await evRes.json());
    } catch (err) {
      console.error(err);
    }
  };

  const askQuestion = async (e) => {
    e.preventDefault();
    if (!question || !currentIndustryId) return;
    setIsAsking(true);
    const q = question;
    setQuestion('');
    
    try {
      const res = await fetch(`${API_BASE}/industries/${currentIndustryId}/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q })
      });
      const data = await res.json();
      setChatLog(prev => [...prev, { q, a: data.answer, evidenceIds: data.evidence_ids }]);
    } catch (err) {
      console.error(err);
    } finally {
      setIsAsking(false);
    }
  };

  return (
    <div className="min-h-screen p-8 max-w-7xl mx-auto space-y-8">
      <header className="flex flex-col items-center space-y-4">
        <h1 className="text-4xl font-extrabold tracking-tight text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-500">
          Value Chain AI Intelligence
        </h1>
        <p className="text-slate-400">Dynamically analyze any industry for AI opportunities.</p>
        
        <form onSubmit={analyzeIndustry} className="flex gap-4 w-full max-w-lg mt-8">
          <input 
            type="text" 
            placeholder="e.g. Retail, Healthcare, Automotive..."
            className="flex-1 px-4 py-3 rounded-lg bg-slate-800 border border-slate-700 focus:outline-none focus:ring-2 focus:ring-blue-500 text-white placeholder-slate-500"
            value={industryName}
            onChange={(e) => setIndustryName(e.target.value)}
          />
          <button type="submit" className="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors shadow-lg">
            Analyze
          </button>
        </form>
        
        {status && (
          <div className="mt-4 px-6 py-2 bg-slate-800/50 rounded-full border border-slate-700 text-sm text-blue-300 animate-pulse">
            {status}
          </div>
        )}
      </header>

      {status === 'Completed successfully.' && (
        <main className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          
          {/* Left Column: Value Chain & Interrogation */}
          <div className="space-y-8 col-span-1">
            <section className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-xl">
              <h2 className="text-xl font-bold mb-4 text-white border-b border-slate-700 pb-2">Value Chain</h2>
              <div className="space-y-4">
                {stages.map(stage => (
                  <div key={stage.id} className="space-y-2">
                    <h3 className="font-semibold text-blue-400">{stage.sequence_order}. {stage.name}</h3>
                    <ul className="pl-4 space-y-1 border-l-2 border-slate-700">
                      {processes.filter(p => p.stage_id === stage.id).map(p => (
                        <li key={p.id}>
                          <button 
                            onClick={() => handleProcessClick(p.id)}
                            className={`text-sm text-left hover:text-white transition-colors w-full p-1 rounded ${selectedProcess === p.id ? 'bg-slate-700 text-white' : 'text-slate-400 hover:bg-slate-700/50'}`}
                          >
                            {p.name}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
            </section>

            <section className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-xl flex flex-col h-96">
              <h2 className="text-xl font-bold mb-4 text-white border-b border-slate-700 pb-2">Interrogate AI</h2>
              <div className="flex-1 overflow-y-auto space-y-4 mb-4">
                {chatLog.map((log, i) => (
                  <div key={i} className="space-y-2 text-sm">
                    <div className="bg-blue-900/40 p-3 rounded-lg border border-blue-800/50 text-blue-200">
                      <span className="font-bold">Q:</span> {log.q}
                    </div>
                    <div className="bg-slate-700/40 p-3 rounded-lg border border-slate-600/50 text-slate-300">
                      <span className="font-bold">A:</span> {log.a}
                    </div>
                  </div>
                ))}
                {isAsking && <div className="text-slate-400 animate-pulse text-sm">Analyzing evidence...</div>}
              </div>
              <form onSubmit={askQuestion} className="flex gap-2">
                <input 
                  type="text" 
                  value={question}
                  onChange={e => setQuestion(e.target.value)}
                  placeholder="Ask about the evidence..."
                  className="flex-1 px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-sm text-white focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <button type="submit" className="bg-slate-700 hover:bg-slate-600 px-4 py-2 rounded-lg text-sm font-semibold transition-colors">
                  Ask
                </button>
              </form>
            </section>
          </div>

          {/* Middle/Right Column: Priority List & Detail View */}
          <div className="col-span-1 lg:col-span-2 space-y-8">
            
            <section className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-xl">
              <h2 className="text-xl font-bold mb-4 text-white border-b border-slate-700 pb-2">Top AI Opportunities (Ranked)</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {priorities.map((prio, idx) => (
                  <div key={prio.process_id} 
                    className="p-4 rounded-lg bg-slate-900/50 border border-slate-700 hover:border-blue-500/50 transition-colors cursor-pointer"
                    onClick={() => handleProcessClick(prio.process_id)}
                  >
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-semibold text-lg text-white">#{prio.rank} {prio.process_name}</h3>
                      <span className="bg-blue-500/20 text-blue-300 text-xs px-2 py-1 rounded-full font-mono border border-blue-500/30">
                        Score: {prio.final_priority_score.toFixed(2)}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">Stage: {prio.stage_name}</p>
                  </div>
                ))}
              </div>
            </section>

            {selectedProcess && processDetails ? (
              <section className="bg-slate-800 rounded-xl p-6 border border-slate-700 shadow-xl animate-in fade-in slide-in-from-bottom-4 duration-300">
                <div className="flex justify-between items-start mb-6">
                  <div>
                    <h2 className="text-2xl font-bold text-white mb-1">{processDetails.name}</h2>
                    <p className="text-slate-400 text-sm">{processDetails.business_purpose}</p>
                  </div>
                  {processDetails.priority_score && (
                    <div className="text-right bg-slate-900 p-3 rounded-lg border border-slate-700">
                      <div className="text-xs text-slate-400 uppercase tracking-wider mb-1">Priority Score</div>
                      <div className="text-2xl font-mono text-purple-400 font-bold">{processDetails.priority_score.final_priority_score.toFixed(2)}</div>
                      <div className="text-[10px] text-slate-500 mt-1 space-y-1 text-left">
                        <div>Impact: {processDetails.priority_score.business_impact_score}</div>
                        <div>Feasibility: {processDetails.priority_score.feasibility_score}</div>
                        <div>Risk: {processDetails.priority_score.risk_score}</div>
                      </div>
                    </div>
                  )}
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Business Challenge</h4>
                    <p className="text-slate-400 text-sm bg-slate-900/50 p-4 rounded-lg border border-slate-800/50">{processDetails.finding?.current_challenges}</p>
                  </div>
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold text-purple-300 uppercase tracking-wider">AI Opportunity</h4>
                    <p className="text-purple-200/80 text-sm bg-purple-900/10 p-4 rounded-lg border border-purple-500/20">{processDetails.finding?.ai_opportunity}</p>
                  </div>
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold text-emerald-300 uppercase tracking-wider">Potential Benefit</h4>
                    <p className="text-emerald-200/80 text-sm bg-emerald-900/10 p-4 rounded-lg border border-emerald-500/20">{processDetails.finding?.potential_benefit}</p>
                  </div>
                  <div className="space-y-2">
                    <h4 className="text-sm font-semibold text-rose-300 uppercase tracking-wider">Key Risks</h4>
                    <p className="text-rose-200/80 text-sm bg-rose-900/10 p-4 rounded-lg border border-rose-500/20">{processDetails.finding?.risk}</p>
                  </div>
                </div>

                <div className="space-y-4">
                  <h4 className="text-sm font-semibold text-slate-300 uppercase tracking-wider border-b border-slate-700 pb-2">Supporting Evidence ({processEvidence.length})</h4>
                  <div className="space-y-3 max-h-64 overflow-y-auto pr-2">
                    {processEvidence.map((ev) => (
                      <div key={ev.id} className="bg-slate-900 p-4 rounded-lg border border-slate-700 text-sm space-y-2">
                        <a href={ev.source_url} target="_blank" rel="noreferrer" className="text-blue-400 hover:text-blue-300 font-semibold flex items-center gap-1">
                          {ev.source_title}
                          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" /></svg>
                        </a>
                        <p className="text-slate-400 text-xs font-serif italic border-l-2 border-slate-600 pl-3">"{ev.extracted_snippet}"</p>
                      </div>
                    ))}
                    {processEvidence.length === 0 && <p className="text-slate-500 text-sm">No specific evidence linked.</p>}
                  </div>
                </div>
              </section>
            ) : selectedProcess ? (
              <div className="h-96 flex items-center justify-center border border-slate-700 rounded-xl bg-slate-800/50 border-dashed">
                <div className="text-slate-500 animate-pulse">Loading process details...</div>
              </div>
            ) : null}
            
          </div>
        </main>
      )}
    </div>
  );
}

export default App;
