import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';

export default function Questionnaire() {
  const [answers, setAnswers] = useState({
    q1_horizon: 3,
    q2_reaction_baisse: 3,
    q3_pct_capital: 3,
    q4_connaissance: 3,
    q5_objectif: 3
  });
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    // Check if user already has a profile
    axios.get('/api/onboarding/profile')
      .then(res => setProfile(res.data))
      .catch(() => {}); // It's ok if not found
  }, []);

  const handleChange = (q, val) => {
    setAnswers(prev => ({ ...prev, [q]: parseInt(val) }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      const res = await axios.post('/api/onboarding/questionnaire', answers);
      setProfile(res.data);
    } catch (err) {
      setError('Erreur lors de la soumission du questionnaire.');
    } finally {
      setLoading(false);
    }
  };

  if (profile) {
    return (
      <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-500">
        <div>
          <h2 className="text-2xl font-bold">Votre Profil de Risque</h2>
          <p className="text-muted-foreground">Ce profil est utilisé par l'IA pour personnaliser vos recommandations.</p>
        </div>
        
        <div className="p-6 bg-secondary/30 border border-border rounded-xl">
          <div className="grid grid-cols-2 gap-4 text-center">
            <div className="p-4 bg-card rounded-lg shadow-sm">
              <div className="text-sm text-muted-foreground uppercase tracking-wider">Type de Profil</div>
              <div className="text-3xl font-bold text-primary mt-2 capitalize">{profile.profile_type}</div>
            </div>
            <div className="p-4 bg-card rounded-lg shadow-sm">
              <div className="text-sm text-muted-foreground uppercase tracking-wider">Score Total</div>
              <div className="text-3xl font-bold mt-2">{profile.score} / 25</div>
            </div>
          </div>
          
          <div className="mt-8 text-center">
            <button 
              onClick={() => setProfile(null)}
              className="px-4 py-2 text-sm font-medium border border-border rounded-md hover:bg-muted transition-colors"
            >
              Refaire le questionnaire
            </button>
            <button 
              onClick={() => navigate('/')}
              className="ml-4 px-4 py-2 text-sm font-medium text-primary-foreground bg-primary rounded-md hover:bg-primary/90 transition-colors"
            >
              Aller au Dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Questionnaire de Profil de Risque</h2>
        <p className="text-muted-foreground">Répondez à ces 5 questions pour nous aider à déterminer votre profil d'investisseur.</p>
      </div>

      {error && <div className="p-3 text-sm text-red-500 bg-red-100 rounded">{error}</div>}

      <form onSubmit={handleSubmit} className="space-y-8">
        <Question 
          label="1. Quel est votre horizon d'investissement ?"
          value={answers.q1_horizon}
          onChange={(v) => handleChange('q1_horizon', v)}
          options={[
            { val: 1, text: "Moins de 1 an" },
            { val: 3, text: "Entre 3 et 5 ans" },
            { val: 5, text: "Plus de 10 ans" }
          ]}
        />
        <Question 
          label="2. Comment réagiriez-vous si votre portefeuille perdait 20% en un mois ?"
          value={answers.q2_reaction_baisse}
          onChange={(v) => handleChange('q2_reaction_baisse', v)}
          options={[
            { val: 1, text: "Je vends tout immédiatement" },
            { val: 3, text: "J'attends que le marché se redresse" },
            { val: 5, text: "J'achète plus pour profiter de la baisse" }
          ]}
        />
        <Question 
          label="3. Quel pourcentage de votre patrimoine total comptez-vous investir ?"
          value={answers.q3_pct_capital}
          onChange={(v) => handleChange('q3_pct_capital', v)}
          options={[
            { val: 1, text: "Moins de 10%" },
            { val: 3, text: "Entre 25% et 50%" },
            { val: 5, text: "Plus de 75%" }
          ]}
        />
        <Question 
          label="4. Quelle est votre connaissance des marchés financiers ?"
          value={answers.q4_connaissance}
          onChange={(v) => handleChange('q4_connaissance', v)}
          options={[
            { val: 1, text: "Débutant (aucune)" },
            { val: 3, text: "Intermédiaire (quelques bases)" },
            { val: 5, text: "Expert (trading actif)" }
          ]}
        />
        <Question 
          label="5. Quel est votre objectif principal ?"
          value={answers.q5_objectif}
          onChange={(v) => handleChange('q5_objectif', v)}
          options={[
            { val: 1, text: "Préserver mon capital avant tout" },
            { val: 3, text: "Croissance modérée avec risques limités" },
            { val: 5, text: "Maximiser les rendements à tout prix" }
          ]}
        />

        <div className="pt-4 border-t border-border">
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-2 font-medium text-primary-foreground bg-primary rounded-md hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            {loading ? "Calcul en cours..." : "Soumettre"}
          </button>
        </div>
      </form>
    </div>
  );
}

function Question({ label, value, onChange, options }) {
  return (
    <div className="space-y-3">
      <label className="block text-base font-medium">{label}</label>
      <div className="space-y-2">
        {options.map((opt) => (
          <label key={opt.val} className="flex items-center space-x-3 cursor-pointer p-3 border rounded-lg hover:bg-muted/50 transition-colors">
            <input
              type="radio"
              name={label}
              value={opt.val}
              checked={value === opt.val}
              onChange={(e) => onChange(e.target.value)}
              className="w-4 h-4 text-primary focus:ring-primary"
            />
            <span className="text-sm">{opt.text}</span>
          </label>
        ))}
      </div>
    </div>
  );
}
