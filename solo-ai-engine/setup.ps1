Write-Host "🚀 Setting up Solo AI Engine..." -ForegroundColor Cyan

# 1. Virtual environment setup
if (!(Test-Path "venv")) {
    Write-Host "Creating Python virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}
.\venv\Scripts\Activate.ps1

# 2. Dependency installation
Write-Host "Installing dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip
pip install -r requirements.txt

# 3. Environment configuration
if (!(Test-Path ".env")) {
    Write-Host "Generating .env from .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "⚠️ Remember to add your GROQ_API_KEY in .env" -ForegroundColor Red
}

# 4. Verify tests pass
Write-Host "Running integrity checks..." -ForegroundColor Yellow
pytest -v

Write-Host "✅ Environment configured! Start the engine with: uvicorn main:app --reload --port 8000" -ForegroundColor Green