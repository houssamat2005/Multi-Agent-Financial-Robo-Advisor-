import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts';
import { AlertCircle, FileText, BrainCircuit, Send, Upload, X, TrendingUp, TrendingDown, DollarSign, BarChart2 } from 'lucide-react';

const COLORS = ['#6366f1', '#8b5cf6', '#a78bfa', '#c4b5fd', '#ddd6fe', '#ede9fe'];

const SUGGESTED_QUESTIONS = [
  "Analyse complète de mon portefeuille",
  "Quels actifs dois-je vendre ?",
  "Comment réduire mon risque ?",
  "Quelle est ma plus grande exposition ?",
  "Recommande un rééquilibrage",
];

export default function Dashboard() {
  const [portfolios, setPortfolios] = useState([]);
  const [activePortfolio, setActivePortfolio] = useState(null);
  const [portfolioDetails, setPortfolioDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [alerts, setAlerts] = useState([]);

  // Import modal
  const [showImportModal, setShowImportModal] = useState(false);
  const [importFile, setImportFile] = useState(null);
  const [importName, setImportName] = useState('');
  const [importing, setImporting] = useState(false);
  const [importStatus, setImportStatus] = useState(null);
  const [dragOver, setDragOver] = useState(false);

  // Chat
  const [chatMessages, setChatMessages] = useState([
    { role: 'assistant', content: 'Bonjour. Le module d\'analyse financière est initialisé. Importez un portefeuille CSV ou posez vos questions sur la gestion d\'actifs.' }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);
  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);

  useEffect(() => { fetchData(); }, []);
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [chatMessages]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [portsRes, alertsRes] = await Promise.all([
        axios.get('/api/portfolio/'),
        axios.get('/api/alerts/').catch(() => ({ data: [] }))
      ]);
      setPortfolios(portsRes.data);
      setAlerts(alertsRes.data);
      if (portsRes.data.length > 0) {
        await loadPortfolioDetails(portsRes.data[0].id);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const loadPortfolioDetails = async (id) => {
    setActivePortfolio(id);
    try {
      const res = await axios.get(`/api/portfolio/${id}`);
      setPortfolioDetails(res.data);
    } catch (err) {
      console.error(err);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith('.csv')) setImportFile(file);
  };

  const handleImport = async () => {
    if (!importFile) return setImportStatus({ type: 'error', msg: 'Veuillez sélectionner un fichier CSV.' });
    setImporting(true);
    setImportStatus({ type: 'info', msg: 'Traitement du fichier en cours...' });
    try {
      const name = importName.trim() || importFile.name.replace('.csv', '');
      const fd = new FormData();
      fd.append('file', importFile);
      fd.append('name', name);
      const res = await axios.post('/api/portfolio/import', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      setImportStatus({ type: 'success', msg: `Portefeuille "${res.data.name}" importé avec succès.` });

      const portsRes = await axios.get('/api/portfolio/');
      setPortfolios(portsRes.data);
      const newPort = portsRes.data.find(p => p.id === res.data.id) || portsRes.data[0];
      if (newPort) await loadPortfolioDetails(newPort.id);

      // Welcome message in chat
      setChatMessages([{ role: 'assistant', content: `Portefeuille "${res.data.name}" chargé avec succès (${res.data.holdings_count || 'actifs'} positions). Vous pouvez lancer une analyse ou interroger le modèle.` }]);
      setTimeout(() => { setShowImportModal(false); setImportStatus(null); setImportFile(null); setImportName(''); }, 1500);
    } catch (err) {
      const msg = err.response?.data?.detail || 'Erreur lors du traitement du fichier CSV.';
      setImportStatus({ type: 'error', msg: msg });
    } finally {
      setImporting(false);
    }
  };

  const sendMessage = async (text) => {
    const msg = text || chatInput.trim();
    if (!msg || chatLoading) return;
    setChatInput('');

    const userMsg = { role: 'user', content: msg };
    const newHistory = [...chatMessages, userMsg];
    setChatMessages(newHistory);
    setChatLoading(true);

    try {
      if (!activePortfolio) {
        setChatMessages(prev => [...prev, { role: 'assistant', content: 'Veuillez sélectionner ou importer un portefeuille pour activer l\'analyse contextuelle.' }]);
        return;
      }
      const historyToSend = chatMessages.filter(m => m.role !== 'system').slice(-10);
      const res = await axios.post(`/api/chat/${activePortfolio}`, { message: msg, history: historyToSend });
      setChatMessages(prev => [...prev, { role: 'assistant', content: res.data.reply }]);
    } catch (err) {
      setChatMessages(prev => [...prev, { role: 'assistant', content: `Erreur : ${err.response?.data?.detail || 'Service d\'analyse temporairement indisponible.'}` }]);
    } finally {
      setChatLoading(false);
    }
  };

  const pnl = (portfolioDetails?.total_market_value || 0) - (portfolioDetails?.capital || 0);
  const pnlPct = portfolioDetails?.capital > 0 ? (pnl / portfolioDetails.capital * 100) : 0;
  const chartData = portfolioDetails?.holdings?.map(h => ({ name: h.ticker, value: parseFloat(h.market_value) })) || [];

  if (loading) return (
    <div className="flex items-center justify-center h-96">
      <div className="animate-spin w-10 h-10 border-4 border-primary border-t-transparent rounded-full"></div>
    </div>
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Tableau de bord</h1>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowImportModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition text-sm font-medium"
          >
            <Upload size={16} /> Importer un portefeuille
          </button>
          <button
            onClick={async () => {
              if (!activePortfolio) return;
              try {
                const response = await axios.post('/api/reports/generate', { portfolio_id: activePortfolio }, { responseType: 'blob' });
                const url = window.URL.createObjectURL(new Blob([response.data]));
                const link = document.createElement('a');
                link.href = url;
                link.setAttribute('download', `rapport_${activePortfolio}.pdf`);
                document.body.appendChild(link);
                link.click();
                link.parentNode.removeChild(link);
              } catch { alert('Erreur PDF'); }
            }}
            className="flex items-center gap-2 px-4 py-2 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/80 transition text-sm"
          >
            <FileText size={16} /> PDF
          </button>
        </div>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <h3 className="text-red-800 font-medium flex items-center gap-2 mb-2"><AlertCircle size={18} /> {alerts.length} Alerte(s)</h3>
          {alerts.map(a => <div key={a.id} className="text-sm text-red-700">Dérive détectée — Seuil: {a.threshold * 100}%</div>)}
        </div>
      )}

      {/* Portfolio selector */}
      {portfolios.length > 1 && (
        <div className="flex gap-2 flex-wrap">
          {portfolios.map(p => (
            <button key={p.id} onClick={() => loadPortfolioDetails(p.id)}
              className={`px-3 py-1 rounded-full text-sm font-medium transition ${activePortfolio === p.id ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground hover:bg-muted/80'}`}>
              {p.name}
            </button>
          ))}
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-5 bg-card rounded-xl border border-border shadow-sm">
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1"><DollarSign size={15} /> Valeur Totale</div>
          <p className="text-3xl font-bold">${(portfolioDetails?.total_market_value || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })}</p>
        </div>
        <div className="p-5 bg-card rounded-xl border border-border shadow-sm">
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-1"><BarChart2 size={15} /> Capital Initial</div>
          <p className="text-3xl font-bold">${(portfolioDetails?.capital || 0).toLocaleString('fr-FR', { minimumFractionDigits: 2 })}</p>
        </div>
        <div className="p-5 bg-card rounded-xl border border-border shadow-sm">
          <div className={`flex items-center gap-2 text-sm mb-1 ${pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {pnl >= 0 ? <TrendingUp size={15} /> : <TrendingDown size={15} />} Plus/Moins-value
          </div>
          <p className={`text-3xl font-bold ${pnl >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {pnl >= 0 ? '+' : ''}{pnl.toLocaleString('fr-FR', { minimumFractionDigits: 2 })}$ <span className="text-lg">({pnlPct.toFixed(2)}%)</span>
          </p>
        </div>
      </div>

      {/* Main layout: Chart + Chat */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Allocation Chart */}
        <div className="p-6 bg-card rounded-xl border border-border shadow-sm">
          <h3 className="text-lg font-bold mb-4">Allocation du Portefeuille</h3>
          {chartData.length > 0 ? (
            <>
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={chartData} cx="50%" cy="50%" innerRadius={55} outerRadius={85} paddingAngle={3} dataKey="value">
                      {chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <RechartsTooltip formatter={(v) => `$${v.toLocaleString()}`} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <table className="w-full text-sm mt-4">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-2">Actif</th>
                    <th className="pb-2 text-right">Qté</th>
                    <th className="pb-2 text-right">Prix Achat</th>
                    <th className="pb-2 text-right">Valeur</th>
                    <th className="pb-2 text-right">PnL</th>
                  </tr>
                </thead>
                <tbody>
                  {portfolioDetails?.holdings?.map((h, i) => (
                    <tr key={h.id} className="border-b last:border-0">
                      <td className="py-2 font-medium flex items-center gap-2">
                        <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: COLORS[i % COLORS.length] }}></span>
                        {h.ticker}
                      </td>
                      <td className="py-2 text-right">{h.quantity}</td>
                      <td className="py-2 text-right">${h.avg_buy_price?.toFixed(2)}</td>
                      <td className="py-2 text-right">${h.market_value?.toLocaleString()}</td>
                      <td className={`py-2 text-right font-medium ${h.pnl_pct >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                        {h.pnl_pct >= 0 ? '+' : ''}{h.pnl_pct?.toFixed(2)}%
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          ) : (
            <div className="h-56 flex flex-col items-center justify-center text-muted-foreground">
              <Upload size={40} className="mb-3 opacity-30" />
              <p>Importez un fichier CSV pour visualiser votre portefeuille</p>
              <button onClick={() => setShowImportModal(true)} className="mt-3 text-primary underline text-sm">Importer maintenant</button>
            </div>
          )}
        </div>

        {/* AI Chat */}
        <div className="flex flex-col bg-card rounded-xl border border-border shadow-sm overflow-hidden" style={{ minHeight: '500px' }}>
          <div className="flex items-center gap-3 p-4 border-b border-border bg-primary/5">
            <div className="w-9 h-9 rounded-full bg-primary flex items-center justify-center text-white">
              <BrainCircuit size={18} />
            </div>
            <div>
              <h3 className="font-bold text-sm">Assistant d'Analyse</h3>
              <p className="text-xs text-muted-foreground">Conseil et synthèse de portefeuille</p>
            </div>
            <div className={`ml-auto w-2 h-2 rounded-full ${chatLoading ? 'bg-yellow-400 animate-pulse' : 'bg-green-500'}`}></div>
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-3" style={{ maxHeight: '340px' }}>
            {chatMessages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap leading-relaxed ${
                  msg.role === 'user'
                    ? 'bg-primary text-primary-foreground rounded-br-sm'
                    : 'bg-muted text-foreground rounded-bl-sm'
                }`}>
                  {msg.content}
                </div>
              </div>
            ))}
            {chatLoading && (
              <div className="flex justify-start">
                <div className="bg-muted rounded-2xl rounded-bl-sm px-4 py-3 flex gap-1.5">
                  <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                  <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                  <span className="w-2 h-2 bg-muted-foreground rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Suggested questions */}
          {chatMessages.length <= 2 && (
            <div className="px-4 pb-2 flex gap-2 flex-wrap">
              {SUGGESTED_QUESTIONS.map((q, i) => (
                <button key={i} onClick={() => sendMessage(q)}
                  className="text-xs px-3 py-1.5 rounded-full border border-primary/30 text-primary hover:bg-primary/5 transition">
                  {q}
                </button>
              ))}
            </div>
          )}

          {/* Input */}
          <div className="p-3 border-t border-border bg-background">
            <div className="flex gap-2 items-end">
              <textarea
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } }}
                placeholder="Posez une question sur votre portefeuille..."
                rows={1}
                className="flex-1 resize-none rounded-xl border border-border bg-card px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition"
                style={{ maxHeight: '100px', overflow: 'auto' }}
              />
              <button
                onClick={() => sendMessage()}
                disabled={chatLoading || !chatInput.trim()}
                className="w-9 h-9 rounded-xl bg-primary text-primary-foreground flex items-center justify-center hover:bg-primary/90 transition disabled:opacity-40"
              >
                <Send size={16} />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Import Modal */}
      {showImportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-card rounded-2xl p-6 w-full max-w-lg shadow-2xl border border-border">
            <div className="flex justify-between items-center mb-5">
              <h3 className="text-lg font-bold flex items-center gap-2"><Upload size={20} className="text-primary" /> Importer un Portefeuille</h3>
              <button onClick={() => { setShowImportModal(false); setImportFile(null); setImportStatus(null); }} className="text-muted-foreground hover:text-foreground"><X size={20} /></button>
            </div>

            {/* Drop zone */}
            <div
              onDragOver={e => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition ${dragOver ? 'border-primary bg-primary/5' : 'border-border hover:border-primary/50 hover:bg-muted/30'} ${importFile ? 'border-green-500 bg-green-50' : ''}`}
            >
              <input ref={fileInputRef} type="file" accept=".csv" className="hidden" onChange={e => setImportFile(e.target.files[0] || null)} />
              {importFile ? (
                <div className="text-primary">
                  <FileText size={36} className="mx-auto mb-2 text-primary" />
                  <p className="font-semibold text-foreground">{importFile.name}</p>
                  <p className="text-sm text-muted-foreground mt-1">{(importFile.size / 1024).toFixed(1)} KB — Fichier prêt pour l'ingestion</p>
                </div>
              ) : (
                <div className="text-muted-foreground">
                  <Upload size={36} className="mx-auto mb-3 opacity-40" />
                  <p className="font-medium">Glissez votre fichier CSV ici</p>
                  <p className="text-sm mt-1">ou cliquez pour choisir</p>
                  <p className="text-xs mt-3 font-mono bg-muted px-2 py-1 rounded inline-block">ticker, nom_actif, quantite, prix_achat_moyen, score_esg_indicatif</p>
                </div>
              )}
            </div>

            <div className="mt-4">
              <label className="block text-sm text-muted-foreground mb-1">Nom du portefeuille (optionnel)</label>
              <input value={importName} onChange={e => setImportName(e.target.value)} placeholder={importFile?.name?.replace('.csv', '') || 'Mon Portefeuille'}
                className="w-full px-3 py-2 border border-border rounded-lg text-sm bg-background focus:outline-none focus:ring-2 focus:ring-primary/30" />
            </div>

            {importStatus && (
              <div className={`mt-3 p-3 rounded-lg text-sm font-medium ${importStatus.type === 'success' ? 'bg-green-100 text-green-800' : importStatus.type === 'error' ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'}`}>
                {importStatus.msg}
              </div>
            )}

            <div className="flex gap-3 mt-5">
              <button onClick={() => { setShowImportModal(false); setImportFile(null); setImportStatus(null); }}
                className="flex-1 px-4 py-2 border border-border rounded-lg text-sm hover:bg-muted transition">Annuler</button>
              <button onClick={handleImport} disabled={importing || !importFile}
                className="flex-1 px-4 py-2 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:bg-primary/90 transition disabled:opacity-50 flex items-center justify-center gap-2">
                {importing && <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></span>}
                {importing ? 'Importation...' : 'Importer et Analyser'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
