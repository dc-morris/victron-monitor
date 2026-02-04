# Victron Monitor

A simple, self-hosted energy monitoring dashboard for Victron systems using the VRM API.

## Features

- **Battery monitoring** - Voltage, current, power, and estimated SOC (state of charge) from voltage
- **Solar tracking** - Real-time power output and daily yield
- **Environment sensors** - Temperature and humidity from connected sensors (e.g., Ruuvi)
- **Auto-refresh** - Dashboard updates every 30 seconds
- **Data logging** - Historical data stored locally in SQLite
- **Modern UI** - Clean, responsive design with circular gauges and color-coded status

## Requirements

- Docker and Docker Compose
- Victron VRM account with API access
- A Victron device connected to VRM (e.g., GlobalLink 520, Cerbo GX)

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/dc-morris/victron-monitor.git
   cd victron-monitor
   ```

2. Create a `.env` file with your VRM credentials:
   ```bash
   cp .env.example .env
   ```

3. Edit `.env` and add your details:
   ```
   VRM_TOKEN=your_vrm_access_token
   VRM_INSTALLATION_ID=your_site_id
   ```

   **To get these values:**
   - **VRM Token**: Go to [VRM Access Tokens](https://vrm.victronenergy.com/access-tokens) and create a new token
   - **Installation ID**: Found in your VRM URL: `vrm.victronenergy.com/installation/XXXXX/dashboard`

4. Start the application:
   ```bash
   docker compose up -d
   ```

5. Open http://localhost:3000 in your browser

## Configuration

| Variable | Description |
|----------|-------------|
| `VRM_TOKEN` | Your VRM API access token |
| `VRM_INSTALLATION_ID` | Your VRM site/installation ID |

## Tech Stack

- **Backend**: Python, FastAPI, SQLAlchemy, SQLite
- **Frontend**: React, Tailwind CSS
- **Deployment**: Docker, Nginx

## Battery SOC Estimation

Since not all Victron setups include a battery monitor (BMV), SOC is estimated from voltage using a lookup table for 12V lead-acid/AGM batteries. This is approximate and works best when the battery is at rest.

## API Endpoints

- `GET /api/current` - Latest readings
- `GET /api/history?hours=24` - Historical data
- `GET /api/stats` - Today's statistics
- `POST /api/refresh` - Trigger manual data refresh
- `GET /api/health` - Health check

## License

MIT
