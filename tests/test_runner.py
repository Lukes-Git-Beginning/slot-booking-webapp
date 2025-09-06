#!/usr/bin/env python3
"""
Einfacher Test-Runner für alle Tests
"""

import sys
from pathlib import Path

# Füge Projektverzeichnis hinzu
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_all_tests():
    """Führe alle verfügbaren Tests aus"""
    test_modules = []
    
    # Integration Tests
    try:
        from tests.integration.test_integration import run_all_tests as integration_tests
        test_modules.append(("Integration Tests", integration_tests))
    except ImportError as e:
        print(f"⚠️ Could not import integration tests: {e}")
    
    # Historical Data Tests  
    try:
        from tests.data.test_historical import test_historical_data
        test_modules.append(("Historical Data Tests", test_historical_data))
    except ImportError as e:
        print(f"⚠️ Could not import historical tests: {e}")
    
    if not test_modules:
        print("❌ No test modules found!")
        return 1
    
    print("=" * 60)
    print("RUNNING ALL TESTS")
    print("=" * 60)
    
    all_passed = True
    for name, test_func in test_modules:
        print(f"\n🔄 Running {name}...")
        try:
            result = test_func()
            if result != 0:
                all_passed = False
        except Exception as e:
            print(f"❌ {name} crashed: {e}")
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 ALL TESTS PASSED")
        return 0
    else:
        print("❌ SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    sys.exit(run_all_tests())