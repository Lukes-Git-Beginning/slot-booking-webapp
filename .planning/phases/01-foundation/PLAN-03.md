---
phase: 01-foundation
plan: 03
type: execute
wave: 2
depends_on: ["01-01"]
files_modified:
  - app/core/celery_init.py
  - app/core/extensions.py
  - app/__init__.py
  - celery_worker.py
  - app/services/finanz_tasks.py
autonomous: true
requirements: [FOUND-03]
must_haves:
  truths:
    - "celery_init_app() function exists in app/core/celery_init.py with FlaskTask wrapper"
    - "Celery is initialized in init_extensions() with graceful degradation (try/except)"
    - "CELERY config dict is set in create_app() with Redis DB 1 for broker, DB 2 for results"
    - "celery_worker.py at project root creates Flask app and exports celery_app"
    - "CELERY_TASK_ALWAYS_EAGER=true makes tasks run synchronously for development"
    - "task_eager_propagates=True ensures exceptions bubble up in dev mode"
    - "health_check_task exists and can be called (at least in eager mode)"
    - "JSON-only serialization configured (no pickle)"
    - "task_acks_late=True and task_reject_on_worker_lost=True for reliability"
  artifacts:
    - app/core/celery_init.py (new -- celery_init_app function)
    - app/core/extensions.py (modified -- celery init added)
    - app/__init__.py (modified -- CELERY config dict added to create_app)
    - celery_worker.py (new -- worker entry point)
    - app/services/finanz_tasks.py (new -- health check test task)
  key_links:
    - "celery_init_app() called from init_extensions() which runs during create_app()"
    - "celery_worker.py imports create_app and exposes celery_app for CLI: celery -A celery_worker:celery_app worker"
    - "All future Celery tasks (@shared_task) automatically get Flask app context via FlaskTask"
---

<objective>
Set up Celery task queue with Flask integration, Redis broker separation, and a health check test task.

Purpose: Background task processing is required for the document pipeline (Phase 4). Celery needs to be wired into the Flask app factory with proper Redis DB separation, dev-mode eager execution, and a test task to verify connectivity.

Output: New `app/core/celery_init.py`, modified `app/core/extensions.py` and `app/__init__.py`, new `celery_worker.py` and `app/services/finanz_tasks.py`.
</objective>

<execution_context>
@C:/Users/Luke/.claude/get-shit-done/workflows/execute-plan.md
@C:/Users/Luke/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/phases/01-foundation/01-CONTEXT.md
@.planning/phases/01-foundation/01-RESEARCH.md
@.planning/phases/01-foundation/01-01-SUMMARY.md

<interfaces>
<!-- Extension initialization pattern from app/core/extensions.py -->

From app/core/extensions.py (init_extensions signature and pattern):
```python
def init_extensions(app: Flask) -> None:
    """Initialize all Flask extensions and external services"""
    global cache_manager, data_persistence, error_handler, level_system, tracking_system, hubspot_service, limiter, csrf, sess
    # ... existing init code ...

    # HubSpot pattern (graceful degradation):
    try:
        from app.services.hubspot_service import hubspot_service as hs
        hubspot_service = hs
        hubspot_service.init_app(app)
    except Exception as e:
        logger.info(f"HubSpot integration not initialized: {e}")
        hubspot_service = None
```

From app/__init__.py (create_app structure):
```python
def create_app(config_object=None) -> Flask:
    app = Flask(...)
    # ... config loading ...

    from app.core.extensions import init_extensions
    init_extensions(app)

    from app.models import init_db, is_postgres_enabled
    if is_postgres_enabled():
        init_db(app)

    # ... middleware, logging, sentry, validation ...
    register_blueprints(app)
    # ... error handlers, context processors, request hooks ...
    return app
```

Redis URL pattern (from existing code):
```python
redis_url = os.getenv('REDIS_URL')  # e.g., redis://localhost:6379/0
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Create Celery init module and worker entry point</name>
  <files>app/core/celery_init.py, celery_worker.py, app/services/finanz_tasks.py</files>
  <action>
1. **Create `app/core/celery_init.py`** with the Flask-Celery integration:

```python
# -*- coding: utf-8 -*-
"""
Celery initialization with Flask app context integration.

Source: https://flask.palletsprojects.com/en/stable/patterns/celery/
All tasks automatically run within Flask app context.
"""
import logging
from celery import Celery, Task
from flask import Flask

logger = logging.getLogger(__name__)


def celery_init_app(app: Flask) -> Celery:
    """Initialize Celery with Flask app context.

    All tasks automatically run within Flask app context,
    enabling access to database, config, and other extensions.

    Args:
        app: Flask application instance with CELERY config dict set.

    Returns:
        Configured Celery application instance.
    """
    class FlaskTask(Task):
        def __call__(self, *args: object, **kwargs: object) -> object:
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    app.extensions["celery"] = celery_app
    logger.info("Celery initialized successfully")
    return celery_app
```

2. **Create `celery_worker.py`** at project root:

```python
# -*- coding: utf-8 -*-
"""
Celery worker entry point.

Usage:
    celery -A celery_worker:celery_app worker --loglevel=info

For development with CELERY_TASK_ALWAYS_EAGER=true,
tasks run synchronously inside the Flask process (no worker needed).
"""
from dotenv import load_dotenv
load_dotenv()

from app import create_app

flask_app = create_app()
celery_app = flask_app.extensions["celery"]
```

3. **Create `app/services/finanz_tasks.py`** with a health check test task:

```python
# -*- coding: utf-8 -*-
"""
Finanzberatung Celery tasks.

All tasks use @shared_task to avoid circular imports with the app factory.
Tasks are automatically discovered when celery_worker.py creates the Flask app.

Future task files (Phase 4):
- app/services/document_tasks.py (extraction, OCR, classification)
- app/services/analysis_tasks.py (embedding, scorecard generation)
"""
import logging
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(ignore_result=False)
def health_check_task():
    """Simple test task to verify Celery worker connectivity.

    Returns dict with status info. Used by deployment health checks
    and during Phase 1 verification.
    """
    logger.info("Celery health check task executed successfully")
    return {"status": "ok", "message": "Celery worker is running"}
```
  </action>
  <verify>
    <automated>cd C:/Users/Luke/Documents/Slots/slot_booking_webapp && python -c "
import os
# Verify files exist
assert os.path.exists('app/core/celery_init.py'), 'celery_init.py missing'
assert os.path.exists('celery_worker.py'), 'celery_worker.py missing'
assert os.path.exists('app/services/finanz_tasks.py'), 'finanz_tasks.py missing'

# Verify celery_init_app is importable
from app.core.celery_init import celery_init_app
assert callable(celery_init_app)

# Verify health check task is importable
from app.services.finanz_tasks import health_check_task
assert callable(health_check_task)

print('Celery files and imports OK')
"</automated>
  </verify>
  <done>
    - app/core/celery_init.py exists with celery_init_app() function and FlaskTask wrapper
    - celery_worker.py exists at project root with Flask app creation and celery_app export
    - app/services/finanz_tasks.py exists with health_check_task
    - All three files are importable without errors
  </done>
</task>

<task type="auto">
  <name>Task 2: Wire Celery into Flask app factory and extensions</name>
  <files>app/__init__.py, app/core/extensions.py</files>
  <action>
1. **Modify `app/__init__.py`** -- Add CELERY config dict to `create_app()`.

Insert the following block AFTER the config loading section (`app.config.from_object(...)`) and BEFORE the `init_extensions(app)` call. Place it right before the line `# Extensions initialisieren (bestehende)`:

```python
    # Celery configuration (must be set before init_extensions)
    import os as _os
    _redis_url = _os.getenv("REDIS_URL", "redis://localhost:6379")
    # Strip trailing /N to get base URL for DB separation
    _redis_base = _redis_url.rsplit("/", 1)[0] if _redis_url.count("/") > 2 else _redis_url

    app.config["CELERY"] = {
        "broker_url": f"{_redis_base}/1",
        "result_backend": f"{_redis_base}/2",
        "task_ignore_result": True,
        "task_serializer": "json",
        "result_serializer": "json",
        "accept_content": ["json"],
        "task_acks_late": True,
        "task_reject_on_worker_lost": True,
        "task_track_started": True,
        "result_expires": 86400,
        "timezone": "Europe/Berlin",
        "enable_utc": True,
        "task_always_eager": _os.getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower()
            in ["true", "1", "yes"],
        "task_eager_propagates": True,
    }
```

**Note:** Use `_os` and `_redis_url`/`_redis_base` as local variable names to avoid shadowing the existing `os` import at the top of the file. Alternatively, just use the already-imported `os` module directly since it is already imported at the top of the file (line 9: `import os`). In that case, no need for `import os as _os` -- just use `os` directly.

2. **Modify `app/core/extensions.py`** -- Add Celery initialization to `init_extensions()`.

Add the Celery init block at the END of `init_extensions()`, AFTER the `init_session_storage(app)` call and BEFORE the final `logger.info("All extensions initialized successfully")` line:

```python
    # Initialize Celery task queue (graceful degradation if Redis unavailable)
    try:
        from app.core.celery_init import celery_init_app
        celery_app = celery_init_app(app)

        # Auto-discover task modules
        celery_app.autodiscover_tasks(['app.services'], related_name='finanz_tasks')
    except Exception as e:
        logger.info(f"Celery not initialized: {e}")
```

**IMPORTANT:** Do NOT modify any existing code in either file. Only ADD the new blocks at the specified locations.
  </action>
  <verify>
    <automated>cd C:/Users/Luke/Documents/Slots/slot_booking_webapp && CELERY_TASK_ALWAYS_EAGER=true USE_POSTGRES=false python -c "
import os
os.environ['CELERY_TASK_ALWAYS_EAGER'] = 'true'
os.environ['USE_POSTGRES'] = 'false'

from app import create_app
app = create_app()

# Verify CELERY config exists
assert 'CELERY' in app.config, 'CELERY config missing'
celery_cfg = app.config['CELERY']
assert celery_cfg['task_serializer'] == 'json', 'JSON serializer not set'
assert celery_cfg['task_acks_late'] == True, 'task_acks_late not set'
assert celery_cfg['task_always_eager'] == True, 'eager mode not activated'
assert celery_cfg['task_eager_propagates'] == True, 'eager propagates not set'
assert '/1' in celery_cfg['broker_url'], 'broker not on Redis DB 1'
assert '/2' in celery_cfg['result_backend'], 'results not on Redis DB 2'

# Verify Celery is in app extensions
assert 'celery' in app.extensions, 'Celery not in app.extensions'

# Verify health check task works in eager mode
with app.app_context():
    from app.services.finanz_tasks import health_check_task
    result = health_check_task.delay()
    assert result.get()['status'] == 'ok', 'Health check task failed'

print('Celery integration verified OK')
"</automated>
  </verify>
  <done>
    - CELERY config dict is set in create_app() with Redis DB 1 for broker, DB 2 for results
    - Celery is initialized in init_extensions() with graceful degradation
    - In eager mode (CELERY_TASK_ALWAYS_EAGER=true), tasks run synchronously and health_check_task returns {"status": "ok"}
    - JSON-only serialization, task_acks_late, task_reject_on_worker_lost, task_track_started all configured
    - No regressions on existing extensions (data_persistence, tracking, etc.)
  </done>
</task>

</tasks>

<verification>
1. `CELERY_TASK_ALWAYS_EAGER=true USE_POSTGRES=false python -c "from app import create_app; app = create_app(); print('celery' in app.extensions)"` returns `True`
2. Health check task executes in eager mode and returns `{"status": "ok"}`
3. `python -c "from celery_worker import celery_app; print(type(celery_app))"` shows Celery instance (requires CELERY_TASK_ALWAYS_EAGER=true)
4. Existing app functionality unaffected (run a quick `python -c "from app import create_app; create_app()"` with USE_POSTGRES=false)
</verification>

<success_criteria>
- Celery is fully integrated into Flask app factory with FlaskTask app context wrapper
- Redis DB separation: DB 0 untouched (sessions), DB 1 broker, DB 2 results
- Dev mode (eager) works without a running Redis/Celery worker
- Health check task verifies the full chain works
- celery_worker.py provides the CLI entry point for production workers
- No regressions on existing app startup
</success_criteria>

<output>
After completion, create `.planning/phases/01-foundation/01-03-SUMMARY.md`
</output>
