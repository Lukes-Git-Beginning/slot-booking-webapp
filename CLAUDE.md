# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Running the Application
```bash
python slot_booking_webapp.py
```

### Testing
```bash
python test_integration.py
```

### Dependencies
```bash
pip install -r requirements.txt
```

## Code Architecture

### Core Application Structure
- **Main Application**: `slot_booking_webapp.py` - Flask app with Google Calendar integration
- **Tracking System**: `tracking_system.py` - Booking analytics and no-show detection  
- **Achievement System**: `achievement_system.py` - Gamification with badges and MVPs
- **Data Persistence**: `data_persistence.py` - Dual-write system (persistent + static directories)
- **Weekly Points**: `weekly_points.py` - Telefonie points tracking with time windows and vacation flags

### Key Architectural Patterns

#### Data Storage Strategy
The app uses a dual-write persistence pattern:
- **Primary**: `/opt/render/project/src/persist/persistent/` (Render disk) or `data/persistent/` (local)
- **Fallback**: `static/` directory for compatibility with legacy systems
- All JSON data is UTF-8 encoded with `ensure_ascii=False`

#### Google Calendar Integration
- Central calendar: `zentralkalenderzfa@gmail.com`
- Service account authentication via `GOOGLE_CREDS_BASE64` environment variable
- Robust error handling with retry logic in `safe_calendar_call()` function
- Color-coded events map to booking outcomes (see `color_mapping.py`)

#### Gamification System
- Badge system with rarity levels (common → mythic)
- Daily/weekly/monthly achievements
- MVP tracking with automatic award scheduling
- Points accumulation tied to booking activities

#### Time Window Logic
- Telefonie points have commit windows (18-21h Europe/Berlin timezone)
- Outside commit window, changes go to pending queues
- Vacation flags override point calculations

### Data Flow
1. **Booking Creation**: User books → Calendar event created → Tracking logged
2. **Outcome Detection**: Daily cron checks event colors → Updates customer profiles
3. **Achievement Processing**: Daily cron evaluates points → Awards badges/MVP status
4. **Availability Generation**: Hourly cron scans consultant calendars → Updates available slots

### Environment Variables
- `GOOGLE_CREDS_BASE64`: Base64-encoded service account JSON
- `CENTRAL_CALENDAR_ID`: Main calendar ID
- `USERLIST`: User credentials (`user1:pass1,user2:pass2`)
- `SECRET_KEY`: Flask session encryption key
- `PERSIST_BASE`: Override for persistence directory

### Critical Files
- `service_account.json`: Google service account credentials (never commit)
- `data/persistent/`: Core data storage
- `static/availability.json`: Generated slot availability
- `color_mapping.py`: Central outcome → color mapping