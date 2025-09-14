#!/usr/bin/env python3
"""
Startup script to run all services for Bank Transaction Categorizer
"""
import subprocess
import sys
import os
import time
import signal
from pathlib import Path


def check_redis():
    """Check if Redis is running."""
    try:
        # Use poetry run to check redis in the virtual environment
        result = subprocess.run([
            "poetry", "run", "python", "-c",
            "import redis; r = redis.Redis(host='localhost', port=6379, db=0); r.ping(); print('REDIS_OK')"
        ], capture_output=True, text=True, timeout=10)

        if result.returncode == 0 and "REDIS_OK" in result.stdout:
            print("✅ Redis is running")
            return True
        else:
            print(f"❌ Redis check failed - Return code: {result.returncode}")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Redis check failed: {e}")
        return False


def start_redis_if_needed():
    """Try to start Redis using common methods."""
    if check_redis():
        return True

    print("🔧 Attempting to start Redis...")

    # Try homebrew service
    try:
        subprocess.run(['brew', 'services', 'start', 'redis'],
                      check=True, capture_output=True)
        time.sleep(2)
        if check_redis():
            return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # Try direct redis-server
    try:
        subprocess.Popen(['redis-server'],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL)
        time.sleep(3)
        if check_redis():
            return True
    except FileNotFoundError:
        pass

    print("❌ Could not start Redis automatically")
    print("Please start Redis manually:")
    print("  macOS: brew services start redis")
    print("  Linux: sudo systemctl start redis-server")
    print("  Docker: docker run -d -p 6379:6379 redis:alpine")
    return False


def main():
    print("🚀 Bank Transaction Categorizer - Startup")
    print("=" * 50)

    # Check if we're in the right directory
    if not Path("src/celery_app.py").exists():
        print("❌ Please run this script from the project root directory")
        return

    # Start Redis if needed
    if not start_redis_if_needed():
        return

    print("\n🎯 Starting all services...")
    processes = []

    try:
        # Start Celery worker
        print("📦 Starting Celery worker...")
        celery_cmd = [
            "poetry", "run",
            "celery", "-A", "src.celery_app", "worker",
            "--loglevel=info", "--concurrency=2"
        ]
        celery_process = subprocess.Popen(celery_cmd)
        processes.append(("Celery Worker", celery_process))
        time.sleep(2)

        # Start Streamlit app
        print("🌐 Starting Streamlit app...")
        streamlit_cmd = [
            "poetry", "run",
            "streamlit", "run", "app.py", "--server.headless=true"
        ]
        streamlit_process = subprocess.Popen(streamlit_cmd)
        processes.append(("Streamlit App", streamlit_process))

        print("\n" + "=" * 50)
        print("✅ All services started successfully!")
        print("📊 Streamlit app: http://localhost:8501")
        print("⚙️  Celery worker: Running in background")
        print("🔴 Redis: Running on localhost:6379")
        print("\n💡 Press Ctrl+C to stop all services")
        print("=" * 50)

        # Wait for processes and handle shutdown
        try:
            while True:
                # Check if any process died
                for name, process in processes:
                    if process.poll() is not None:
                        print(f"❌ {name} stopped unexpectedly")
                        return
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Stopping all services...")

    except Exception as e:
        print(f"❌ Error starting services: {e}")

    finally:
        # Clean up processes
        for name, process in processes:
            try:
                print(f"🔄 Stopping {name}...")
                process.terminate()
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                print(f"⚡ Force killing {name}...")
                process.kill()
            except Exception as e:
                print(f"❌ Error stopping {name}: {e}")

        print("✅ All services stopped")


if __name__ == "__main__":
    main()