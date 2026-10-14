# 🤖 Robo-Advisor Financier Intelligent

> Système multi-agents de conseil en investissement basé sur l'IA — Projet de Fin d'Année (PFA)

[![CI](https://github.com/your-org/robo-advisor/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/robo-advisor/actions)

## Vue d'ensemble

Le Robo-Advisor automatise entièrement le cycle **Collecter → Analyser → Recommander → Rééquilibrer** en combinant :
- **Optimisation quantitative** (Markowitz, RSI, SHAP)
- **Analyse de sentiment** (FinBERT sur actualités financières)
- **Graphe de connaissances** (Neo4j : chaînes d'approvisionnement, ESG)
- **LLM** (Mistral 7B via Groq) pour des recommandations en langage naturel

## Prérequis

- Docker Desktop ≥ 4.x
- Python 3.11+
- Node.js 20+
- Git

## Démarrage rapide (< 10 minutes)

```bash
# 1. Cloner le dépôt
git clone https://github.com/your-org/robo-advisor.git
cd robo-advisor

# 2. Configurer les secrets
cp .env.example .env
# Éditer .env et renseigner : POSTGRES_PASSWORD, GROQ_API_KEY, JWT_SECRET_KEY, NEWS_API_KEY, NEO4J_PASSWORD, LANGCHAIN_API_KEY

# 3. Démarrer l'environnement complet
docker compose -f infra/docker-compose.yml up -d

# 4. Initialiser la base de données
cd backend
pip install -r requirements.txt
alembic upgrade head

# 5. Accéder à l'application
# Frontend  : http://localhost:5173
# API docs  : http://localhost:8000/docs
# Neo4j     : http://localhost:7474
# MLflow    : http://localhost:5000
```

## Structure du projet

```
robo-advisor/
├── backend/          # API FastAPI + Agents IA
├── frontend/         # Interface React.js
├── ml/               # Notebooks et expérimentations
├── infra/            # Docker Compose + Kafka config
├── docs/             # Documentation technique
└── .github/          # CI/CD GitHub Actions
```

## Stack technique

| Couche | Technologies |
|--------|-------------|
| Frontend | React.js, TailwindCSS, Recharts |
| Backend | FastAPI (Python 3.11), LangGraph, Celery |
| Bases de données | PostgreSQL, Redis, Neo4j, ChromaDB |
| IA | FinBERT, Mistral 7B (Groq), SHAP, PyPortfolioOpt |
| Ingestion | Apache Kafka, yfinance, NewsAPI |
| Infra | Docker Compose, GitHub Actions |

## Documentation

- [Guide API](docs/API.md)
- [Architecture technique](docs/ARCHITECTURE.md)
- [Guide de déploiement](docs/DEPLOYMENT.md)

## Compte de démo

```
Email    : demo@roboadvisor.ai
Password : Demo1234!
```

## Métriques de performance (backtesting 2020–2024)

| Métrique | Valeur |
|---------|--------|
| Sharpe Ratio | > 1.0 |
| Max Drawdown | < 25% |
| Latence recommandation | < 8s |

## Licence

Projet académique — PFA 2026
