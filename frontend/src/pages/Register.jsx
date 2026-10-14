import React, { useState } from 'react';
import axios from 'axios';
import { useNavigate, Link } from 'react-router-dom';

export default function Register() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    try {
      await axios.post('/api/auth/register', { email, password });
      setSuccess(true);
      setTimeout(() => navigate('/login'), 2000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Erreur lors de l\'inscription.');
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-md p-8 space-y-6 bg-card rounded-xl shadow-lg border border-border">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-foreground">Inscription</h1>
          <p className="mt-2 text-sm text-muted-foreground">Créer un nouveau compte</p>
        </div>
        
        {error && <div className="p-3 text-sm text-red-500 bg-red-100 rounded">{error}</div>}
        {success && <div className="p-3 text-sm text-green-700 bg-green-100 rounded">Inscription réussie ! Redirection...</div>}
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-foreground">Email</label>
            <input
              type="email"
              className="w-full px-3 py-2 mt-1 border rounded-md focus:ring-primary focus:border-primary bg-background text-foreground"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-foreground">Mot de passe</label>
            <input
              type="password"
              className="w-full px-3 py-2 mt-1 border rounded-md focus:ring-primary focus:border-primary bg-background text-foreground"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button
            type="submit"
            className="w-full px-4 py-2 font-medium text-primary-foreground bg-primary rounded-md hover:bg-primary/90 transition-colors"
          >
            S'inscrire
          </button>
        </form>
        
        <div className="text-sm text-center">
          Déjà un compte ? <Link to="/login" className="text-primary hover:underline">Se connecter</Link>
        </div>
      </div>
    </div>
  );
}
