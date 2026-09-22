# SmartGov AI

SmartGov AI is a final-year-project prototype for government scheme discovery, deterministic eligibility assistance, ML relevance ranking, multilingual search/chat, voice interaction, application assistance, RPA demo, complaints, feedback and admin operations.

## Core architecture

Citizen Profile → Deterministic Eligibility Engine → Potentially Eligible Schemes → ML Relevance Ranking → Explainable Recommendation.

The ML model ranks potentially eligible schemes. It is **not** a legal or official eligibility authority.

## Run on Windows PowerShell

**PATH: `C:\Users\Hp\Desktop\GovScheme`**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m compileall .
python -m pytest -q
python app.py
```

Open `http://127.0.0.1:5000`.

## First setup

Copy `.env.example` to `.env` and configure deployment secrets. Never commit `.env`.

Required for basic local/offline operation:

- `FLASK_SECRET_KEY`
- `DATABASE_PATH`
- `ML_MODEL_PATH`

Optional:

- Azure Speech STT/TTS
- approved official scheme JSON feed
- UiPath Orchestrator
- password-reset email delivery
- authorized DigiLocker integration

## ML model

If `ml_models/trained_model.joblib` is missing or incompatible, retrain it:

**PATH: `C:\Users\Hp\Desktop\GovScheme`**

```powershell
python ai\train_model.py
```

The training split is citizen-level to avoid leakage across the 20 scheme rows belonging to one citizen.

## Database

Database initialization is additive and idempotent. It does not reset existing users or applications.

**PATH: `C:\Users\Hp\Desktop\GovScheme`**

```powershell
python database\build_db.py
```

## Voice

Browser speech is the no-key fallback. For server-side cloud STT/TTS configure Azure:

`STT_PROVIDER=azure`

`STT_API_KEY=...`

`STT_REGION=...`

`TTS_PROVIDER=azure`

`TTS_API_KEY=...`

`TTS_REGION=...`

Live provider calls require real credentials and were not claimed as tested in the packaged build.

## Official schemes

The built-in workbook is synthetic/prototype data. Official links are stored only where configured. Live automatic discovery requires an explicitly configured HTTPS `.gov.in`/`.nic.in` machine-readable feed and admin review.

## DigiLocker

SmartGov AI provides a document-readiness layer and official DigiLocker handoff architecture. It does not collect DigiLocker credentials or scrape DigiLocker. An authorized API/consent integration must be configured for live document metadata access.

## Demo vs official application

- `DEMO-*` references are prototype RPA records and are never real government application numbers.
- Official application buttons open the configured government portal.
- CAPTCHA, OTP, biometric and other security controls are never bypassed.

## Security

Use environment variables for secrets, parameterized SQL, hashed passwords, protected admin routes, safe error pages, upload size limits, same-origin protection for state-changing browser requests, and audit logging.

## Testing

**PATH: `C:\Users\Hp\Desktop\GovScheme`**

```powershell
python -m compileall .
python -m pytest -q
```

See `docs/MASTER_PROMPT_GAP_REPORT.md` for the master-prompt implementation status and external configuration requirements.


## ML model compatibility safety net

The application loads the persisted recommendation model when it is compatible with the installed scikit-learn version. If an old joblib pipeline cannot be unpickled, the dashboard does not crash: it uses a deterministic fallback relevance scorer and exposes the condition in the admin system-health endpoint. For the intended ML path, retrain with `python ai/train_model.py` inside the project's virtual environment.
