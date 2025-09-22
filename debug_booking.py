#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug script to test booking availability logic
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from app.services.booking_service import get_effective_availability, get_slot_status, load_availability

def debug_booking_availability():
    """Debug the booking availability for the problematic date"""

    # Test data
    date_str = "2025-09-29"  # Monday
    hour = "16:00"

    print(f"=== Debugging Booking Availability for {date_str} {hour} ===")

    # Step 1: Load availability data
    print("\n1. Loading availability data...")
    availability = load_availability()
    print(f"   Total entries in availability.json: {len(availability)}")

    # Step 2: Check effective availability
    print("\n2. Getting effective availability...")
    effective_beraters = get_effective_availability(date_str, hour)
    print(f"   Effective beraters: {effective_beraters}")
    print(f"   Berater count: {len(effective_beraters)}")

    # Step 3: Check slot status
    print("\n3. Getting slot status...")
    berater_count = len(effective_beraters)
    if berater_count > 0:
        slot_list, booked, total, freie_count, overbooked = get_slot_status(date_str, hour, berater_count)
        print(f"   Slot list: {len(slot_list)} events")
        print(f"   Booked: {booked}")
        print(f"   Total: {total}")
        print(f"   Free count: {freie_count}")
        print(f"   Overbooked: {overbooked}")

        # Step 4: Check booking conditions
        print("\n4. Checking booking conditions...")
        print(f"   berater_count == 0: {berater_count == 0}")
        print(f"   overbooked or freie_count <= 0: {overbooked or freie_count <= 0}")

        if berater_count == 0:
            print("   ❌ BOOKING BLOCKED: No consultants available")
        elif overbooked or freie_count <= 0:
            print("   ❌ BOOKING BLOCKED: Slot is full")
        else:
            print("   ✅ BOOKING ALLOWED: All conditions met")
    else:
        print("   ❌ BOOKING BLOCKED: No effective beraters found")

    # Step 5: Check raw availability data
    print("\n5. Raw availability data check...")
    key1 = f"{date_str} {hour}"
    key2_nested = date_str in availability and hour in availability[date_str]

    print(f"   Key '{key1}' exists: {key1 in availability}")
    if key1 in availability:
        print(f"   Value: {availability[key1]}")

    print(f"   Nested format exists: {key2_nested}")
    if key2_nested:
        print(f"   Value: {availability[date_str][hour]}")

if __name__ == "__main__":
    debug_booking_availability()