# FM Trading Agency v5.0

FM Trading Agency is an advanced, AI-powered multi-agent trading system that integrates with Zerodha for live NSE market data and trade execution. It leverages a LangGraph-based AI pipeline for 9-layer market analysis, maintains a local trade journal, and provides real-time Telegram alerts, all accessible through a modern Next.js dashboard.

## 🏗️ Architecture & Services

The system is composed of several microservices, working together seamlessly:

1. **`fm-bridge`** (Port `8002`): Zerodha bridge for fetching NSE data, executing orders, and streaming WebSocket ticks.
2. **`fm-agents`** (Port `8003`): The AI brain using a LangGraph pipeline to perform deep 9-layer market analysis.
3. **`fm-journal`** (Port `8004`): SQLite-backed trade journal for logging trades, performance analytics, and backtesting.
4. **`fm-alerts`** (Port `8005`): Notification service for sending daily Telegram briefings and custom price alerts.
5. **`fm-quant`**: Embedded quantitative analysis package used directly by `fm-agents`.
6. **`fm-web`** (Port `3000`): A rich Next.js dashboard to interact with the entire system.

---

## ⚙️ Configuration & `.env` Files Setup

Before running the project, you **must** configure environment variables in specific directories. Create `.env` files in the following folders with their respective variables:

### 1. `fm-bridge/.env` (Required for Live Market Data & Execution)
This configures your connection to Zerodha Kite API.
```ini
# Required for API Authentication
ZERODHA_API_KEY=your_api_key_here
ZERODHA_API_SECRET=your_api_secret_here

# Optional: Auto-login Credentials
# Note: If these are provided, the system will attempt an automated login.
# If you prefer to log in manually via the browser, leave these blank or omit them.
ZERODHA_USER_ID=your_id_here
ZERODHA_PASSWORD=your_password_here
ZERODHA_TOTP_SECRET=your_totp_secret_here
```

### 2. `fm-agents/.env` (Required for AI Pipeline)
This configures the primary LLM provider used by the 9-layer AI pipeline.
```ini
GOOGLE_API_KEY=your_gemini_api_key_here
# OR
# ANTHROPIC_API_KEY=your_claude_api_key_here
```

### 3. `fm-alerts/.env` (Required for Telegram Notifications)
This configures the notification bot.
```ini
TELEGRAM_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_telegram_chat_id_here
```

### 4. `fm-journal/.env` & `fm-quant/.env` (Optional Overrides)
These usually don't require manual configuration for local runs as they rely on default database paths and logic, but if you have custom database URLs or overrides, you can place them in their respective `.env` files.

### 5. `fm-web/.env` (Required for Web Dashboard)
Next.js configuration parameters. You can usually copy this from a provided `.env.local.example` if available.
```ini
NEXT_PUBLIC_BRIDGE_URL=http://localhost:8002
NEXT_PUBLIC_AGENTS_URL=http://localhost:8003
```

---

## 📦 Dependencies & Installation

There is a single, unified `requirements.txt` file located in the root directory (`d:\fm-bridge1\requirements.txt`) which contains all the required Python packages for every backend service (fm-bridge, fm-agents, fm-alerts, fm-journal, fm-quant).

### Global Installation (Python Services)
```bash
# Create a virtual environment in the root directory
python -m venv .venv

# Activate the virtual environment
# On Windows (PowerShell):
.\.venv\Scripts\Activate
# On Mac/Linux:
source .venv/bin/activate

# Install all backend dependencies at once
pip install -r requirements.txt
```

### Global Installation (Web Dashboard)
Navigate into the `fm-web` folder and install Node packages:
```bash
cd fm-web
npm install
```

---

## 🚀 How to Run the Project Smoothly

You can run the agency either via **Docker** (recommended) or **Locally** (direct Python/Node execution).

### Method 1: Local Installation (Manual / Tmux)

We provide handy bash scripts to set up virtual environments and run the services locally using `tmux`. Alternatively, you can run them in separate terminal windows.

1. **Install dependencies using the bash script (Linux/Mac/WSL)**:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```
   *(This script will create Python venvs, install `requirements.txt`, and run `npm install` for the web dashboard).*

2. **Run the services**:
   ```bash
   ./run.sh
   ```
   *If `tmux` is installed, it will neatly organize all services into a single background session named `fm-trading`.*
   *If you do not have `tmux` (or are on Windows natively), or run `./run.sh --plain`, it will output the exact commands to run each service in separate terminal windows.*

   **Running Manually in Separate Terminals (Windows Recommended):**
   * **Terminal 1**: `cd fm-bridge && python app.py`
   * **Terminal 2**: `cd fm-agents && python app.py`
   * **Terminal 3**: `cd fm-alerts && python app.py`
   * **Terminal 4**: `cd fm-journal && python app.py`
   * **Terminal 5**: `cd fm-web && npm run dev`

### Method 2: Docker (Recommended for Deployment)

1. Ensure all `.env` files are created and populated inside their respective directories as detailed above.
2. Run Docker Compose from the root directory:
   ```bash
   docker-compose up -d
   ```
3. The Next.js dashboard will be available at `http://localhost:3000`.

---

## 📊 Dashboard Access
Once all services are running, open your browser and navigate to:
**http://localhost:3000**

Enjoy using your automated, AI-powered Trading Agency!
