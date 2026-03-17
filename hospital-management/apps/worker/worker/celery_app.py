from celery import Celery

celery_app = Celery(
    "hospital_worker",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/1",
)

celery_app.conf.task_routes = {
    "tasks.health.ping": {"queue": "default"},
}
