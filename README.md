# Campus Care — College Help Desk API

A small, deployable teaching project for learning client/server communication, HTTP methods, path and query parameters, JSON request bodies, headers, JWT authentication, API keys, CRUD, and relational databases.

## Stack
- Frontend: HTML, CSS, vanilla JavaScript (served by FastAPI)
- Backend: Python + FastAPI
- Database: PostgreSQL on Render; SQLite automatically used for local development
- Deployment: Render

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open:
- Website: http://127.0.0.1:8000
- API documentation: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/health

Create a student account in the website. No pre-created student password is included.

## Deploy to Render

### Option A: Blueprint (recommended)
1. Push this folder to a GitHub repository.
2. In Render, choose **New → Blueprint**.
3. Connect the repository and select `render.yaml`.
4. Review the web service and PostgreSQL database, then apply.
5. Wait for the deployment to finish.
6. Open the generated `https://...onrender.com` URL.
7. Open `/docs` to inspect and test the API.

The Blueprint creates a PostgreSQL database and generates `SECRET_KEY` and `INTEGRATION_API_KEY` values. The integration key is stored as a server environment variable; do not commit secrets to GitHub.

**Plan note:** the included database plan is a paid Render database plan. If you want a no-cost temporary classroom trial, change the database plan to a currently available free option in Render if your account offers one, or use an external PostgreSQL provider. Free database availability and expiry rules can change. Do not use ephemeral local SQLite on a hosted service for student records.

### Environment variables
- `DATABASE_URL`: PostgreSQL connection string (Render Blueprint sets it)
- `SECRET_KEY`: long random secret used to sign JWT tokens
- `INTEGRATION_API_KEY`: secret API key for the integration endpoint

## Main endpoints

| Method | Endpoint | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | No | Health check |
| GET | `/api/announcements` | No | Public data |
| POST | `/api/auth/signup` | No | Create account; JSON body |
| POST | `/api/auth/login` | No | Login; returns JWT |
| GET | `/api/me` | Bearer JWT | Current user |
| GET | `/api/tickets` | Bearer JWT | List own tickets; query `status`, `limit` |
| POST | `/api/tickets` | Bearer JWT | Create ticket; JSON body |
| GET | `/api/tickets/{ticket_id}` | Bearer JWT | Path parameter |
| PUT | `/api/tickets/{ticket_id}` | Bearer JWT | Replace ticket fields |
| PATCH | `/api/tickets/{ticket_id}/status` | Bearer JWT | Update status only |
| DELETE | `/api/tickets/{ticket_id}` | Bearer JWT | Delete own ticket |
| GET | `/api/integration/tickets` | X-API-Key | Server-to-server integration demo |

## Teaching examples

### Path parameter
`GET /api/tickets/12` — `12` identifies a specific ticket.

### Query parameter
`GET /api/tickets?status=open&limit=5` — filters and limits the result.

### JSON body
`POST /api/tickets`
```json
{
  "issue": "Wi-Fi not working",
  "description": "Cannot connect in Lab 2",
  "location": "Lab 2"
}
```

### JWT authentication
After login, send:
`Authorization: Bearer <access_token>`

### API key
Send:
`X-API-Key: <INTEGRATION_API_KEY>`

For teaching, the API Playground accepts custom headers. Share the demo key with students only through a controlled channel. Never embed a real API key in browser JavaScript for production use; browser code and requests are visible to users. The API-key endpoint is intended to demonstrate server-to-server authentication.

## Security and production notes
- Passwords are hashed; plaintext passwords are never stored.
- Each student can only read, update, or delete their own tickets.
- JWT expiration is 12 hours.
- Change secrets through Render environment variables.
- Add rate limiting, email verification, audit logs, backups, and admin roles before using this as a real college support system.
- The default local secrets are for local development only.
