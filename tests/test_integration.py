#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test-Script für die Integration der verschiedenen Systeme
"""

import os
import sys
import json
from datetime import datetime

def test_color_mapping():
    """Test der zentralen Color-Definition"""
    print("🎨 Testing Color Mapping...")
    
    try:
        from color_mapping import get_outcome_from_color, get_potential_type, blocks_availability
        
        # Test verschiedene Farben
        test_colors = ["2", "7", "11", "6", "9"]
        
        for color in test_colors:
            outcome = get_outcome_from_color(color)
            potential = get_potential_type(color)
            blocks = blocks_availability(color)
            
            print(f"  Color {color}: Outcome={outcome}, Potential={potential}, Blocks={blocks}")
        
        print("✅ Color Mapping Test erfolgreich")
        return True
        
    except Exception as e:
        print(f"❌ Color Mapping Test fehlgeschlagen: {e}")
        return False

def test_achievement_system():
    """Test des Achievement Systems"""
    print("🏆 Testing Achievement System...")
    
    try:
        from achievement_system import achievement_system
        
        # Test Badge-Laden
        badges = achievement_system.load_badges()
        print(f"  Geladene Badges: {len(badges)} User")
        
        # Test Daily Stats
        stats = achievement_system.load_daily_stats()
        print(f"  Daily Stats: {len(stats)} User")
        
        print("✅ Achievement System Test erfolgreich")
        return True
        
    except Exception as e:
        print(f"❌ Achievement System Test fehlgeschlagen: {e}")
        return False

def test_tracking_system():
    """Test des Tracking Systems"""
    print("📊 Testing Tracking System...")
    
    try:
        from tracking_system import BookingTracker
        
        tracker = BookingTracker()
        
        # Prüfe ob Dateien existieren
        files = [
            tracker.bookings_file,
            tracker.outcomes_file,
            tracker.metrics_file,
            tracker.customer_file
        ]
        
        for file_path in files:
            if os.path.exists(file_path):
                print(f"  ✅ {os.path.basename(file_path)} existiert")
            else:
                print(f"  ⚠️ {os.path.basename(file_path)} fehlt")
        
        print("✅ Tracking System Test erfolgreich")
        return True
        
    except Exception as e:
        print(f"❌ Tracking System Test fehlgeschlagen: {e}")
        return False

def test_main_app():
    """Test der Hauptanwendung"""
    print("🌐 Testing Main App...")
    
    try:
        from slot_booking_webapp import app, add_points_to_user
        
        # Test Punkte-Funktion
        test_result = add_points_to_user("test_user", 5)
        print(f"  Punkte-Test: {len(test_result)} neue Badges")
        
        print("✅ Main App Test erfolgreich")
        return True
        
    except Exception as e:
        print(f"❌ Main App Test fehlgeschlagen: {e}")
        return False

def test_file_structure():
    """Test der Dateistruktur"""
    print("📁 Testing File Structure...")
    
    required_files = [
        "static/scores.json",
        "static/champions.json",
        "static/user_badges.json",
        "static/daily_user_stats.json",
        "data/tracking/bookings.jsonl",
        "data/tracking/outcomes.jsonl",
        "data/tracking/daily_metrics.json",
        "data/tracking/customer_profiles.json"
    ]
    
    all_good = True
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} fehlt")
            all_good = False
    
    if all_good:
        print("✅ File Structure Test erfolgreich")
    else:
        print("⚠️ File Structure Test - einige Dateien fehlen")
    
    return all_good

def main():
    """Hauptfunktion für alle Tests"""
    print("🚀 Starting Integration Tests...")
    print("=" * 50)
    
    tests = [
        test_color_mapping,
        test_achievement_system,
        test_tracking_system,
        test_main_app,
        test_file_structure
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")
            results.append(False)
        print()
    
    # Zusammenfassung
    print("=" * 50)
    print("📋 Test Summary:")
    
    passed = sum(results)
    total = len(results)
    
    print(f"  Passed: {passed}/{total}")
    print(f"  Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 Alle Tests erfolgreich!")
        return 0
    else:
        print("⚠️ Einige Tests fehlgeschlagen")
        return 1

if __name__ == "__main__":
    sys.exit(main())
