# Celery configuration for background processing
import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Create Celery app instance
celery_app = Celery(
    'bank_transaction_processor',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0'),
    include=['src.tasks']  # Import tasks module
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,

    # Result backend settings
    result_expires=3600,  # Results expire after 1 hour

    # Worker settings
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,

    # Task routing (disabled for now - use default queue)
    # task_routes={
    #     'src.tasks.process_csv_async': {'queue': 'csv_processing'},
    # },

    # Progress tracking
    task_track_started=True,
)

if __name__ == '__main__':
    celery_app.start()