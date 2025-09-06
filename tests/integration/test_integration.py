#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bereinigte Integration Tests ohne externe Dependencies
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path

# Füge das Projektverzeichnis zum Python-Pfad hinzu
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_file_structure():
    """Test der kritischen Dateistruktur"""
    print("Testing File Structure...")
    
    required_files = [
        "static/availability.json",
        "main.py",
        "static/admin_style.css",
        "static/js/app.js"
    ]
    
    optional_files = [
        "static/scores.json",
        "static/champions.json", 
        "static/user_badges.json",
        "static/daily_user_stats.json"
    ]
    
    all_good = True
    
    # Kritische Dateien
    for file_path in required_files:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} FEHLT (kritisch)")
            all_good = False
    
    # Optionale Dateien
    for file_path in optional_files:
        if os.path.exists(file_path):
            print(f"  ✅ {file_path}")
        else:
            print(f"  ⚠️  {file_path} fehlt (wird erstellt)")
            # Versuche die Datei zu erstellen
            try:
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f, indent=2)
                print(f"  ✅ {file_path} erstellt")
            except Exception as e:
                print(f"  ❌ Konnte {file_path} nicht erstellen: {e}")
    
    return all_good

def test_availability_json():
    """Test der availability.json Struktur"""
    print("Testing Availability JSON...")
    
    try:
        with open("static/availability.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if not isinstance(data, dict):
            print("  ❌ availability.json ist kein Dictionary")
            return False
        
        print(f"  ✅ {len(data)} Zeitslots gefunden")
        
        # Prüfe Format der Schlüssel
        valid_keys = 0
        for key in data.keys():
            if len(key) == 16 and key[10] == ' ':  # "YYYY-MM-DD HH:MM"
                valid_keys += 1
        
        print(f"  ✅ {valid_keys}/{len(data)} Schlüssel haben korrektes Format")
        
        # Prüfe ob Berater-Listen vorhanden sind
        has_advisors = sum(1 for v in data.values() if isinstance(v, list) and len(v) > 0)
        print(f"  ✅ {has_advisors} Slots haben verfügbare Berater")
        
        return True
        
    except FileNotFoundError:
        print("  ❌ availability.json nicht gefunden")
        return False
    except json.JSONDecodeError:
        print("  ❌ availability.json ist korrupt")
        return False
    except Exception as e:
        print(f"  ❌ Fehler: {e}")
        return False

def test_basic_imports():
    """Test der grundlegenden Imports"""
    print("Testing Basic Imports...")
    
    import_tests = [
        ("datetime", "from datetime import datetime, timedelta"),
        ("json", "import json"),
        ("os", "import os"),
        ("pytz", "import pytz"),
    ]
    
    all_good = True
    for name, import_stmt in import_tests:
        try:
            exec(import_stmt)
            print(f"  ✅ {name}")
        except ImportError as e:
            print(f"  ❌ {name}: {e}")
            all_good = False
    
    return all_good

def test_app_imports():
    """Test der App-spezifischen Imports"""
    print("Testing App Imports...")
    
    try:
        # Versuche main.py zu importieren
        import main
        print("  ✅ main.py importiert")
        
        # Teste ob Flask App existiert
        if hasattr(main, 'app'):
            print("  ✅ Flask app gefunden")
        else:
            print("  ❌ Flask app nicht gefunden")
            return False
            
        return True
        
    except ImportError as e:
        print(f"  ❌ Konnte main.py nicht importieren: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Unerwarteter Fehler: {e}")
        return False

def test_css_exists():
    """Test ob CSS-Dateien existieren"""
    print("Testing CSS Files...")
    
    css_files = [
        "static/admin_style.css",
        "static/js/app.js"
    ]
    
    all_good = True
    for css_file in css_files:
        if os.path.exists(css_file):
            size = os.path.getsize(css_file)
            print(f"  ✅ {css_file} ({size} bytes)")
        else:
            print(f"  ❌ {css_file} fehlt")
            all_good = False
    
    return all_good

def test_data_directories():
    """Test der Datenverzeichnisse"""
    print("Testing Data Directories...")
    
    required_dirs = [
        "static",
        "data",
        "data/tracking",
        "data/persistent"
    ]
    
    for dir_path in required_dirs:
        if os.path.exists(dir_path) and os.path.isdir(dir_path):
            print(f"  ✅ {dir_path}/")
        else:
            print(f"  ⚠️  {dir_path}/ fehlt - erstelle...")
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"  ✅ {dir_path}/ erstellt")
            except Exception as e:
                print(f"  ❌ Konnte {dir_path}/ nicht erstellen: {e}")
                return False
    
    return True

def run_all_tests():
    """Führe alle Tests aus"""
    print("=" * 50)
    print("SLOT BOOKING WEBAPP - INTEGRATION TESTS")
    print("=" * 50)
    
    tests = [
        test_basic_imports,
        test_file_structure,
        test_data_directories,
        test_availability_json,
        test_css_exists,
        test_app_imports,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
            results.append(False)
        print()
    
    # Zusammenfassung
    print("=" * 50)
    print("TEST SUMMARY:")
    
    passed = sum(results)
    total = len(results)
    
    print(f"Passed: {passed}/{total}")
    print(f"Failed: {total - passed}/{total}")
    
    if passed == total:
        print("🎉 Alle Tests erfolgreich!")
        return 0
    else:
        print("⚠️ Einige Tests fehlgeschlagen")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())