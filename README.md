# Robo-Advisor Multi-Agents : Système d'Aide à la Décision Financière

Projet de Fin d'Année (PFA) portant sur la conception et l'implémentation d'une plateforme distribuée d'optimisation de portefeuille d'actifs financiers, combinant calcul quantitatif, analyse de sentiment et raisonnement multi-agents.

---

## 1. Présentation du projet

La gestion moderne de portefeuille requiert la synthèse simultanée de données quantitatives (historiques de cours, volatilité, corrélations) et qualitatives (actualités financières, sentiment de marché, critères ESG). 

Ce projet implémente une architecture multi-agents orchestrée avec **LangGraph**, permettant d'automatiser le cycle d'analyse et de rééquilibrage de portefeuille :

1. **Agent Quantitatif** : Calcul de la frontière efficiente selon la théorie moderne de portefeuille de Markowitz, maximisation du ratio de Sharpe, calcul des indicateurs techniques (RSI) et explicabilité via valeurs SHAP.
2. **Agent Analyste** : Ingestion de flux d'actualités financières, scoring de polarité via le modèle NLP **FinBERT**, extraction de relations sectorielles et critères ESG depuis une base graphe **Neo4j**.
3. **Agent Conseiller (LLM)** : Synthèse des signaux quantitatifs et qualitatifs, génération de recommandations argumentées et dialogue interactif avec l'investisseur.

---

## 2. Architecture technique

Le système repose sur des services conteneurisés communicant de manière asynchrone :

* **Frontend** : Application React (Vite, TailwindCSS, Recharts) offrant un tableau de bord de suivi de portefeuille, un assistant interactif et un module de visualisations analytiques.
* **Backend API** : Service FastAPI (Python 3.11) exposant les endpoints REST, gérant l'authentification JWT et l'orchestration des agents.
* **Pipeline de données** :
  * **Apache Kafka & Zookeeper** : Ingestion en streaming des flux de cotations et dépêches d'actualités.
  * **Celery & Redis** : Planification des tâches périodiques de rebalancement et mise en cache temps réel des prix.
  * **PostgreSQL** : Persistance transactionnelle (comptes utilisateurs, portefeuilles, historique des transactions et recommandations).
  * **Neo4j** : Modélisation des relations inter-entreprises, dépendances de chaînes d'approvisionnement et données ESG.
  * **ChromaDB** : Base vectorielle pour l'indexation sémantique et la recherche documentaire (RAG).

---

## 3. Structure du projet

```
├── backend/
│   ├── app/
│   │   ├── agents/          # Définition et orchestration des agents (LangGraph)
│   │   ├── api/             # Routes FastAPI (auth, portfolio, chat, analytics)
│   │   ├── core/            # Configuration et sécurité JWT
│   │   ├── db/              # Connecteurs Postgres, Redis, Neo4j, Chroma
│   │   ├── ingestion/       # Consommateurs Kafka et flux de prix
│   │   ├── models/          # Modèles SQLAlchemy (User, Portfolio, Holding)
│   │   └── services/        # Moteurs Markowitz, FinBERT, SHAP et génération PDF
│   ├── tasks/               # Tâches asynchrones Celery
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/      # Composants structurels et navigation
│   │   ├── contexts/        # Contexte d'authentification React
│   │   └── pages/           # Dashboard, Analytics, Profil de risque, Login
│   ├── Dockerfile
│   └── package.json
├── infra/                   # Configuration Kafka et scripts d'initialisation
├── portefeuille/            # Données de test (fichiers CSV de démonstration)
└── docker-compose.yml       # Déploiement multi-conteneurs
```

---

## 4. Installation et démarrage

### Prérequis
* Docker et Docker Compose
* Git

### Déploiement local

1. **Cloner le projet**
   ```bash
   git clone https://github.com/houssamat2005/Multi-Agent-Financial-Robo-Advisor-.git
   cd Multi-Agent-Financial-Robo-Advisor-
   ```

2. **Configuration de l'environnement**
   Copiez le fichier de variables d'environnement modèle :
   ```bash
   cp .env.example backend/.env
   ```
   Renseignez votre clé d'API de modèle de langage (`GROQ_API_KEY`) dans `backend/.env`.

3. **Lancement des conteneurs**
   ```bash
   docker-compose up -d --build
   ```

4. **Accès aux services**
   * Interface utilisateur : [http://localhost:3000](http://localhost:3000)
   * Documentation OpenAPI (Swagger) : [http://localhost:8000/docs](http://localhost:8000/docs)
   * Console Neo4j : [http://localhost:7474](http://localhost:7474)

---

## 5. Fonctionnalités principales

* **Importation de portefeuille** : Support du format CSV (`ticker`, `quantite`, `prix_achat_moyen`). Un fichier d'exemple est disponible dans `portefeuille/portefeuille_exemple.csv`.
* **Tableau de bord dynamique** : Calcul automatique de la valeur liquidative, plus/moins-values latentes et répartition d'actifs.
* **Assistant conversationnel spécialisé** : Dialogue en langage naturel contextualisé par les actifs détenus et les données de marché en direct.
* **Rapports et visualisations** : Page dédiée regroupant frontière efficiente de Markowitz, courbes de drawdown, matrices de corrélation et explicabilité des décisions.
