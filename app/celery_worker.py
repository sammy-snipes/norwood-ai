import logging

from celery import Celery

from app.config import get_settings

settings = get_settings()

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger(__name__)

celery_app = Celery(
    "norwood_ai",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.analyze",
        "app.tasks.counseling",
        "app.tasks.certification",
        "app.tasks.forum",
    ],
)

celery_app.conf.update(
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,  # Results expire after 1 hour
    beat_schedule={
        "check-forum-agent-schedules": {
            "task": "check_forum_agent_schedules",
            "schedule": 60.0,  # Every 60 seconds
        },
    },
)

# Reduce verbosity of task success logs (don't print full return value)
logging.getLogger("celery.app.trace").setLevel(logging.WARNING)

logger.info("Celery worker configured")
