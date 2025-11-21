#!/usr/bin/env python3
"""Test My Calendar data loading"""
import os
import sys

# Set environment
os.environ['DATABASE_URL'] = 'postgresql://business_hub_user:BizHub2025Secure@localhost/business_hub'
os.environ['USE_POSTGRES'] = 'true'

from app.routes.calendar import get_user_bookings

print("=" * 60)
print("MY CALENDAR DATA LOADING TEST")
print("=" * 60)

username = "christian.mast"
print(f"\nTesting get_user_bookings('{username}', days_back=60, days_forward=90)")

try:
    bookings = get_user_bookings(username, days_back=60, days_forward=90)

    print(f"\n✅ SUCCESS: Returned {len(bookings)} bookings")

    if bookings:
        print(f"\nFirst 5 bookings:")
        for i, b in enumerate(bookings[:5]):
            print(f"  {i+1}. {b.get('customer', 'N/A')} - {b.get('date', 'N/A')} at {b.get('time', 'N/A')}")
    else:
        print("\n⚠️ WARNING: No bookings returned!")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
