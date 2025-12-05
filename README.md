# Norwood AI

A brutal AI-powered Norwood scale classifier. Upload a photo, get roasted about your hairline.

## Tech Stack

- **Backend**: FastAPI + Celery + Redis
- **Frontend**: Vue 3 + Tailwind CSS
- **AI**: Claude (Anthropic) for vision analysis
- **Package Management**: uv (Python), npm (frontend)

## Prerequisites

- Python 3.11+
- Node.js 18+ & npm
- Docker (for Redis)
- [uv](https://github.com/astral-sh/uv) - Python package manager

### Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Install Node.js & npm

See https://nodejs.org/en/download for the latest instructions.

**Using fnm (recommended):**
```bash
curl -fsSL https://fnm.vercel.app/install | bash
fnm install 20
```

**macOS (Homebrew):**
```bash
brew install node
```

Verify with `node -v` and `npm -v`.

### Install Docker (Ubuntu)

```bash
# Add Docker's official GPG key:
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Add the repository to Apt sources:
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update

# Install Docker Engine
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Optional: run docker without sudo:
```bash
sudo usermod -aG docker $USER
newgrp docker  # or log out and back in
```

## Setup

### 1. Clone and install dependencies

```bash
git clone <repo-url>
cd norwood-ai
make install
```

### 2. Set up Redis

```bash
make setup-services
```

This pulls the Redis Docker image and creates a container. Only needed once.

### 3. Configure environment

```bash
cp backend/.env.example backend/.env
```

Edit `backend/.env` and add your Anthropic API key:

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Get an API key at https://console.anthropic.com/

## Running the App

You need **two terminals**:

### Terminal 1: Celery Worker

```bash
make run-celery
```

This starts the background worker that processes image analyses. It will automatically start Redis if it's stopped.

### Terminal 2: Web App

```bash
make run-app
```

This builds the Vue frontend and starts FastAPI. Open http://localhost:8000 in your browser.

## Development

For frontend development with hot reload:

```bash
# Terminal 1
make run-celery

# Terminal 2 - backend only
uv run --project backend uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 3 - Vue dev server with hot reload
make run-frontend
```

Then open http://localhost:5173 (Vite dev server proxies API calls).

## Make Commands

```
make help             # Show all available commands

# Setup (one-time)
make install          # Install Python and frontend dependencies
make setup-services   # Pull Redis image and create container

# Build
make build-frontend   # Build Vue frontend for production

# Run
make run-app          # Build frontend + run FastAPI (port 8000)
make run-celery       # Run Celery worker (auto-starts Redis)
make run-frontend     # Run Vue dev server (port 5173)

# Services
make ensure-redis     # Start Redis if stopped
make stop-redis       # Stop Redis container
make services-status  # Check Redis status
```

## Project Structure

```
norwood-ai/
├── Makefile
├── backend/
│   ├── pyproject.toml
│   ├── .env                 # Your config (not committed)
│   ├── .env.example
│   └── app/
│       ├── main.py          # FastAPI app
│       ├── config.py        # Settings
│       ├── schemas.py       # Pydantic models
│       ├── celery_worker.py # Celery config
│       └── tasks/
│           └── analyze.py   # Image analysis task
└── frontend/
    ├── package.json
    ├── src/
    │   └── App.vue          # Main Vue component
    └── dist/                # Built frontend (generated)
```

## API Endpoints

- `POST /analyze` - Submit image for analysis, returns task_id
- `GET /tasks/{task_id}` - Poll for analysis results
- `GET /health` - Health check

---

## TODO: Upcoming Features

### Authentication & Users
- [ ] Set up PostgreSQL database
- [ ] Create User model (google_id, email, name, created_at)
- [ ] Create Analysis model (user_id, stage, confidence, description, reasoning, roast, created_at)
- [ ] Set up Google OAuth (Google Cloud Console project, OAuth credentials)
- [ ] Implement login/logout endpoints
- [ ] Add JWT token authentication
- [ ] Protected routes for authenticated users

### Free Tier & Usage Limits
- [ ] Track analysis count per user
- [ ] Implement "1 free Norwood" limit for new users
- [ ] Show "upgrade to premium" prompt after free analysis used

### Premium ($5 one-time payment)
- [ ] Integrate Stripe for payments
- [ ] Create Payment/Subscription model
- [ ] Premium flag on user account
- [ ] Unlock unlimited analyses for premium users

### Norwood Projections (Premium Feature)
- [ ] Integrate image generation API (DALL-E, Stable Diffusion, or similar)
- [ ] Generate "future you" at Norwood stages +1, +2, +3
- [ ] Display projection gallery after analysis

### User Dashboard
- [ ] Analysis history page
- [ ] View past roasts and stages
- [ ] Track Norwood progression over time (if multiple uploads)

### Deployment
- [ ] Dockerize the full application
- [ ] Set up on droplet (nginx, SSL, etc.)
- [ ] Production Redis (or AWS ElastiCache)
- [ ] Production PostgreSQL (or AWS RDS)
- [ ] AWS S3 for image storage (optional)
- [ ] AWS Secrets Manager for API keys
