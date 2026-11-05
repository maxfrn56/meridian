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

Sans accès aux moteurs, les réponses sont simulées et l'interface l'indique. Posez les identifiants dans un fichier `.env` à la racine (voir `.env.example`) pour passer en appels réels.

**DataForSEO** (`DATAFORSEO_LOGIN`, `DATAFORSEO_PASSWORD`) interroge les six moteurs suivis (`services/dataforseo.py`) :

| Moteur | Ce qui est mesuré |
|---|---|
| ChatGPT (`openai`) | la réponse de l'interface chatgpt.com et les sources qu'elle cite |
| Google AI Overviews | le résumé IA en tête des résultats Google, quand Google en affiche un |
| Google AI Mode | la réponse du mode IA de Google |
| Gemini | la réponse de l'interface Gemini |
| Perplexity | l'API Sonar, avec recherche web |
| Claude | l'API Claude (`CLAUDE_MODEL`), avec recherche web |

Le pays (`DATAFORSEO_COUNTRY`, France par défaut) règle la localisation ; la langue est déduite de la question. `ENGINES` limite les moteurs interrogés. Quand Google n'affiche pas de résumé IA, la réponse est marquée « Pas de réponse IA » et sort des calculs.

Sans DataForSEO, `OPENAI_API_KEY`, `PERPLEXITY_API_KEY` et `GEMINI_API_KEY` permettent des appels directs (utile en développement) ; les moteurs sans accès sont simulés. `MOCK_LLM=auto` interroge un moteur seulement s'il a un accès.

`ANTHROPIC_API_KEY` active l'analyse des réponses réelles par Claude Haiku (`ANALYSIS_MODEL`, `claude-haiku-5-5` par défaut). Sans elle, ou si l'appel échoue, l'analyse se fait par mots-clés.

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

Chaque réponse réelle est lue une fois par Claude, à la collecte (`services/llm_analysis.py`) : toutes les marques nommées, leur rang dans la réponse, leur traitement (recommandée, comparée, citée en passant, déconseillée), le ton et un extrait. Le résultat est enregistré dans la table `mentions` ; les tableaux de bord le relisent sans rappeler le modèle. Un extrait introuvable mot pour mot dans la réponse fait écarter la mention. `PROMPT_VERSION` est enregistré avec chaque analyse. Les réponses simulées et celles sans analyse passent par `services/analyzer.py` (mots-clés).

L'audit lit le HTML (BeautifulSoup), le JSON-LD, `robots.txt` et `/llms.txt`. Playwright n'est utilisé que si `USE_PLAYWRIGHT=true` (`pip install playwright && playwright install chromium`).

Le suivi s'exécute dans le process API. `services/tasks.py` prépare Celery : l'état étant en base, des workers séparés peuvent le lire s'ils pointent vers le même PostgreSQL. Redis et Postgres se lancent avec `docker compose up -d`.

## Base de données

L'API possède la base, via SQLAlchemy. Les tables sont dans `apps/api/models/tables.py`, les migrations Alembic dans `apps/api/migrations/`. L'API applique les migrations à chaque démarrage.

- **En local**, sans `DATABASE_URL`, tout va dans `apps/api/data/meridian.db` (SQLite, ignoré par Git). Supprimez ce fichier pour repartir de zéro.
- **Avec PostgreSQL**, posez `DATABASE_URL` (`postgresql://…` ou `postgres://…`, le pilote psycopg est ajouté tout seul). En local : `docker compose up -d` puis `DATABASE_URL=postgresql://geo:geo@localhost:5432/geo`. Sur Railway : ajoutez un service Postgres et référencez sa variable `DATABASE_URL`.
- `SEED_DEMO=false` en production, sinon le compte démo est créé avec son mot de passe public.

Tables : users, workspaces (la marque suivie et le forfait), competitors, queries, tracking_runs, citations, audits, prospects.

Pour faire évoluer le schéma : modifiez `tables.py`, puis générez la migration et relisez-la avant de la committer.

```bash
make migration m="ajout colonne x"
```

Sous Windows sans `make` : `cd apps/api && .venv/Scripts/alembic.exe revision --autogenerate -m "ajout colonne x"`.

Un ancien `apps/api/data/prospects.json` est repris dans la base au premier démarrage, puis renommé en `prospects.json.imported`.

## Tests

```bash
make test
```
