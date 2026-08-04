# MySQL + Qdrant + Redis

The application storage architecture is:

- MySQL: document metadata, parsed document chunks, chat history, and feedback.
- Qdrant: named dense/sparse vectors and chunk location metadata.
- Redis: QA cache, task status, and rebuild locks.
- Local files: uploaded source documents only; retrieval indexes live in MySQL/Qdrant.

## Start infrastructure

```powershell
docker compose up -d mysql qdrant redis
docker compose ps
```

MySQL listens on `127.0.0.1:3307`, Qdrant on `127.0.0.1:6333`,
and Redis on `127.0.0.1:6379`.

Copy the configuration:

```powershell
Copy-Item .env.example .env
```

Change all passwords in `.env` before using the application outside local
development.

## Install backend dependencies

Use the virtual environment Python directly; activation is optional:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-app.txt
```

## Initialize MySQL

Tables are created automatically when FastAPI starts:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

To copy records from the legacy `data/app.db` database:

```powershell
.\.venv\Scripts\python.exe scripts\migrate_sqlite_to_mysql.py
```

The migration is idempotent by primary key and does not delete the SQLite
file.

## Initialize Qdrant

Qdrant is populated by the existing rebuild-index task. Start the API and
run:

```powershell
$task = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/rebuild-index
$taskId = $task.data.task_id
Invoke-RestMethod -Uri "http://127.0.0.1:8000/task-status/$taskId"
```

The rebuild writes parsed chunks to MySQL `document_chunk`, then creates
collection `docusearch_chunks` with named `dense` and `bm25` sparse vectors.
Queries prefetch both result sets and fuse them in Qdrant with RRF.

## Verify

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

The health response includes `database`, `qdrant`, `redis`, `index`, `storage`
and `llm`.
