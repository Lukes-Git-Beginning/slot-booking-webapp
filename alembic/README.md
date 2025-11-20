# Alembic Database Migrations

Automatische PostgreSQL-Migrations basierend auf SQLAlchemy Models.

## Befehle

### Neue Migration erstellen (autogenerate)
```bash
alembic revision --autogenerate -m "Beschreibung der Änderung"
```

Beispiele:
```bash
alembic revision --autogenerate -m "Add user email field"
alembic revision --autogenerate -m "Create weekly points table"
```

### Migrations anwenden

```bash
# Alle ausstehenden Migrations anwenden
alembic upgrade head

# Eine bestimmte Migration anwenden
alembic upgrade <revision_id>

# Eine Migration zurückrollen
alembic downgrade -1

# Bis zu einer bestimmten Revision zurückrollen
alembic downgrade <revision_id>
```

### Migration-Status

```bash
# Aktuelle Revision anzeigen
alembic current

# Migration-Historie anzeigen
alembic history

# Detaillierte Historie
alembic history --verbose
```

### Datenbank-Vergleich

```bash
# Unterschiede zwischen Models und Database anzeigen (ohne Migration zu erstellen)
alembic check
```

## Workflow

1. **Models ändern** (z.B. in `app/models/user.py`)
2. **Migration generieren**: `alembic revision --autogenerate -m "Add new field"`
3. **Migration prüfen**: Datei in `alembic/versions/` öffnen und prüfen
4. **Migration testen** (lokal): `alembic upgrade head`
5. **Migration committen**: `git add alembic/versions/...` + `git commit`
6. **Auf Server deployen**: `alembic upgrade head` auf Production

## Initial Migration (bereits erstellt)

Die Initial-Migration erstellt alle Tables basierend auf den aktuellen Models:

```bash
# Wurde automatisch erstellt mit:
alembic revision --autogenerate -m "Initial migration - all tables"
```

## Tipps

### Migration-Skript manuell anpassen

Nach `alembic revision --autogenerate` solltest du die generierte Datei prüfen:

1. Öffne `alembic/versions/<timestamp>_<slug>.py`
2. Prüfe `upgrade()` und `downgrade()` Funktionen
3. Passe an falls nötig (z.B. Data-Migrations, Custom-Logic)
4. Teste lokal vor Deployment

### Data-Migration hinzufügen

Beispiel: Daten von einer Spalte in eine andere kopieren

```python
def upgrade():
    # Schema-Änderung
    op.add_column('users', sa.Column('full_name', sa.String(200)))

    # Data-Migration
    connection = op.get_bind()
    connection.execute(
        """
        UPDATE users
        SET full_name = first_name || ' ' || last_name
        WHERE full_name IS NULL
        """
    )

def downgrade():
    op.drop_column('users', 'full_name')
```

### Rollback-Plan

Immer VOR Migration ein Backup erstellen:

```bash
# PostgreSQL Backup
pg_dump -U business_hub_user business_hub > backup_pre_migration.sql

# Nach Migration (bei Problemen):
psql -U business_hub_user business_hub < backup_pre_migration.sql
```

## Troubleshooting

### "Target database is not up to date"

```bash
# Lösung: Datenbank auf aktuelle Revision bringen
alembic upgrade head
```

### "Can't locate revision identified by..."

```bash
# Lösung: Revision-History reparieren
alembic stamp head  # Markiert aktuelle DB als "head"
```

### Migration schlägt fehl

```bash
# Rollback zur vorherigen Version
alembic downgrade -1

# Logs prüfen
tail -f /var/log/business-hub/error.log
```

## Struktur

```
alembic/
├── env.py              # Environment-Setup
├── script.py.mako      # Template für neue Migrations
├── README.md           # Diese Datei
└── versions/           # Migration-Scripts
    └── 20251120_...py  # Initial Migration
```

## Weitere Infos

- [Alembic Dokumentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy Migrations Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
