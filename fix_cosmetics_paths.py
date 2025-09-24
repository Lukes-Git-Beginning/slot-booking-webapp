#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cosmetics Path Fix - Korrigiere Pfade für Server-Struktur
"""

import os
import json

def fix_cosmetics_paths():
    """Fix cosmetics paths for server structure"""
    print("🔧 Fixing Cosmetics Paths...")

    # Old paths vs new paths
    path_mappings = [
        ("data/persistent/cosmetic_purchases.json", "persist/persistent/cosmetic_purchases.json"),
        ("data/persistent/active_cosmetics.json", "persist/persistent/active_cosmetics.json"),
    ]

    for old_path, new_path in path_mappings:
        print(f"Checking: {old_path} -> {new_path}")

        # Create new directory if needed
        new_dir = os.path.dirname(new_path)
        if not os.path.exists(new_dir):
            os.makedirs(new_dir, exist_ok=True)
            print(f"  Created directory: {new_dir}")

        # If old file exists but new doesn't, copy data
        if os.path.exists(old_path) and not os.path.exists(new_path):
            try:
                with open(old_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                with open(new_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                print(f"  ✓ Migrated: {old_path} -> {new_path}")

            except Exception as e:
                print(f"  ✗ Error migrating {old_path}: {e}")

        # If new file doesn't exist at all, create empty
        elif not os.path.exists(new_path):
            try:
                with open(new_path, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=2)
                print(f"  ✓ Created empty: {new_path}")
            except Exception as e:
                print(f"  ✗ Error creating {new_path}: {e}")

        else:
            print(f"  ✓ Already exists: {new_path}")

def update_cosmetics_shop():
    """Update cosmetics shop to use correct paths"""
    print("\n🔧 Updating Cosmetics Shop Paths...")

    cosmetics_file = "cosmetics_shop.py"
    if os.path.exists(cosmetics_file):
        try:
            with open(cosmetics_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Replace paths
            content = content.replace(
                'self.purchases_file = "data/persistent/cosmetic_purchases.json"',
                'self.purchases_file = "persist/persistent/cosmetic_purchases.json"'
            )
            content = content.replace(
                'self.active_cosmetics_file = "data/persistent/active_cosmetics.json"',
                'self.active_cosmetics_file = "persist/persistent/active_cosmetics.json"'
            )
            content = content.replace(
                'os.makedirs("data/persistent", exist_ok=True)',
                'os.makedirs("persist/persistent", exist_ok=True)'
            )

            with open(cosmetics_file, 'w', encoding='utf-8') as f:
                f.write(content)

            print(f"✓ Updated paths in {cosmetics_file}")

        except Exception as e:
            print(f"✗ Error updating {cosmetics_file}: {e}")

def test_cosmetics_loading():
    """Test if cosmetics can be loaded"""
    print("\n🧪 Testing Cosmetics Loading...")

    try:
        # Import cosmetics shop
        import sys
        sys.path.append(os.path.dirname(os.path.abspath(__file__)))

        from cosmetics_shop import cosmetics_shop

        # Test loading for a dummy user
        test_user = "test_user"
        cosmetics_data = cosmetics_shop.get_user_cosmetics(test_user)

        print(f"✓ Cosmetics loading works!")
        print(f"  Structure: {list(cosmetics_data.keys())}")

        # Test available items
        available_titles = cosmetics_shop.get_available_items(test_user, "titles")
        print(f"  Available titles: {len(available_titles)}")

        return True

    except Exception as e:
        print(f"✗ Cosmetics loading failed: {e}")
        return False

def create_theme_css():
    """Create CSS for theme application"""
    print("\n🎨 Creating Theme CSS...")

    css_content = """
/* Dynamic Theme System */
:root {
  /* Default theme */
  --theme-primary: #5ab1ff;
  --theme-secondary: #3d8bfd;
  --theme-accent: #ffd700;
}

/* Theme Classes */
.theme-sunset-vibes {
  --theme-primary: #ff6b35;
  --theme-secondary: #f7931e;
  --theme-accent: #ff9f43;
}

.theme-ocean-breeze {
  --theme-primary: #0066cc;
  --theme-secondary: #00aaff;
  --theme-accent: #33ccff;
}

.theme-forest-zen {
  --theme-primary: #2d5a27;
  --theme-secondary: #4a7c59;
  --theme-accent: #7fb069;
}

.theme-neon-cyber {
  --theme-primary: #ff00ff;
  --theme-secondary: #00ffff;
  --theme-accent: #ffff00;
}

.theme-royal-purple {
  --theme-primary: #663399;
  --theme-secondary: #9966cc;
  --theme-accent: #ffd700;
}

.theme-rainbow-explosion {
  --theme-primary: linear-gradient(45deg, #ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #4b0082, #9400d3);
  --theme-secondary: linear-gradient(45deg, #ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #4b0082, #9400d3);
  --theme-accent: linear-gradient(45deg, #ff0000, #ff7f00, #ffff00, #00ff00, #0000ff, #4b0082, #9400d3);
  animation: rainbow-pulse 3s ease-in-out infinite;
}

@keyframes rainbow-pulse {
  0%, 100% { filter: brightness(1); }
  50% { filter: brightness(1.2) saturate(1.3); }
}

/* Apply theme colors to elements */
body.themed {
  --accent: var(--theme-primary);
  --secondary: var(--theme-secondary);
}

.themed .action-btn:hover {
  border-color: var(--theme-primary);
  background: rgba(var(--theme-primary-rgb), 0.1);
}

.themed .player-row:hover {
  background: rgba(var(--theme-primary-rgb), 0.08);
}

.themed .level-number {
  background: linear-gradient(135deg, var(--theme-primary), var(--theme-secondary));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
"""

    css_path = "static/theme_system.css"
    try:
        with open(css_path, 'w', encoding='utf-8') as f:
            f.write(css_content)
        print(f"✓ Created theme CSS: {css_path}")
    except Exception as e:
        print(f"✗ Error creating theme CSS: {e}")

if __name__ == "__main__":
    print("🚀 Starting Cosmetics System Fix...")

    fix_cosmetics_paths()
    update_cosmetics_shop()
    create_theme_css()

    success = test_cosmetics_loading()

    print(f"\n{'✅ Cosmetics system fix completed successfully!' if success else '❌ Some issues remain - check logs above'}")