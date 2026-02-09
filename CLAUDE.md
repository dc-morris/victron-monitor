# Victron Monitor - Project Notes

## Project Structure

- `backend/` - Python FastAPI backend
- `frontend/` - React + Vite + Tailwind frontend

## Commands

### Backend
```bash
cd backend
pytest test_main.py -v      # Run tests
uvicorn main:app --reload   # Dev server (port 8000)
```

### Frontend
```bash
cd frontend
npm run dev        # Dev server (port 5173)
npm run test:run   # Run tests
npm run build      # Production build
```

### Fly.io (auto-deploys on push to main)
```bash
fly status -a victron-monitor-api  # Check backend status
fly status -a victron-monitor      # Check frontend status
fly logs -a victron-monitor-api    # View backend logs
```

## VRM API

Diagnostic codes used:
- `bv` - Battery voltage
- `bc` - Battery current
- `bp` - Battery power
- `bst` - Battery state (0=idle, 1=charging, 2=discharging)
- `PVP` - Solar/PV power
- `ScV` - Solar voltage
- `ScI` - Solar current
- `YT` - Yield today (kWh)
- `tsT` - Temperature sensor
- `tsH` - Humidity sensor

## Key Files

- `backend/vrm_client.py` - VRM API integration and data parsing
- `backend/models.py` - SQLAlchemy database models
- `frontend/src/App.jsx` - Main dashboard component
- `frontend/src/utils.js` - Utility functions (voltageToSOC, getStateLabel, etc.)

## Workflow

- Run all tests before any commit
- Every commit should reference a GitHub Issue
- Create an issue first if one doesn't exist
- Reference in commit messages (e.g., "Fix battery display #12")

## Deployment

- **Fly.io**: Auto-deploys on push to main via CI/CD
  - Frontend: https://victron-monitor.fly.dev/
  - Backend API: https://victron-monitor-api.fly.dev/
  - Backend uses persistent volume for SQLite database

## Notes

- Battery SOC is estimated from voltage using a lookup table for 12V lead-acid/AGM
- Data is polled from VRM every minute and stored in SQLite
- Frontend refreshes every 30 seconds
