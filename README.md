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

## 🚀 Getting Started

You can run the agency either via **Docker** (recommended) or **Locally** (direct Python/Node execution).

### Prerequisites
* **Python 3.10+**
* **Node.js 18+**
* **Docker & Docker Compose** (Optional, for Docker setup)
* Active Zerodha Account (API keys & credentials)
* Google Gemini or Anthropic API Key
* Telegram Bot Token

### ⚙️ Configuration

Before starting the services, you must configure the environment variables for each service. Sample `.env.example` files are provided in each directory.

1. **`fm-bridge/.env`**:
   ```ini
   ZERODHA_USER_ID=your_id
   ZERODHA_API_KEY=your_api_key
   ZERODHA_PASSWORD=your_password
   ZERODHA_TOTP_SECRET=your_totp_secret
   ```

2. **`fm-agents/.env`**:
   ```ini
   GOOGLE_API_KEY=your_gemini_key
   # OR ANTHROPIC_API_KEY=your_claude_key
   ```

3. **`fm-alerts/.env`**:
   ```ini
   TELEGRAM_TOKEN=your_bot_token
   TELEGRAM_CHAT_ID=your_chat_id
   ```

4. **`fm-web/.env.local`**:
   Copy from `fm-web/.env.local.example` (usually no changes needed for local development).

---

### Method 1: Docker (Recommended)

1. Ensure all `.env` files are configured as mentioned above.
2. Run Docker Compose:
   ```bash
   docker-compose up -d
   ```
3. The Next.js dashboard will be available at `http://localhost:3000`.

### Method 2: Local Installation (No Docker)

We provide handy bash scripts to set up virtual environments and run the services locally using `tmux`.

1. **Install dependencies**:
   ```bash
   chmod +x install.sh
   ./install.sh
   ```
   *(This script will create Python venvs, install `requirements.txt`, and run `npm install` for the web dashboard).*

2. **Run the services**:
   ```bash
   ./run.sh
   ```
   *If `tmux` is installed, it will neatly organize all 5 services into a single background session named `fm-trading`.*
   *If you do not have `tmux`, or run `./run.sh --plain`, it will output the exact commands to run each service in separate terminal windows.*

3. **Stop services (if using tmux)**:
   ```bash
   tmux kill-session -t fm-trading
   ```

---

## 📊 Dashboard Access
Once the services are running, open your browser and navigate to:
**http://localhost:3000**
