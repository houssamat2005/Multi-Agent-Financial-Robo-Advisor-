import React from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { LayoutDashboard, LogOut, FileText, Activity, BarChart2 } from 'lucide-react';

export default function Layout() {
  const { user, logout } = useAuth();
  const location = useLocation();

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <header className="bg-card border-b border-border">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center">
              <Activity className="h-8 w-8 text-primary" />
              <span className="ml-2 text-xl font-bold text-foreground">Robo-Advisor AI</span>
            </div>
            
            <div className="flex items-center space-x-4">
              <span className="text-sm text-muted-foreground">{user?.email}</span>
              <button 
                onClick={logout}
                className="p-2 rounded-full hover:bg-muted text-muted-foreground transition-colors"
                title="Déconnexion"
              >
                <LogOut size={20} />
              </button>
            </div>
          </div>
        </div>
      </header>
      
      <div className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 flex gap-8">
        {/* Sidebar Nav */}
        <aside className="w-64 flex-shrink-0">
          <nav className="space-y-1">
            <Link 
              to="/" 
              className={`flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
                location.pathname === '/' 
                  ? 'bg-primary/10 text-primary' 
                  : 'text-foreground hover:bg-muted'
              }`}
            >
              <LayoutDashboard className="mr-3 h-5 w-5" />
              Tableau de bord
            </Link>
            <Link 
              to="/questionnaire" 
              className={`flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
                location.pathname === '/questionnaire' 
                  ? 'bg-primary/10 text-primary' 
                  : 'text-foreground hover:bg-muted'
              }`}
            >
              <FileText className="mr-3 h-5 w-5" />
              Profil de Risque
            </Link>
            <Link 
              to="/analytics" 
              className={`flex items-center px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
                location.pathname === '/analytics' 
                  ? 'bg-primary/10 text-primary' 
                  : 'text-foreground hover:bg-muted'
              }`}
            >
              <BarChart2 className="mr-3 h-5 w-5" />
              Visualisations & Rapport
            </Link>
          </nav>
        </aside>
        
        {/* Main Content */}
        <main className="flex-1 bg-card rounded-xl border border-border shadow-sm p-6 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
