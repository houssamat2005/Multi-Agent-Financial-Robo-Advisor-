import React from 'react';
import { 
  LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, Legend, ResponsiveContainer, 
  BarChart, Bar, ScatterChart, Scatter, ZAxis, Cell
} from 'recharts';
import { Activity, BarChart2, Zap, BrainCircuit, Network, GitGraph } from 'lucide-react';

export default function Analytics() {
  // --- MOCK DATA ---
  const cumulativeData = [
    { date: 'Jan 23', robo: 100, spy: 100 },
    { date: 'Avr 23', robo: 108, spy: 105 },
    { date: 'Juil 23', robo: 115, spy: 111 },
    { date: 'Oct 23', robo: 112, spy: 108 },
    { date: 'Jan 24', robo: 122, spy: 116 },
    { date: 'Avr 24', robo: 130, spy: 121 },
    { date: 'Juil 24', robo: 138, spy: 127 },
    { date: 'Oct 24', robo: 135, spy: 125 },
    { date: 'Jan 25', robo: 145, spy: 132 },
  ];

  const drawdownData = [
    { date: 'Jan 23', drawdown: 0 },
    { date: 'Avr 23', drawdown: -2.1 },
    { date: 'Juil 23', drawdown: -1.5 },
    { date: 'Oct 23', drawdown: -8.4 },
    { date: 'Jan 24', drawdown: -3.2 },
    { date: 'Avr 24', drawdown: 0 },
    { date: 'Juil 24', drawdown: 0 },
    { date: 'Oct 24', drawdown: -5.1 },
    { date: 'Jan 25', drawdown: 0 },
  ];

  const markowitzData = Array.from({ length: 50 }, () => ({
    volatility: 10 + Math.random() * 15,
    return: 5 + Math.random() * 15,
  })).map(p => ({ ...p, return: p.return + (p.volatility * 0.3) })); // Make it look somewhat like a frontier
  
  const optimalPortfolio = [{ volatility: 14.5, return: 18.2, name: 'Portefeuille Optimal' }];

  const shapData = [
    { feature: 'Momentum 6M', value: 0.08, fill: '#10b981' }, // Green
    { feature: 'Volatilité Historique', value: -0.05, fill: '#ef4444' }, // Red
    { feature: 'Score Sentiment (FinBERT)', value: 0.12, fill: '#10b981' },
    { feature: 'Ratio P/E Secteur', value: -0.03, fill: '#ef4444' },
    { feature: 'Taux Directeur', value: -0.02, fill: '#ef4444' },
  ];

  const finbertData = [
    { name: 'Positif', count: 450, fill: '#10b981' },
    { name: 'Neutre', count: 320, fill: '#94a3b8' },
    { name: 'Négatif', count: 180, fill: '#ef4444' },
  ];

  const latencyData = [
    { component: 'WebSocket -> Kafka', p50: 5, p99: 15 },
    { component: 'FastAPI routing', p50: 8, p99: 25 },
    { component: 'Agent quantitatif', p50: 200, p99: 500 },
    { component: 'Agent analyste (FinBERT)', p50: 800, p99: 2000 },
    { component: 'LLaMA 3.3 / Groq', p50: 180, p99: 400 },
    { component: 'Pipeline complet', p50: 1500, p99: 3500 },
  ];

  const kafkaData = Array.from({ length: 20 }, (_, i) => ({
    time: `${i}s`,
    throughput: 40000 + Math.sin(i) * 10000 + Math.random() * 5000,
  }));

  const assets = ['AAPL', 'MSFT', 'NVDA', 'TSLA', 'SPY'];
  const correlationMatrix = [
    [1.00, 0.75, 0.65, 0.40, 0.85],
    [0.75, 1.00, 0.70, 0.35, 0.88],
    [0.65, 0.70, 1.00, 0.50, 0.78],
    [0.40, 0.35, 0.50, 1.00, 0.60],
    [0.85, 0.88, 0.78, 0.60, 1.00],
  ];

  const getColorForCorrelation = (val) => {
    if (val === 1) return 'bg-blue-600 text-white';
    if (val > 0.8) return 'bg-blue-400 text-white';
    if (val > 0.6) return 'bg-blue-300 text-gray-900';
    if (val > 0.4) return 'bg-blue-200 text-gray-900';
    return 'bg-blue-50 text-gray-900';
  };

  const Card = ({ title, icon: Icon, children, description }) => (
    <div className="bg-white p-6 rounded-xl border shadow-sm">
      <div className="flex items-center mb-2">
        <Icon className="w-5 h-5 text-indigo-600 mr-2" />
        <h3 className="text-lg font-bold text-gray-800">{title}</h3>
      </div>
      {description && <p className="text-sm text-gray-500 mb-4">{description}</p>}
      <div className="h-64 w-full mt-4">
        {children}
      </div>
    </div>
  );

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Visualisations & Analyses Avancées</h1>
          <p className="text-muted-foreground mt-1">Indicateurs quantitatifs de risque, backtesting et télémétrie du système</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Rendement Cumulé */}
        <Card title="Rendement cumulé — Robo-Advisor vs. SPY (2023-2025)" icon={BarChart2} description="Fichier: backtest_cumulative_return">
          <ResponsiveContainer>
            <LineChart data={cumulativeData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.5} />
              <XAxis dataKey="date" />
              <YAxis domain={['auto', 'auto']} />
              <RechartsTooltip />
              <Legend />
              <Line type="monotone" dataKey="robo" name="Robo-Advisor" stroke="#4f46e5" strokeWidth={3} dot={{ r: 4 }} />
              <Line type="monotone" dataKey="spy" name="Benchmark SPY" stroke="#94a3b8" strokeWidth={2} strokeDasharray="5 5" />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        {/* Drawdown */}
        <Card title="Courbe de drawdown — Robo-Advisor vs. SPY" icon={Activity} description="Fichier: backtest_drawdown">
          <ResponsiveContainer>
            <AreaChart data={drawdownData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.5} />
              <XAxis dataKey="date" />
              <YAxis />
              <RechartsTooltip />
              <Area type="monotone" dataKey="drawdown" name="Drawdown (%)" fill="#ef4444" fillOpacity={0.3} stroke="#ef4444" strokeWidth={2} />
            </AreaChart>
          </ResponsiveContainer>
        </Card>

        {/* Markowitz */}
        <Card title="Frontière efficiente de Markowitz" icon={Network} description="Fichier: markowitz_frontier">
          <ResponsiveContainer>
            <ScatterChart>
              <CartesianGrid strokeDasharray="3 3" opacity={0.5} />
              <XAxis type="number" dataKey="volatility" name="Volatilité (%)" unit="%" />
              <YAxis type="number" dataKey="return" name="Rendement Espéré (%)" unit="%" />
              <RechartsTooltip cursor={{ strokeDasharray: '3 3' }} />
              <Legend />
              <Scatter name="Portefeuilles Simulés" data={markowitzData} fill="#93c5fd" />
              <Scatter name="Portefeuille Optimal (Max Sharpe)" data={optimalPortfolio} fill="#ef4444" shape="star" />
            </ScatterChart>
          </ResponsiveContainer>
        </Card>

        {/* Matrice de Corrélation */}
        <Card title="Matrice de corrélation des actifs" icon={GitGraph} description="Fichier: correlation_matrix">
          <div className="h-full flex flex-col">
            <div className="grid grid-cols-6 gap-1 flex-1">
              <div className="flex items-end justify-center pb-2"></div>
              {assets.map(a => <div key={a} className="flex items-end justify-center font-bold text-xs pb-2 text-gray-600">{a}</div>)}
              
              {correlationMatrix.map((row, i) => (
                <React.Fragment key={i}>
                  <div className="flex items-center justify-end pr-2 font-bold text-xs text-gray-600">{assets[i]}</div>
                  {row.map((val, j) => (
                    <div key={`${i}-${j}`} className={`flex items-center justify-center rounded text-xs font-semibold ${getColorForCorrelation(val)}`}>
                      {val.toFixed(2)}
                    </div>
                  ))}
                </React.Fragment>
              ))}
            </div>
          </div>
        </Card>

        {/* SHAP Values */}
        <Card title="SHAP Waterfall Chart — Explicabilité IA" icon={BrainCircuit} description="Fichier: shap_waterfall">
          <ResponsiveContainer>
            <BarChart data={shapData} layout="vertical" margin={{ left: 100 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.5} />
              <XAxis type="number" />
              <YAxis dataKey="feature" type="category" width={100} tick={{ fontSize: 11 }} />
              <RechartsTooltip />
              <Bar dataKey="value" name="Impact (SHAP Value)">
                {shapData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* FinBERT */}
        <Card title="Distribution des scores de sentiment FinBERT" icon={BarChart2} description="Fichier: finbert_distribution">
          <ResponsiveContainer>
            <BarChart data={finbertData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.5} />
              <XAxis dataKey="name" />
              <YAxis />
              <RechartsTooltip />
              <Bar dataKey="count" name="Nombre d'articles">
                {finbertData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Latency */}
        <Card title="Latence P50/P99 par composant du pipeline" icon={Zap} description="Fichier: latency_chart">
          <ResponsiveContainer>
            <BarChart data={latencyData} margin={{ bottom: 30 }}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.5} />
              <XAxis dataKey="component" angle={-45} textAnchor="end" tick={{ fontSize: 10 }} />
              <YAxis label={{ value: 'Latence (ms)', angle: -90, position: 'insideLeft' }} />
              <RechartsTooltip />
              <Legend verticalAlign="top" />
              <Bar dataKey="p50" name="P50 (ms)" fill="#3b82f6" />
              <Bar dataKey="p99" name="P99 (ms)" fill="#f59e0b" />
            </BarChart>
          </ResponsiveContainer>
        </Card>

        {/* Kafka */}
        <Card title="Throughput Kafka sous charge simulée" icon={Activity} description="Fichier: kafka_throughput">
          <ResponsiveContainer>
            <LineChart data={kafkaData}>
              <CartesianGrid strokeDasharray="3 3" opacity={0.5} />
              <XAxis dataKey="time" />
              <YAxis domain={['auto', 'auto']} label={{ value: 'Msg/sec', angle: -90, position: 'insideLeft' }} />
              <RechartsTooltip />
              <Line type="monotone" dataKey="throughput" name="Messages/sec" stroke="#10b981" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>

        {/* LangGraph Diagram */}
        <Card title="Graphe d'états LangGraph — orchestration" icon={Network} description="Fichier: langgraph_diagram">
          <div className="h-full w-full bg-slate-50 rounded-lg flex items-center justify-center p-4">
            <div className="flex flex-col items-center space-y-4">
              {/* START Node */}
              <div className="w-24 h-10 bg-gray-800 text-white rounded-full flex items-center justify-center font-bold text-xs shadow-md z-10">START</div>
              <div className="h-6 border-l-2 border-dashed border-gray-400"></div>
              
              {/* Orchestrator Node */}
              <div className="w-48 h-12 bg-indigo-600 text-white rounded-lg flex items-center justify-center font-bold text-sm shadow-md z-10">Agent Quantitatif</div>
              <div className="h-6 border-l-2 border-dashed border-gray-400"></div>
              
              <div className="w-48 h-12 bg-blue-500 text-white rounded-lg flex items-center justify-center font-bold text-sm shadow-md z-10">Agent Analyste (FinBERT)</div>
              <div className="h-6 border-l-2 border-dashed border-gray-400"></div>

              {/* LLaMA Synthesis */}
              <div className="w-56 h-12 bg-emerald-500 text-white rounded-lg flex items-center justify-center font-bold text-sm shadow-md z-10 border-2 border-emerald-300">Synthèse Conseiller (LLaMA)</div>
              <div className="h-6 border-l-2 border-dashed border-gray-400"></div>
              
              {/* END Node */}
              <div className="w-24 h-10 bg-gray-800 text-white rounded-full flex items-center justify-center font-bold text-xs shadow-md z-10">END</div>
            </div>
          </div>
        </Card>

        {/* Neo4j Graph */}
        <Card title="Graphe Neo4j — KPI/ESG" icon={Network} description="Fichier: neo4j_graph">
          <div className="h-full w-full bg-slate-900 rounded-lg relative overflow-hidden flex items-center justify-center shadow-inner">
            {/* SVG Edges */}
            <svg className="absolute inset-0 w-full h-full pointer-events-none">
              <line x1="50%" y1="50%" x2="30%" y2="25%" stroke="#475569" strokeWidth="2" />
              <line x1="50%" y1="50%" x2="70%" y2="25%" stroke="#475569" strokeWidth="2" />
              <line x1="50%" y1="50%" x2="20%" y2="60%" stroke="#475569" strokeWidth="2" />
              <line x1="50%" y1="50%" x2="80%" y2="60%" stroke="#475569" strokeWidth="2" />
              <line x1="50%" y1="50%" x2="50%" y2="80%" stroke="#475569" strokeWidth="2" />
            </svg>

            {/* Nodes */}
            <div className="absolute top-[25%] left-[30%] -translate-x-1/2 -translate-y-1/2 w-20 h-20 bg-orange-500 rounded-full flex items-center justify-center shadow-[0_0_15px_rgba(249,115,22,0.5)] border-2 border-orange-300">
              <span className="text-white text-[10px] font-bold text-center">Secteur<br/>Tech</span>
            </div>

            <div className="absolute top-[25%] left-[70%] -translate-x-1/2 -translate-y-1/2 w-20 h-20 bg-green-500 rounded-full flex items-center justify-center shadow-[0_0_15px_rgba(34,197,94,0.5)] border-2 border-green-300">
              <span className="text-white text-[10px] font-bold text-center">Score ESG<br/>AA</span>
            </div>

            <div className="absolute top-[60%] left-[20%] -translate-x-1/2 -translate-y-1/2 w-16 h-16 bg-purple-500 rounded-full flex items-center justify-center shadow-[0_0_15px_rgba(168,85,247,0.5)] border-2 border-purple-300">
              <span className="text-white text-[10px] font-bold text-center">P/E<br/>Ratio</span>
            </div>

            <div className="absolute top-[60%] left-[80%] -translate-x-1/2 -translate-y-1/2 w-16 h-16 bg-pink-500 rounded-full flex items-center justify-center shadow-[0_0_15px_rgba(236,72,153,0.5)] border-2 border-pink-300">
              <span className="text-white text-[10px] font-bold text-center">CEO<br/>T. Cook</span>
            </div>

            <div className="absolute top-[80%] left-[50%] -translate-x-1/2 -translate-y-1/2 w-20 h-20 bg-cyan-500 rounded-full flex items-center justify-center shadow-[0_0_15px_rgba(6,182,212,0.5)] border-2 border-cyan-300">
              <span className="text-white text-[10px] font-bold text-center">Dette<br/>Faible</span>
            </div>

            {/* Central Node */}
            <div className="absolute top-[50%] left-[50%] -translate-x-1/2 -translate-y-1/2 w-24 h-24 bg-blue-600 rounded-full flex items-center justify-center shadow-[0_0_25px_rgba(37,99,235,0.8)] border-4 border-blue-300 z-10">
              <span className="text-white text-xs font-bold text-center">Company<br/>AAPL</span>
            </div>
          </div>
        </Card>

      </div>
    </div>
  );
}
