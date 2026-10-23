# Hamdars

A Persian, right-to-left classroom and question-bank application.

## Local development

### API

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

The interactive API documentation is available at `http://localhost:8000/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at `http://localhost:5173`. During development, Vite proxies `/api` requests to FastAPI at `http://localhost:8000`.

## Verification

```bash
cd backend
pytest

cd ../frontend
npm run build
```

Local development stores uploaded question images on disk. Production deployments should use private S3-compatible storage or Supabase Storage.
