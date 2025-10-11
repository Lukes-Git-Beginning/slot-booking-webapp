# T2 Availability System Deployment Guide

## Overview
Complete deployment guide for the T2 Availability and Interactive Calendar system.

## Files to Deploy

### 1. Backend Services (New)
```bash
scp -i ~/.ssh/server_key app/services/t2_calendar_parser.py root@91.98.192.233:/opt/business-hub/app/services/
scp -i ~/.ssh/server_key app/services/t2_availability_service.py root@91.98.192.233:/opt/business-hub/app/services/
```

### 2. Routes (Updated)
```bash
scp -i ~/.ssh/server_key app/routes/t2.py root@91.98.192.233:/opt/business-hub/app/routes/
```

### 3. Templates (Updated & New)
```bash
scp -i ~/.ssh/server_key templates/t2/booking.html root@91.98.192.233:/opt/business-hub/templates/t2/
scp -i ~/.ssh/server_key templates/t2/draw_closer.html root@91.98.192.233:/opt/business-hub/templates/t2/
scp -i ~/.ssh/server_key templates/t2/no_tickets.html root@91.98.192.233:/opt/business-hub/templates/t2/

# Deploy new calendar (will replace old calendar.html)
scp -i ~/.ssh/server_key templates/t2/calendar_new.html root@91.98.192.233:/opt/business-hub/templates/t2/calendar.html
```

### 4. Systemd Timer (New)
```bash
scp -i ~/.ssh/server_key deployment/t2-availability-scan.service root@91.98.192.233:/etc/systemd/system/
scp -i ~/.ssh/server_key deployment/t2-availability-scan.timer root@91.98.192.233:/etc/systemd/system/
```

## Deployment Steps

### Step 1: Deploy All Files
Run all SCP commands above to transfer files to server.

### Step 2: Set Up Systemd Timer
```bash
ssh -i ~/.ssh/server_key root@91.98.192.233 << 'EOF'
# Reload systemd to recognize new timer
systemctl daemon-reload

# Enable and start the timer
systemctl enable t2-availability-scan.timer
systemctl start t2-availability-scan.timer

# Verify timer is active
systemctl status t2-availability-scan.timer --no-pager
systemctl list-timers --all | grep t2-availability
EOF
```

### Step 3: Create Log Directory (if needed)
```bash
ssh -i ~/.ssh/server_key root@91.98.192.233 "touch /var/log/business-hub/t2-availability.log && chmod 644 /var/log/business-hub/t2-availability.log"
```

### Step 4: Run Initial Availability Scan
```bash
ssh -i ~/.ssh/server_key root@91.98.192.233 "cd /opt/business-hub && source venv/bin/activate && python -c 'from app.services.t2_availability_service import scan_all_closers; scan_all_closers()'"
```

### Step 5: Restart Application
```bash
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl restart business-hub"
```

### Step 6: Verify Deployment
```bash
# Check service status
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl status business-hub --no-pager"

# Check timer status
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl status t2-availability-scan.timer --no-pager"

# Check logs
ssh -i ~/.ssh/server_key root@91.98.192.233 "tail -50 /var/log/business-hub/t2-availability.log"
ssh -i ~/.ssh/server_key root@91.98.192.233 "tail -50 /var/log/business-hub/error.log | grep t2"

# Verify availability cache was created
ssh -i ~/.ssh/server_key root@91.98.192.233 "ls -lh /opt/business-hub/data/persistent/t2_availability.json"
```

## Testing

### 1. Test Booking Page
Open: http://91.98.192.233/t2/booking

**Expected:**
- Select a date
- See available time slots load (09:00, 11:00, 13:00, 15:00, 17:00, 19:00, 20:00)
- No errors in browser console

### 2. Test Calendar (Opener View)
Open: http://91.98.192.233/t2/calendar

**Expected:**
- See closer dropdown selector
- Calendar grid with green dots on available days
- Click day → modal shows free time slots
- "Kommende Termine" section shows next 5 bookings

### 3. Test Calendar (Closer View)
Login as closer (Jose, Alexander, David, Daniel, Christian, or Tim):
Open: http://91.98.192.233/t2/calendar

**Expected:**
- No closer dropdown (viewing own calendar)
- Calendar grid with yellow/purple dots for T2/T3 appointments
- Click day → modal shows appointment details (customer, type, time)
- "Kommende Termine" section shows next 5 appointments

### 4. Test Systemd Timer
```bash
# Manually trigger scan
ssh -i ~/.ssh/server_key root@91.98.192.233 "systemctl start t2-availability-scan.service"

# Check logs
ssh -i ~/.ssh/server_key root@91.98.192.233 "tail -50 /var/log/business-hub/t2-availability.log"

# Should see:
# "=== T2 Availability Scan Started ==="
# "Scanned Alexander: X days with data"
# "Scanned Christian: X days with data"
# ... (all 6 closers)
# "=== Scan Complete: 6 closers processed ==="
```

## Timer Schedule
- **Morning Scan:** 07:00 UTC (09:00 Berlin time)
- **Evening Scan:** 19:00 UTC (21:00 Berlin time)
- **Persistent:** Yes (runs missed scans if server was down)

## API Endpoints Added

### For All Users
- `GET /t2/api/availability-calendar/<closer_name>` - Available dates for 6 weeks
- `GET /t2/api/availability/<closer_name>/<date_str>` - Available slots for specific date

### For Closers Only
- `GET /t2/api/my-calendar-events/<date_str>` - Events for specific date
- `GET /t2/api/my-upcoming-events` - Next 5 upcoming events

### For Openers Only
- `GET /t2/api/my-bookings` - All bookings
- `GET /t2/api/my-upcoming-bookings` - Next 5 bookings

## Troubleshooting

### Timer Not Running
```bash
# Check timer status
systemctl status t2-availability-scan.timer

# Check service status
systemctl status t2-availability-scan.service

# View timer logs
journalctl -u t2-availability-scan.service -n 50
```

### No Availability Data
```bash
# Manually run scan
systemctl start t2-availability-scan.service

# Check if cache file exists
ls -lh /opt/business-hub/data/persistent/t2_availability.json

# View cache contents
cat /opt/business-hub/data/persistent/t2_availability.json | python -m json.tool | head -100
```

### Calendar Not Loading
```bash
# Check error logs
tail -100 /var/log/business-hub/error.log | grep t2

# Test API endpoints
curl http://91.98.192.233/t2/api/availability-calendar/Alexander
curl http://91.98.192.233/t2/api/availability/Alexander/2025-10-10
```

## Features Deployed

### ✅ Booking Page Enhancements
- Datepicker shows green dots for available days
- Real-time availability loading from cached data
- 2-hour time slots (09:00-22:00)
- Fixed CSS styling (Tailwind/DaisyUI)

### ✅ Interactive Calendar
- Dual mode (Opener/Closer views)
- Month navigation
- Colored dots (green=available, yellow=T2, purple=T3)
- Fullscreen modal for day details
- "Kommende Termine" section

### ✅ Automated Availability Scanning
- 6 weeks (42 days) ahead
- 2x daily scans (09:00 & 21:00 Berlin time)
- Intelligent slot detection (2-hour blocks)
- Conflict detection (no double bookings)
- Persistent caching

### ✅ Appointment Type Recognition
- Regex parsing (T2, T2.5, T2.75, T3, T3.5, etc.)
- Color mapping (yellow for T2.x, purple for T3.x)
- Customer name extraction

## Rollback Plan

If issues occur:

```bash
# Stop timer
systemctl stop t2-availability-scan.timer
systemctl disable t2-availability-scan.timer

# Restore old calendar.html (if backup exists)
ssh -i ~/.ssh/server_key root@91.98.192.233 "cp /opt/business-hub/templates/t2/calendar.html.backup /opt/business-hub/templates/t2/calendar.html"

# Restart service
systemctl restart business-hub
```

## Notes
- All 6 closer calendars are scanned individually
- Cache is stored in `data/persistent/t2_availability.json`
- Cache includes last_updated timestamp and scan duration
- CSS bugs fixed across all T2 templates (draw_closer, booking, no_tickets)
- All text in German as requested
