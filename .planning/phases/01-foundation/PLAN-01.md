---
phase: 01-foundation
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/config/base.py
  - requirements.txt
  - requirements-ml.txt
autonomous: true
requirements: [FOUND-01, FOUND-04]
must_haves:
  truths:
    - "FinanzConfig class loads with FINANZ_ENABLED, FINANZ_LLM_ENABLED, token TTLs, upload limits, embedding settings, and all FINANZ_* env vars"
    - "get_env_bool() and get_env_list() are usable as class-level defaults in all config classes (moved above class definitions)"
    - "finanz_config singleton is importable from app.config.base"
    - "celery[redis] is listed in requirements.txt"
    - "requirements-ml.txt exists with pdfplumber, tiktoken, pytesseract, sentence-transformers, chromadb, torch"
  artifacts:
    - app/config/base.py (modified -- FinanzConfig added, helpers moved up)
    - requirements.txt (modified -- celery[redis] added)
    - requirements-ml.txt (new -- ML packages)
  key_links:
    - "finanz_config.FINANZ_ENABLED controls blueprint registration in Phase 2"
    - "finanz_config.FINANZ_LLM_ENABLED controls mock vs live LLM in Phase 4"
---

<objective>
Add FinanzConfig configuration class and install all project dependencies.

Purpose: The Finanzberatung module needs its configuration (feature toggles, upload limits, token TTLs, LLM settings) and all required packages before any feature code can be written.

Output: Modified `app/config/base.py` with FinanzConfig class, updated `requirements.txt` with celery[redis], new `requirements-ml.txt` with ML packages.
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

<interfaces>
<!-- Existing helper functions that must be moved above all class definitions -->

From app/config/base.py (currently lines 286-310, must move to top after imports):
```python
def get_env_bool(key: str, default: bool = False) -> bool:
    """Hilfsfunktion zum Parsen von Boolean-Umgebungsvariablen"""
    return os.getenv(key, str(default)).lower() in ["true", "1", "yes"]

def get_env_list(key: str, default: List[str], separator: str = ",") -> List[str]:
    """Hilfsfunktion zum Parsen von Listen aus Umgebungsvariablen"""
    env_value = os.getenv(key)
    if env_value:
        return [item.strip() for item in env_value.split(separator)]
    return default

def get_env_dict(key: str, default: Dict[str, str], item_separator: str = ",", kv_separator: str = ":") -> Dict[str, str]:
    """Hilfsfunktion zum Parsen von Dictionaries aus Umgebungsvariablen"""
    env_value = os.getenv(key)
    if env_value:
        result = {}
        for item in env_value.split(item_separator):
            if kv_separator in item:
                k, v = item.split(kv_separator, 1)
                result[k.strip()] = v.strip()
            return result
    return default
```

Existing config class pattern (HubSpotConfig, lines 232-253):
```python
class HubSpotConfig:
    HUBSPOT_ACCESS_TOKEN: str = os.getenv("HUBSPOT_ACCESS_TOKEN", "")
    HUBSPOT_ENABLED: bool = bool(os.getenv("HUBSPOT_ACCESS_TOKEN", ""))
    # ...

hubspot_config = HubSpotConfig()
```

Singleton instances at bottom of file (lines 313-322):
```python
config = Config()
slot_config = SlotConfig()
# ...
hubspot_config = HubSpotConfig()
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Move helper functions and add FinanzConfig to app/config/base.py</name>
  <files>app/config/base.py</files>
  <action>
1. **Move helper functions above all class definitions.** Cut `get_env_bool()`, `get_env_list()`, and `get_env_dict()` from lines 286-310 (the "HILFSFUNKTIONEN" section) and paste them immediately after the imports (after `from typing import List, Dict, Any`, before the `class Config:` definition). Remove the old `# ========== HILFSFUNKTIONEN ==========` section header. Add a new section header `# ========== HILFSFUNKTIONEN ==========` above the moved functions, before the Config class.

2. **Add FinanzConfig class** after the HubSpotConfig class (before LoggingConfig). Use this exact structure:

```python
# ========== FINANZBERATUNG KONFIGURATION ==========
class FinanzConfig:
    """Konfiguration fuer Finanzberatungs-Modul"""

    # Master toggle
    FINANZ_ENABLED: bool = get_env_bool("FINANZ_ENABLED", False)

    # LLM toggle
    FINANZ_LLM_ENABLED: bool = get_env_bool("FINANZ_LLM_ENABLED", False)
    FINANZ_LLM_MODEL: str = os.getenv("FINANZ_LLM_MODEL", "meta-llama/Llama-3.1-8B-Instruct")
    FINANZ_LLM_BASE_URL: str = os.getenv("FINANZ_LLM_BASE_URL", "http://localhost:8000/v1")

    # Upload limits
    FINANZ_MAX_FILE_SIZE_MB: int = int(os.getenv("FINANZ_MAX_FILE_SIZE_MB", "50"))
    FINANZ_MAX_UPLOADS_PER_TOKEN: int = int(os.getenv("FINANZ_MAX_UPLOADS_PER_TOKEN", "20"))
    FINANZ_ALLOWED_EXTENSIONS: list = get_env_list(
        "FINANZ_ALLOWED_EXTENSIONS", ["pdf", "jpg", "jpeg", "png", "tiff", "heic"]
    )

    # Token TTLs (seconds)
    FINANZ_TOKEN_TTL_T1: int = int(os.getenv("FINANZ_TOKEN_TTL_T1", "7200"))           # 2h
    FINANZ_TOKEN_TTL_FOLLOWUP: int = int(os.getenv("FINANZ_TOKEN_TTL_FOLLOWUP", "1209600"))  # 14d
    FINANZ_TOKEN_TTL_T2: int = int(os.getenv("FINANZ_TOKEN_TTL_T2", "7200"))           # 2h

    # Embedding / Vector
    FINANZ_EMBEDDING_MODEL: str = os.getenv(
        "FINANZ_EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2"
    )
    FINANZ_CHUNK_SIZE: int = int(os.getenv("FINANZ_CHUNK_SIZE", "4000"))
    FINANZ_CHUNK_OVERLAP: int = int(os.getenv("FINANZ_CHUNK_OVERLAP", "200"))

    # Cache
    FINANZ_CACHE_TTL: int = int(os.getenv("FINANZ_CACHE_TTL", "1800"))  # 30 min

    # Upload directory (relative to PERSIST_BASE)
    FINANZ_UPLOAD_DIR: str = os.getenv("FINANZ_UPLOAD_DIR", "finanz_uploads")
```

3. **Add singleton** at the bottom of the file, after `hubspot_config = HubSpotConfig()`:
```python
finanz_config = FinanzConfig()
```

**IMPORTANT:** Do NOT change any existing class definitions. Only move helper functions and add new code.
  </action>
  <verify>
    <automated>cd C:/Users/Luke/Documents/Slots/slot_booking_webapp && python -c "from app.config.base import finanz_config; assert finanz_config.FINANZ_ENABLED == False; assert finanz_config.FINANZ_TOKEN_TTL_T1 == 7200; assert finanz_config.FINANZ_TOKEN_TTL_FOLLOWUP == 1209600; assert finanz_config.FINANZ_MAX_UPLOADS_PER_TOKEN == 20; print('FinanzConfig OK')"</automated>
  </verify>
  <done>
    - FinanzConfig class exists in app/config/base.py with all settings: FINANZ_ENABLED, FINANZ_LLM_ENABLED, FINANZ_LLM_MODEL, FINANZ_LLM_BASE_URL, FINANZ_MAX_FILE_SIZE_MB, FINANZ_MAX_UPLOADS_PER_TOKEN, FINANZ_ALLOWED_EXTENSIONS, FINANZ_TOKEN_TTL_T1, FINANZ_TOKEN_TTL_FOLLOWUP, FINANZ_TOKEN_TTL_T2, FINANZ_EMBEDDING_MODEL, FINANZ_CHUNK_SIZE, FINANZ_CHUNK_OVERLAP, FINANZ_CACHE_TTL, FINANZ_UPLOAD_DIR
    - finanz_config singleton importable from app.config.base
    - get_env_bool/get_env_list/get_env_dict are above all class definitions
    - All existing config classes still work (no regressions)
  </done>
</task>

<task type="auto">
  <name>Task 2: Update requirements.txt and create requirements-ml.txt</name>
  <files>requirements.txt, requirements-ml.txt</files>
  <action>
1. **Update requirements.txt**: Add `celery[redis]>=5.4.0` in a new "# Task Queue" section after the "# Cache & Session Management" section (after the Flask-Session line, before the "# Testing" section). Do NOT remove any existing packages.

2. **Create requirements-ml.txt** (new file at project root) with:
```
# ML & Document Processing Dependencies
# Install separately: pip install -r requirements-ml.txt
# These packages are NOT required for basic app functionality.
# Only needed when FINANZ_ENABLED=true and running document pipeline.

# PDF & Document Processing
pdfplumber>=0.11.0
tiktoken>=0.7.0
pytesseract>=0.3.10

# Embeddings & Vector Search
sentence-transformers>=3.0.0
chromadb>=0.5.0

# PyTorch (choose based on environment)
# Production (CUDA): pip install torch --index-url https://download.pytorch.org/whl/cu124
# Development (CPU): pip install torch --index-url https://download.pytorch.org/whl/cpu
# Default: CPU-only
torch
```
  </action>
  <verify>
    <automated>cd C:/Users/Luke/Documents/Slots/slot_booking_webapp && python -c "import celery; print(f'celery {celery.__version__} OK')" && grep -q "celery\[redis\]" requirements.txt && echo "requirements.txt OK" && test -f requirements-ml.txt && echo "requirements-ml.txt OK"</automated>
  </verify>
  <done>
    - celery[redis]>=5.4.0 is in requirements.txt
    - requirements-ml.txt exists at project root with pdfplumber, tiktoken, pytesseract, sentence-transformers, chromadb, torch
    - No existing requirements.txt entries were removed or modified
  </done>
</task>

</tasks>

<verification>
1. `python -c "from app.config.base import finanz_config; print(finanz_config.FINANZ_ENABLED)"` returns `False`
2. `python -c "from app.config.base import config, slot_config, hubspot_config; print('existing configs OK')"` -- no regressions
3. `grep "celery\[redis\]" requirements.txt` finds the entry
4. `cat requirements-ml.txt` shows all ML packages
5. `python -c "from app.config.base import get_env_bool; print('helpers accessible')"` -- helpers importable at module level
</verification>

<success_criteria>
- FinanzConfig is importable and all 15 settings have correct defaults
- Moving helpers caused zero regressions in existing config classes
- celery[redis] is in requirements.txt
- requirements-ml.txt exists with 6 ML packages
</success_criteria>

<output>
After completion, create `.planning/phases/01-foundation/01-01-SUMMARY.md`
</output>
