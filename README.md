# Meridian

MVP de plateforme GEO (Generative Engine Optimization). Une entreprise suit sa visibilité dans les réponses d'OpenAI, Perplexity et Gemini, audite son site, et reçoit des actions classées par priorité.

## Lancer le projet

Deux process, depuis la racine :

```bash
make install
make api
make web
```

L'interface est sur [http://localhost:3000](http://localhost:3000). Compte de démonstration : `demo@geo.dev` / `meridian`.

Sans clé d'API, les réponses des moteurs sont simulées et l'interface l'indique. Posez les clés dans un fichier `.env` à la racine (voir `.env.example`) pour passer en appels réels :

- `OPENAI_API_KEY` — GPT-4o avec recherche web
- `PERPLEXITY_API_KEY` — modèle Sonar
- `GEMINI_API_KEY` — Gemini avec Google Search

`MOCK_LLM=auto` interroge un moteur seulement si sa clé est présente.

## Architecture

```
apps/web     Next.js (App Router), React Query, shadcn/ui, Recharts
apps/api     FastAPI
  routers/   contrats HTTP
  services/  tracker, analyzer, auditor, recommender
  models/    schémas Pydantic
```

Le frontend parle à `/api/geo/*`, qui proxifie `http://127.0.0.1:8000/api/v1`.

Les prompts de suivi sont envoyés tels quels : la marque n'est pas injectée dans la question. Le taux de citation compte une réponse si la marque est nommée ou si son domaine figure dans les sources. La part de voix rapporte les mentions de la marque à l'ensemble des marques suivies.

L'audit lit le HTML (BeautifulSoup), le JSON-LD, `robots.txt` et `/llms.txt`. Playwright n'est utilisé que si `USE_PLAYWRIGHT=true` (`pip install playwright && playwright install chromium`).

Le suivi s'exécute dans le process API. `services/tasks.py` prépare Celery pour le jour où PostgreSQL est partagé entre l'API et les workers. Redis et Postgres se lancent avec `docker compose up -d`.

## Base de données

Le schéma Prisma est dans `apps/web/prisma/schema.prisma`, l'URL Postgres dans `apps/web/prisma.config.ts`. Tables : users, workspaces, brands, competitors, queries, tracking runs, citations, mentions, audits. L'API du MVP garde l'état en mémoire pour démarrer sans base : les contrats sont les mêmes que le schéma.

```bash
docker compose up -d
cd apps/web && npx prisma db push
```

## Tests

```bash
make test
```
