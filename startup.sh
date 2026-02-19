#!/bin/bash
set -e

# ------------------------------
# Paths and Environment
# ------------------------------
LOG_FILE="/www/source/startup.log"
BACKEND_DIR="/www/source/cot-back"
VENV_PATH="$BACKEND_DIR/.venv/bin/activate"
NEXTJS_DIR="/www/source/FrantzdyTradingCo"
VENV_ACTIVATE="source \"$VENV_PATH\""

# Redirect all output to the log file (append, not overwrite)
exec >> "$LOG_FILE" 2>&1
echo "----- Startup $(date) -----"

# ------------------------------
# Helper function: start screen session if not already running
# ------------------------------
start_screen_session() {
    SESSION_NAME="$1"
    COMMAND="$2"
    CD_PATH="$3"
    LOG_PATH="/www/source/${SESSION_NAME}.log"

    if ! screen -ls | grep -q "$SESSION_NAME"; then
        echo "Starting $SESSION_NAME..."
        screen -dmS "$SESSION_NAME" bash -c "cd \"$CD_PATH\" && $COMMAND 2>&1 | tee -a \"$LOG_PATH\""
        sleep 1
        if ! screen -ls | grep -q "$SESSION_NAME"; then
            echo "⚠️ Failed to start $SESSION_NAME (check $LOG_PATH)"
        else
            echo "✅ $SESSION_NAME started"
        fi
    else
        echo "$SESSION_NAME is already running."
    fi
}

# ------------------------------
# Activate Virtual Environment
# ------------------------------
cd "$BACKEND_DIR" || { echo "❌ Failed to cd to $BACKEND_DIR"; exit 1; }
if [ -f "$VENV_PATH" ]; then
    source "$VENV_PATH"
    echo "✅ Virtual environment activated"
else
    echo "⚠️ Virtual environment not found at $VENV_PATH"
fi

# ------------------------------
# Start Celery Workers (2 workers, optimized for I/O)
# ------------------------------
start_screen_session "celery_worker1" "python -m celery -A api worker --pool=gevent --concurrency=4 --max-tasks-per-child=1000 -l INFO -Q default -n worker1@%h" "$BACKEND_DIR"
start_screen_session "celery_worker2" "python -m celery -A api worker --pool=gevent --concurrency=4 --max-tasks-per-child=1000 -l INFO -Q default -n worker2@%h" "$BACKEND_DIR"
start_screen_session "celery_admin" \
"python -m celery -A api worker --pool=gevent --concurrency=4 --max-tasks-per-child=1000 -l INFO -n admin@%h -Q admin" \
"$BACKEND_DIR"
start_screen_session "celery_beat" "python -m celery -A api beat -l INFO --scheduler django_celery_beat.schedulers:DatabaseScheduler" "$BACKEND_DIR"
echo "✅ Celery workers and beat started"

# ------------------------------
# Start Gunicorn as daemon (original command preserved)
# ------------------------------
echo "Starting Gunicorn..."
python -m gunicorn api.wsgi --bind 0.0.0.0:8001 --daemon --workers 3 --threads 2
echo "✅ Gunicorn started"

# ------------------------------
# Start Next.js (frontend in screen)
# ------------------------------
cd "$NEXTJS_DIR" || { echo "❌ Failed to cd to $NEXTJS_DIR"; exit 1; }
start_screen_session "nextjs" "npm run start" "$NEXTJS_DIR"
echo "✅ Next.js started"

# ------------------------------
# Done
# ------------------------------
echo "Startup complete: $(date)"