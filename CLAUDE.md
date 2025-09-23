# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Slot Booking Webapp** is a comprehensive, enterprise-grade appointment scheduling system with advanced gamification, analytics, and business intelligence features. This is not just a simple booking system - it's a full-featured business application with sophisticated user engagement and data analytics capabilities.

### Key Capabilities
- 🎯 **Complete Appointment Management** - Multi-consultant booking with Google Calendar integration
- 🎮 **Advanced Gamification** - Achievement systems, badges, levels, prestige, daily quests, cosmetics shop
- 📊 **Business Intelligence** - Comprehensive analytics, predictive insights, customer profiling
- 🔧 **Admin Dashboard** - Full administrative control with reporting and user management
- 🎨 **Customization System** - User personalization with themes, avatars, and custom goals
- 📱 **Modern Architecture** - Production-ready Flask application with proper separation of concerns

## Development Commands

### Running the Application
```bash
python run.py                    # Start the application (new structure)
# OR
python slot_booking_webapp.py    # Legacy startup method
```

### Testing
```bash
python test_integration.py       # Run comprehensive integration tests
```

### Dependencies
```bash
pip install -r requirements.txt  # Install all dependencies
```

### Development Tools
```bash
python -c "from app.core.extensions import data_persistence; data_persistence.create_backup()"  # Manual backup
python -c "from app.services.achievement_system import achievement_system; achievement_system.process_daily_achievements()"  # Process achievements
```

## Application Architecture

### Modern Flask Structure
The application follows a professional Flask structure with:

```
app/
├── config/           # Environment-based configuration
│   ├── base.py      # Base configuration classes
│   ├── development.py
│   └── production.py
├── core/            # Core application components
│   ├── extensions.py    # Flask extensions initialization
│   ├── google_calendar.py  # Google Calendar service
│   └── middleware.py    # Request/response middleware
├── routes/          # HTTP route handlers (blueprints)
│   ├── admin/       # Administrative functions
│   ├── gamification/ # Gamification features
│   ├── auth.py      # Authentication
│   ├── booking.py   # Appointment booking
│   ├── calendar.py  # Calendar views
│   ├── main.py      # Main application routes
│   └── api.py       # JSON API endpoints
├── services/        # Business logic layer
│   ├── achievement_system.py  # Gamification engine
│   ├── booking_service.py     # Booking business logic
│   ├── data_persistence.py    # Data storage abstraction
│   ├── level_system.py        # User progression system
│   ├── tracking_system.py     # Analytics and tracking
│   └── weekly_points.py       # Points management
├── models/          # Data models (if using ORM)
└── utils/           # Utility functions and helpers
```

### Core Application Components
- **Flask Application Factory**: `app/__init__.py` - Modern Flask app creation pattern
- **Configuration Management**: `app/config/` - Environment-specific settings
- **Google Calendar Integration**: `app/core/google_calendar.py` - Robust calendar service
- **Data Persistence Layer**: `app/services/data_persistence.py` - Dual-write system
- **Gamification Engine**: `app/services/achievement_system.py` - Complete engagement system
- **Analytics System**: `app/services/tracking_system.py` - Business intelligence
- **Admin Dashboard**: `app/routes/admin/` - Comprehensive management interface

### Key Architectural Patterns

#### Data Storage Strategy
The app uses a sophisticated dual-write persistence pattern:
- **Primary**: `/opt/render/project/src/persist/persistent/` (Render disk) or `data/persistent/` (local)
- **Fallback**: `static/` directory for compatibility with legacy systems
- All JSON data is UTF-8 encoded with `ensure_ascii=False`
- Automatic backup system with retention policies
- Data integrity validation and migration support

#### Google Calendar Integration
- Central calendar: `zentralkalenderzfa@gmail.com`
- Service account authentication via `GOOGLE_CREDS_BASE64` environment variable
- Robust error handling with retry logic in `safe_calendar_call()` function
- Color-coded events map to booking outcomes (see `color_mapping.py`)
- Multi-consultant calendar support with availability scanning

#### Advanced Gamification System
- **Badge System**: 6 rarity levels (common → mythic) with 50+ unique badges
- **Level System**: XP-based progression with rewards and unlocks
- **Prestige System**: 6 prestige levels with 5 mastery categories
- **Daily Quests**: Rotating challenges with mini-games and rewards
- **Cosmetics Shop**: Titles, themes, avatars, and special effects
- **Achievement Engine**: Real-time progress tracking and automatic awards
- **Personal Goals**: User-defined challenges with custom rewards

#### Business Intelligence & Analytics
- **Customer Profiling**: Risk assessment and reliability scoring
- **Behavioral Analytics**: Pattern detection and insights
- **Predictive Modeling**: Success rate predictions and recommendations
- **Performance Tracking**: Individual and team metrics
- **Historical Analysis**: 269+ days of integrated booking data
- **Export Capabilities**: JSON, CSV, PDF with customizable filters

#### Time Window Logic & Points System
- Telefonie points have commit windows (18-21h Europe/Berlin timezone)
- Outside commit window, changes go to pending queues
- Vacation flags override point calculations
- Weekly point tracking with rollover and bonus systems
- Achievement milestones tied to point accumulation

### Advanced Data Flow

#### 1. Booking Lifecycle
```
User Request → Validation → Calendar Check → Slot Creation → Tracking → Gamification Update → Notification
```

#### 2. Real-time Processing
```
Event Trigger → Data Update → Cache Invalidation → Achievement Check → UI Update → Analytics Log
```

#### 3. Scheduled Operations
- **Hourly**: Availability generation, cache refresh
- **Daily**: Outcome processing, achievement awards, analytics aggregation
- **Weekly**: Point rollover, leaderboard updates, backup creation
- **Monthly**: Historical analysis, report generation, data archiving

#### 4. Gamification Pipeline
```
User Action → Progress Tracking → Quest Update → Badge Evaluation → Level Check → Reward Distribution
```

## Complete Feature Catalog

### 🎯 Core Booking Features
- **Multi-Consultant Scheduling**: Support for unlimited consultants with individual calendars
- **Real-time Availability**: Hourly calendar scanning and slot generation
- **Conflict Prevention**: Advanced booking validation and double-booking prevention
- **Customer Management**: Complete customer profiles with history and preferences
- **Outcome Tracking**: Automatic detection of appointments, no-shows, and cancellations

### 🎮 Gamification Features (Advanced)
- **Achievement System**: 50+ badges across 6 rarity levels
- **XP & Level System**: Progressive advancement with rewards
- **Prestige System**: 6 prestige levels with specialized mastery tracks
- **Daily Quests**: Rotating challenges with mini-games and rewards
- **Leaderboards**: Multiple ranking categories and competitive elements
- **Cosmetics Shop**: Full customization with titles, themes, avatars, effects
- **Personal Goals**: User-defined challenges with custom rewards
- **Behavioral Analytics**: Pattern recognition and performance insights

### 📊 Analytics & Business Intelligence
- **Performance Dashboards**: Real-time metrics and KPIs
- **Customer Profiling**: Risk assessment and reliability scoring
- **Predictive Analytics**: Success rate predictions and recommendations
- **Historical Analysis**: 269+ days of integrated booking data
- **Export Functions**: JSON, CSV, PDF with advanced filtering
- **Trend Analysis**: Pattern detection and insight generation
- **Team Performance**: Comparative analysis and benchmarking

### 🔧 Administrative Features
- **User Management**: Complete user lifecycle management
- **Role-Based Access**: Admin/user permissions with granular controls
- **Data Export**: Comprehensive reporting and data extraction
- **System Monitoring**: Performance metrics and health checks
- **Configuration Management**: Dynamic settings and feature toggles
- **Backup & Recovery**: Automated backup with retention policies

### 🎨 Customization & Personalization
- **Theme System**: Multiple visual themes and color schemes
- **Avatar System**: Customizable user profiles with unlockable components
- **Dashboard Customization**: Personalized layouts and widgets
- **Notification Preferences**: Customizable alerts and updates
- **Personal Analytics**: Individual insights and progress tracking

### Environment Variables & Configuration
- `GOOGLE_CREDS_BASE64`: Base64-encoded service account JSON
- `CENTRAL_CALENDAR_ID`: Main calendar ID
- `USERLIST`: User credentials (`user1:pass1,user2:pass2`)
- `SECRET_KEY`: Flask session encryption key
- `PERSIST_BASE`: Override for persistence directory
- `FLASK_ENV`: Environment setting (development/production)
- `ADMIN_USERS`: Comma-separated list of admin usernames
- `CONSULTANTS`: Consultant mapping (name:email pairs)
- `EXCLUDED_CHAMPION_USERS`: Users excluded from leaderboards

### Critical Files & Directories
- `service_account.json`: Google service account credentials (never commit)
- `data/persistent/`: Primary data storage with complete application state
- `data/backups/`: Automated backup directory with retention
- `static/availability.json`: Generated slot availability (legacy fallback)
- `app/config/`: Environment-specific configuration files
- `templates/`: Jinja2 HTML templates for all pages
- `static/`: CSS, JavaScript, and static assets

## Development Workflow & Best Practices

### Code Quality Standards
- **Follow Flask best practices**: Use blueprints, application factory pattern
- **Maintain separation of concerns**: Services for business logic, routes for HTTP handling
- **Type hints encouraged**: Use Python type hints for better code clarity
- **Error handling**: Always implement proper error handling with logging
- **Testing**: Write tests for new features and critical functionality

### Database & Data Management
- **JSON-first approach**: All data stored in optimized JSON format
- **Dual-write pattern**: Always write to both persistent and static directories
- **Backup strategy**: Automated backups with manual backup capabilities
- **Data integrity**: Validate data on read/write operations
- **UTF-8 encoding**: Always use `ensure_ascii=False` for JSON files

### API Development
- **RESTful principles**: Follow REST conventions for API endpoints
- **JSON responses**: Consistent JSON structure for all API responses
- **Error codes**: Use appropriate HTTP status codes
- **Rate limiting**: Implement rate limiting for API endpoints
- **Documentation**: Document all API endpoints with examples

### Troubleshooting & Debugging

#### Common Issues
1. **Google Calendar API Errors**
   ```bash
   # Check credentials
   python -c "from app.core.google_calendar import GoogleCalendarService; print('OK' if GoogleCalendarService().is_configured() else 'FAIL')"
   ```

2. **Data Persistence Issues**
   ```bash
   # Verify data integrity
   python -c "from app.services.data_persistence import data_persistence; data_persistence.verify_integrity()"
   ```

3. **Gamification System Issues**
   ```bash
   # Reset user achievements (admin only)
   python -c "from app.services.achievement_system import achievement_system; achievement_system.reset_user_progress('username')"
   ```

4. **Performance Issues**
   ```bash
   # Clear all caches
   python -c "from app.core.extensions import cache_manager; cache_manager.clear_all()"
   ```

### Testing Strategy
- **Integration tests**: `test_integration.py` covers end-to-end workflows
- **Unit tests**: Individual component testing
- **Performance tests**: Load testing for critical paths
- **Data tests**: Validate data integrity and migration

### Deployment Checklist
- [ ] Environment variables configured
- [ ] Google Calendar credentials valid
- [ ] Database/persistence layer initialized
- [ ] Static assets properly served
- [ ] Scheduled tasks configured (GitHub Actions)
- [ ] Monitoring and logging enabled
- [ ] Backup system operational

## Git Commit Guidelines
- **NEVER** include Claude Code attribution in commit messages
- **NEVER** add "🤖 Generated with [Claude Code]" or "Co-Authored-By: Claude"
- Keep commit messages clean and professional without AI tool references
- Use conventional commit format: `feat:`, `fix:`, `docs:`, `refactor:`, etc.
- Reference issue numbers when applicable

## Project Status & Recent Updates

### Current Version: v3.0+ (Enterprise-Grade)
The application has evolved into a sophisticated business platform with:
- ✅ **Complete Gamification System**: Advanced engagement features
- ✅ **Business Intelligence**: Comprehensive analytics and reporting
- ✅ **Modern Architecture**: Production-ready Flask application
- ✅ **Administrative Dashboard**: Full management capabilities
- ✅ **Customization Platform**: User personalization features
- ✅ **Performance Optimization**: Caching, deduplication, error handling

### Latest Feature Additions
- ✅ **Daily Quest Updates**: Enhanced challenges and mini-games
- ✅ **Cosmetics Shop System**: Complete customization platform
- ✅ **Advanced Analytics**: Behavioral insights and predictions
- ✅ **Performance Improvements**: Caching and optimization
- ✅ **Modern Flask Structure**: Proper application organization

### Next Development Priorities
- 🔄 **API Enhancement**: Comprehensive REST API for mobile/external apps
- 🔄 **Real-time Features**: WebSocket integration for live updates
- 🔄 **Machine Learning**: Predictive analytics and recommendation engine
- 🔄 **Mobile PWA**: Progressive Web App capabilities
- 🔄 **Advanced Security**: Enhanced authentication and authorization

## Technical Implementation Guide

### Working with the Codebase

#### Key Service Classes
```python
# Core services - always import these for major operations
from app.services.data_persistence import data_persistence
from app.services.achievement_system import achievement_system
from app.services.booking_service import BookingService
from app.services.tracking_system import tracking_system
from app.core.extensions import cache_manager, level_system
```

#### Data Persistence Patterns
```python
# Always use the data persistence layer for data operations
data_persistence.save_data('user_badges', badge_data)
user_data = data_persistence.load_data('user_stats', {})
data_persistence.create_backup()  # Manual backup creation
```

#### Adding New Features
1. **Create service class** in `app/services/` for business logic
2. **Add route handlers** in appropriate `app/routes/` blueprint
3. **Update configuration** in `app/config/base.py` if needed
4. **Add tests** to `test_integration.py`
5. **Update documentation** in both CLAUDE.md and README.md

#### Gamification Integration
```python
# Award achievements for new features
from app.services.achievement_system import achievement_system

def handle_new_feature_action(user, action_data):
    # Your feature logic here
    result = perform_action(action_data)

    # Integrate with gamification
    achievement_system.update_quest_progress(user, 'new_feature_quest', 1)
    achievement_system.check_and_award_badges(user)

    return result
```

#### Error Handling Best Practices
```python
import logging
from app.utils.logging import get_logger

logger = get_logger(__name__)

def safe_operation():
    try:
        # Your operation here
        result = risky_operation()
        logger.info("Operation completed successfully")
        return result
    except Exception as e:
        logger.error(f"Operation failed: {str(e)}", extra={'operation': 'safe_operation'})
        return None
```

### Database Schema (JSON Collections)

#### Core Data Structure
```
data/persistent/
├── user_badges.json          # Badge awards and timestamps
├── user_levels.json          # XP and level progression
├── daily_user_stats.json     # Daily performance metrics
├── prestige_data.json        # Prestige system data
├── cosmetic_purchases.json   # Shop purchases and equipped items
├── daily_quests.json         # Quest progress and completions
├── behavior_patterns.json    # User behavior analytics
├── weekly_points.json        # Telefonie points system
├── champions.json            # Leaderboard data
└── scores.json               # Overall scoring system
```

#### Data Relationships
- **Users** are identified by username strings
- **Badges** link to users via username keys
- **Quests** track progress per user per day
- **Analytics** aggregate data across multiple timeframes
- **Points** follow weekly cycles with rollover logic

### API Development Guidelines

#### Creating New Endpoints
```python
# In app/routes/api.py
@api_bp.route("/feature/<parameter>")
@require_login
def api_new_feature(parameter):
    """API endpoint for new feature"""
    try:
        user = session.get("user")
        result = feature_service.process(user, parameter)
        return jsonify({"success": True, "data": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

#### Response Format Standards
```python
# Success response
{
    "success": true,
    "data": {...},
    "message": "Operation completed"
}

# Error response
{
    "success": false,
    "error": "Error description",
    "code": "ERROR_CODE"
}
```

### Testing Guidelines

#### Integration Test Structure
```python
# Add to test_integration.py
def test_new_feature():
    """Test new feature functionality"""
    # Setup
    test_user = "test_user"
    test_data = {"param": "value"}

    # Execute
    result = new_feature_function(test_user, test_data)

    # Verify
    assert result is not None
    assert result["success"] == True

    # Cleanup if needed
    cleanup_test_data()
```

### Performance Considerations

#### Caching Guidelines
- **Cache frequently accessed data** (user stats, availability)
- **Use appropriate timeouts** (5min for dynamic, 1hr for semi-static)
- **Implement cache invalidation** on data updates
- **Monitor cache hit rates** for optimization

#### Database Optimization
- **Batch write operations** when possible
- **Use data_persistence.save_multiple()** for bulk updates
- **Implement data archiving** for historical records
- **Monitor file sizes** and implement compression if needed

### Deployment Considerations

#### Environment Configuration
```bash
# Required environment variables
GOOGLE_CREDS_BASE64=<base64-encoded-credentials>
CENTRAL_CALENDAR_ID=<calendar-email>
SECRET_KEY=<strong-secret-key>
USERLIST=<user:pass,user2:pass2>

# Optional configuration
PERSIST_BASE=<custom-persistence-path>
FLASK_ENV=<development|production>
ADMIN_USERS=<admin1,admin2>
```

#### Health Checks
```python
# Add health check endpoints
@app.route('/health')
def health_check():
    """System health verification"""
    checks = {
        'database': data_persistence.verify_integrity(),
        'calendar': google_calendar_service.test_connection(),
        'cache': cache_manager.is_healthy()
    }

    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return jsonify({
        'status': 'healthy' if all_healthy else 'unhealthy',
        'checks': checks
    }), status_code
```

## Important Notes for Development

### Code Quality Requirements
- **Always use type hints** for function parameters and returns
- **Follow PEP 8** for code formatting and style
- **Add docstrings** for complex functions and classes
- **Use meaningful variable names** that describe their purpose
- **Implement proper error handling** with logging

### Security Requirements
- **Never commit credentials** or sensitive data
- **Always validate user input** before processing
- **Use parameterized queries** to prevent injection attacks
- **Implement rate limiting** for API endpoints
- **Log security-relevant events** for audit trails

### Performance Requirements
- **Profile critical code paths** for bottlenecks
- **Implement caching** for expensive operations
- **Use background tasks** for heavy processing
- **Monitor memory usage** and optimize data structures
- **Test under load** to ensure scalability

This comprehensive slot booking application represents a sophisticated business platform that can serve as the foundation for extensive enterprise applications and multi-program ecosystems.