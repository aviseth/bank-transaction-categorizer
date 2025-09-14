# Bank Transaction Categorizer

AI-powered bank transaction categorization system that automatically identifies transaction types and vendors.

## Quick Setup

1. **Install dependencies**:

   ```bash
   poetry install
   ```

2. **Set up API key**:

   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

3. **Start the application**:

   ```bash
   # Easy one-command startup
   python start.py

   # Or manually start just the web interface
   poetry run streamlit run app.py
   ```

4. **Open your browser** to `http://localhost:8501`

## How to Use

### Upload and Process Transactions

1. Go to **Process Transactions** page
2. Upload a CSV file or select sample data
3. Click **Process** to categorize transactions
4. View results in real-time

### Review Results

- **Vendor Payments**: View all vendor transactions and matching details
- **Analytics**: See spending patterns and charts
- **Vendors**: Browse identified vendors and their information
- **Database**: View all transactions by category

## UI Pages

- **Process Transactions**: Upload CSV files and run processing
- **Analytics**: Charts and spending analysis
- **Vendor Payments**: Review vendor transactions with matching source
- **Vendors**: Browse all identified vendors
- **Database**: View transaction categories and data management

## Background Processing (Optional)

For large files, enable background processing:

1. **Start services**:

   ```bash
   # Install Redis (macOS)
   brew install redis
   brew services start redis

   # Start Celery worker (separate terminal)
   poetry run celery -A src.celery_app worker --loglevel=info
   ```

2. **Use "Process in Background"** button in the UI
3. **Monitor progress** while using other pages

## Managing Services

### Shut Down All Services

To stop all running services (Celery workers, Streamlit app, Redis):

```bash
# Kill all Celery worker processes
pkill -f "celery.*worker"

# Kill Streamlit app
pkill -f "streamlit.*app.py"

# Stop Redis service
brew services stop redis
# OR if Redis was started manually:
redis-cli SHUTDOWN
```

### Clear All Cache and Data

To clear all Redis cache, Celery queues, and start fresh:

```bash
# Start Redis (if not running)
redis-server --daemonize yes

# Clear all Redis data
redis-cli FLUSHALL
redis-cli FLUSHDB

# Purge all Celery tasks
poetry run celery -A src.celery_app purge -f

# Stop Redis
redis-cli SHUTDOWN
```

### View Background Processing Logs

To see real-time logs from background processing:

```bash
# Option 1: Run Celery worker manually (shows logs in terminal)
poetry run celery -A src.celery_app worker --loglevel=info

# Option 2: Monitor task events
poetry run celery -A src.celery_app events --dump

# Option 3: Check active tasks
poetry run celery -A src.celery_app inspect active
```

## Features

- **Smart Categorization**: vendor_payment, salary_payment, customer_payment_received, etc.
- **Vendor Identification**: Automatically extracts and matches vendors
- **Confidence Scores**: Shows AI confidence for all decisions
- **MECE Categories**: Mutually exclusive, collectively exhaustive categories
- **Duplicate Detection**: Prevents processing duplicate transactions
- **Interactive UI**: Real-time progress and filtering

## Requirements

- Python 3.10+
- OpenAI API key
- Poetry
- Redis (optional, for background processing)

## Sample Data

Includes sample Danish bank CSV data for testing. The system processes these fields:

- Date, Amount, Currency, Transaction text, Vendor info, etc.

## Architecture

- **Database**: SQLite with transaction and vendor tables
- **AI**: OpenAI GPT for categorization and vendor enrichment
- **UI**: Streamlit web interface
- **Background**: Celery + Redis for async processing
