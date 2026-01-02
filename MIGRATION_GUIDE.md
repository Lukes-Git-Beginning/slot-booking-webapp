# 🎨 Tailwind + DaisyUI Migration Guide

## 📋 Übersicht

**Ziel:** Slot-Booking von Bootstrap 5.3.2 auf Tailwind + DaisyUI migrieren
**Status:** Hub/T2 bereits auf Tailwind ✅ | Slots auf Bootstrap ❌
**Aufwand:** 5-7 Tage (inkl. Testing & Feinschliff)

---

## 🚀 TEIL 1: Vorbereitungen

### 1.1 Template-Struktur verstehen

**Aktueller Stand:**
```
templates/
├── hub/
│   ├── base.html          ✅ Tailwind + DaisyUI (Master)
│   ├── dashboard.html     ✅ Tailwind + DaisyUI
│   ├── profile.html       ✅ Tailwind + DaisyUI
│   └── settings.html      ✅ Tailwind + DaisyUI
│
├── t2/
│   ├── base.html          ✅ Tailwind + DaisyUI
│   ├── draw_closer.html   ✅ Tailwind + DaisyUI
│   └── ...                ✅ (11 Templates)
│
└── slots/
    ├── base.html          ❌ Bootstrap 5.3.2 (MIGRIEREN!)
    ├── dashboard.html     ❌ Bootstrap 5.3.2 (MIGRIEREN!)
    ├── booking.html       ❌ Bootstrap 5.3.2 (MIGRIEREN!)
    └── day_view.html      ❌ Bootstrap 5.3.2 (MIGRIEREN!)
```

---

## 📦 TEIL 2: Was du kopieren musst

### 2.1 Base Template

**Von:** `templates/hub/base.html`
**Nach:** `templates/slots/base_new.html` (Backup-Strategie)

**Wichtige Komponenten:**
- ✅ Tailwind CDN + Config
- ✅ DaisyUI CSS
- ✅ Alpine.js
- ✅ Lucide Icons
- ✅ Glassmorphism-Styles
- ✅ Dark/Light Mode
- ✅ CSRF-Protection
- ✅ Session Timeout

---

### 2.2 Komponenten-Bibliothek erstellen

Erstelle wiederverwendbare Komponenten:

```bash
mkdir templates/components
```

#### **Button Component** (`templates/components/button.html`)

```html
{#
  Wiederverwendbarer Button mit Tailwind + DaisyUI

  Usage:
  {% include 'components/button.html' with
     text="Speichern",
     type="primary",
     icon="save",
     onclick="saveData()"
  %}
#}

<button
  class="btn btn-{{ type or 'primary' }} gap-2"
  {% if onclick %}onclick="{{ onclick }}"{% endif %}
  {% if disabled %}disabled{% endif %}>
  {% if icon %}
  <i data-lucide="{{ icon }}" class="w-4 h-4"></i>
  {% endif %}
  {{ text }}
</button>
```

**DaisyUI Button-Varianten:**
- `btn-primary` → Primäre Aktionen
- `btn-secondary` → Sekundäre Aktionen
- `btn-accent` → Hervorgehobene Aktionen
- `btn-success` → Erfolgsaktionen
- `btn-warning` → Warnungen
- `btn-error` → Löschaktionen
- `btn-ghost` → Transparente Buttons
- `btn-outline` → Outlined Buttons

---

#### **Card Component** (`templates/components/card.html`)

```html
{#
  Glass Card mit optionalem Icon

  Usage:
  {% include 'components/card.html' with
     title="Slot-Übersicht",
     icon="calendar",
     content="Dein Inhalt hier"
  %}
#}

<div class="glass rounded-2xl p-6 hover:bg-white/10 transition-all" data-aos="fade-up">
  {% if icon or title %}
  <div class="flex items-center gap-3 mb-4">
    {% if icon %}
    <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
      <i data-lucide="{{ icon }}" class="w-5 h-5 text-white"></i>
    </div>
    {% endif %}
    {% if title %}
    <h3 class="text-xl font-bold text-white">{{ title }}</h3>
    {% endif %}
  </div>
  {% endif %}

  <div class="text-white/80">
    {{ content | safe }}
  </div>
</div>
```

---

#### **Badge Component** (`templates/components/badge.html`)

```html
{#
  Status Badge

  Usage:
  {% include 'components/badge.html' with
     text="Verfügbar",
     type="success"
  %}
#}

<div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full
     {% if type == 'success' %}bg-success/20 border border-success/40 text-success
     {% elif type == 'warning' %}bg-warning/20 border border-warning/40 text-warning
     {% elif type == 'error' %}bg-error/20 border border-error/40 text-error
     {% else %}bg-primary/20 border border-primary/40 text-primary
     {% endif %}
     text-xs font-semibold">
  {% if type == 'success' %}
  <span class="w-2 h-2 bg-success rounded-full animate-pulse"></span>
  {% endif %}
  {{ text }}
</div>
```

---

## 🔄 TEIL 3: Bootstrap → Tailwind Mapping

### 3.1 Layout-Klassen

| Bootstrap 5 | Tailwind + DaisyUI |
|-------------|-------------------|
| `container` | `container mx-auto px-4` |
| `row` | `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4` |
| `col-md-6` | `md:col-span-2` |
| `d-flex` | `flex` |
| `justify-content-between` | `justify-between` |
| `align-items-center` | `items-center` |
| `gap-3` | `gap-3` |
| `mb-4` | `mb-4` |
| `p-3` | `p-3` |

### 3.2 Komponenten

| Bootstrap 5 | Tailwind + DaisyUI |
|-------------|-------------------|
| `<button class="btn btn-primary">` | `<button class="btn btn-primary">` (gleich!) |
| `<div class="card">` | `<div class="glass rounded-2xl p-6">` |
| `<div class="alert alert-success">` | `<div class="alert alert-success">` (DaisyUI) |
| `<span class="badge bg-success">` | `<span class="badge badge-success">` |
| `<div class="modal">` | `<dialog class="modal">` (DaisyUI) |

### 3.3 Farben

| Bootstrap 5 | Tailwind + DaisyUI |
|-------------|-------------------|
| `text-primary` | `text-primary` |
| `bg-success` | `bg-success` |
| `border-warning` | `border-warning` |
| `text-muted` | `text-white/60` (Dark) / `text-gray-600` (Light) |

---

## 🎯 TEIL 4: Migration-Workflow (Slot-Booking)

### 4.1 Backup erstellen

```bash
# Backup-Ordner erstellen
mkdir templates/slots_backup

# Alle Slot-Templates sichern
cp templates/slots/*.html templates/slots_backup/
```

### 4.2 Base Template migrieren

**Schritt 1:** Neue `slots/base.html` erstellen

```html
<!DOCTYPE html>
<html lang="de" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>{% block title %}Slot-Booking{% endblock %} • Business Tool Hub</title>

    <!-- Favicon -->
    <link rel="icon" type="image/png" href="{{ url_for('static', filename='favicon.png') }}">

    <!-- Tailwind CSS + DaisyUI (gleich wie Hub) -->
    <script src="{{ url_for('static', filename='tailwind.min.js') }}"></script>
    <link href="{{ url_for('static', filename='daisyui.min.css') }}" rel="stylesheet" type="text/css" />

    <!-- Lucide Icons -->
    <script src="{{ url_for('static', filename='lucide.js') }}"></script>

    <!-- AOS (Animate On Scroll) -->
    <link href="{{ url_for('static', filename='aos.css') }}" rel="stylesheet">
    <script src="{{ url_for('static', filename='aos.js') }}"></script>

    <!-- Alpine.js -->
    <script defer src="{{ url_for('static', filename='alpine.min.js') }}"></script>

    <!-- Custom Tailwind Config (GLEICH wie Hub!) -->
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        'primary': '#d4af6a',
                        'primary-dark': '#c2ae7f',
                        'secondary': '#207487',
                        'accent': '#294c5d',
                        'zfa-gray': '#77726d',
                    },
                    fontFamily: {
                        sans: ['Inter', 'system-ui', 'sans-serif'],
                    },
                },
            },
        }
    </script>

    <!-- Glassmorphism Styles (KOPIERT aus hub/base.html) -->
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Inter', sans-serif;
            overflow-x: hidden;
            transition: background-color 0.3s ease, color 0.3s ease;
        }

        /* Dark Theme (Default) */
        [data-theme="dark"] body {
            background: linear-gradient(to bottom right, #0f172a, #294c5d, #0f172a);
            color: white;
        }

        /* Light Theme */
        [data-theme="light"] body {
            background: linear-gradient(to bottom right, #f5f5f4, #e7e5e4, #fafaf9);
            color: #292524;
        }

        /* Glassmorphism - Dark */
        [data-theme="dark"] .glass {
            background: rgba(18, 24, 32, 0.65);
            backdrop-filter: blur(20px) saturate(180%);
            -webkit-backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid rgba(255, 255, 255, 0.12);
        }

        /* Glassmorphism - Light */
        [data-theme="light"] .glass {
            background: rgba(255, 255, 255, 0.90);
            backdrop-filter: blur(20px) saturate(150%);
            -webkit-backdrop-filter: blur(20px) saturate(150%);
            border: 1px solid rgba(212, 175, 106, 0.25);
            box-shadow: 0 8px 32px rgba(120, 113, 108, 0.15);
        }

        /* Text Colors - Light Theme */
        [data-theme="light"] .text-white {
            color: #1c1917 !important;
        }

        [data-theme="light"] .text-white\/70 {
            color: #57534e !important;
        }
    </style>

    {% block extra_css %}{% endblock %}
</head>
<body class="bg-gradient-to-br from-slate-900 via-[#294c5d] to-slate-900 text-white min-h-screen">

    <!-- Theme Toggle -->
    <button @click="toggleTheme()"
            class="fixed top-6 right-6 z-50 btn btn-circle btn-ghost hover:bg-white/10 theme-toggle">
        <i data-lucide="sun" class="w-5 h-5" x-show="$store.theme.current === 'dark'"></i>
        <i data-lucide="moon" class="w-5 h-5" x-show="$store.theme.current === 'light'"></i>
    </button>

    <!-- Back to Hub Button -->
    <a href="{{ url_for('hub.dashboard') }}"
       class="fixed top-6 left-6 z-50 glass px-6 py-3 rounded-xl flex items-center gap-3 hover:bg-white/10 transition-all group">
        <i data-lucide="arrow-left" class="w-5 h-5 group-hover:-translate-x-1 transition-transform"></i>
        <span class="hidden md:inline">Zurück zum Hub</span>
    </a>

    <!-- Main Container -->
    <div class="container mx-auto px-4 py-24 md:py-32">

        <!-- Header -->
        <header class="glass rounded-3xl p-8 md:p-12 mb-12 text-center" data-aos="fade-down">
            <div class="inline-flex items-center justify-center w-20 h-20 rounded-2xl bg-gradient-to-br from-primary to-secondary mb-6">
                <i data-lucide="calendar-check" class="w-10 h-10 text-white"></i>
            </div>
            <h1 class="text-4xl md:text-5xl font-bold mb-4">
                {% block header_title %}Slot Buchung{% endblock %}
            </h1>
            <p class="text-lg text-white/70">
                {% block header_subtitle %}Wähle deinen bevorzugten Zeitslot{% endblock %}
            </p>
        </header>

        <!-- Content -->
        <div data-aos="fade-up" data-aos-delay="100">
            {% block content %}{% endblock %}
        </div>

    </div>

    <!-- Footer -->
    <footer class="glass mt-24 py-8" data-aos="fade-up">
        <div class="container mx-auto px-4">
            <div class="flex flex-col md:flex-row justify-between items-center gap-4">
                <div>
                    <h5 class="font-bold text-lg mb-2">Slot-Booking</h5>
                    <p class="text-sm text-gray-400">Zentrum für Finanzielle Aufklärung</p>
                </div>
                <div class="flex items-center gap-6">
                    <a href="/health" class="flex items-center gap-2 text-gray-400 hover:text-primary transition-colors">
                        <i data-lucide="activity" class="w-4 h-4"></i>
                        <span>System Status</span>
                    </a>
                    <span class="text-sm text-gray-400">Version 3.3.6</span>
                </div>
            </div>
        </div>
    </footer>

    <!-- JavaScript Initialization -->
    <script>
        // Alpine.js Theme Store
        document.addEventListener('alpine:init', () => {
            Alpine.store('theme', {
                current: localStorage.getItem('theme') || 'dark',

                init() {
                    this.apply();
                },

                apply() {
                    document.documentElement.setAttribute('data-theme', this.current);
                    localStorage.setItem('theme', this.current);
                },

                toggle() {
                    this.current = this.current === 'dark' ? 'light' : 'dark';
                    this.apply();
                }
            });
        });

        // Global toggle function
        function toggleTheme() {
            Alpine.store('theme').toggle();
            setTimeout(() => lucide.createIcons(), 100);
        }

        // Initialize theme on page load
        window.addEventListener('DOMContentLoaded', () => {
            const savedTheme = localStorage.getItem('theme') || 'dark';
            document.documentElement.setAttribute('data-theme', savedTheme);
            Alpine.store('theme').current = savedTheme;
        });

        // Initialize Lucide Icons
        lucide.createIcons();

        // Initialize AOS
        AOS.init({
            duration: 800,
            easing: 'ease-out-cubic',
            once: true,
            offset: 50
        });
    </script>

    {% block extra_js %}{% endblock %}
</body>
</html>
```

---

### 4.3 Dashboard migrieren (Beispiel)

**Vorher (Bootstrap):**
```html
<div class="container mt-5">
  <div class="row">
    <div class="col-md-6">
      <div class="card">
        <div class="card-body">
          <h5 class="card-title">Slot-Übersicht</h5>
          <p class="card-text">Deine gebuchten Slots</p>
        </div>
      </div>
    </div>
  </div>
</div>
```

**Nachher (Tailwind + DaisyUI):**
```html
{% extends "slots/base.html" %}

{% block content %}
<div class="grid grid-cols-1 md:grid-cols-2 gap-6">
  <div class="glass rounded-2xl p-6 hover:bg-white/10 transition-all" data-aos="fade-up">
    <div class="flex items-center gap-3 mb-4">
      <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
        <i data-lucide="calendar" class="w-5 h-5 text-white"></i>
      </div>
      <h3 class="text-xl font-bold text-white">Slot-Übersicht</h3>
    </div>
    <p class="text-white/70">Deine gebuchten Slots</p>
  </div>
</div>
{% endblock %}
```

---

## 🧪 TEIL 5: Testing-Checkliste

Nach jeder Migration testen:

### 5.1 Funktional
- [ ] Slots werden korrekt angezeigt
- [ ] Buchung funktioniert
- [ ] Kalender-Integration funktioniert
- [ ] Punkte-System funktioniert
- [ ] Validierung funktioniert

### 5.2 UI/UX
- [ ] Dark Mode funktioniert
- [ ] Light Mode funktioniert
- [ ] Responsive auf Mobile
- [ ] Responsive auf Tablet
- [ ] Animationen laufen smooth
- [ ] Icons werden angezeigt
- [ ] Glassmorphism funktioniert
- [ ] Hover-Effekte funktionieren

### 5.3 Performance
- [ ] Seite lädt < 2s
- [ ] Keine Console-Errors
- [ ] Keine Layout-Shifts
- [ ] Smooth Scrolling

---

## 📋 TEIL 6: Schritt-für-Schritt Migrations-Plan

### Tag 1-2: Base Template + Dashboard
1. ✅ Neue `slots/base.html` erstellen (siehe oben)
2. ✅ `slots/dashboard.html` migrieren
3. ✅ Testen (Dark/Light Mode, Responsive)

### Tag 3-4: Booking & Day View
4. ✅ `slots/booking.html` migrieren
5. ✅ `slots/day_view.html` migrieren
6. ✅ Slot-Cards mit Glassmorphism stylen
7. ✅ Kalender-Integration testen

### Tag 5-6: Feinschliff & Polish
8. ✅ Animationen optimieren (AOS)
9. ✅ Hover-Effekte verfeinern
10. ✅ Performance-Testing
11. ✅ Cross-Browser-Testing (Chrome, Firefox, Safari, Edge)

### Tag 7: Deployment & Monitoring
12. ✅ Code-Review
13. ✅ Alte Bootstrap-Templates löschen
14. ✅ Deployment auf Server
15. ✅ User-Feedback sammeln

---

## 🎨 TEIL 7: Figma AI Prompt

(Siehe separate Datei: `FIGMA_PROMPT.md`)

---

## 📚 Ressourcen

- **Tailwind Docs:** https://tailwindcss.com/docs
- **DaisyUI Docs:** https://daisyui.com/components/
- **Lucide Icons:** https://lucide.dev/icons/
- **Alpine.js Docs:** https://alpinejs.dev/start-here
- **AOS Docs:** https://michalsnik.github.io/aos/

---

## 🚨 Wichtige Hinweise

1. **NIEMALS** beide Systeme gleichzeitig laden (Bootstrap + Tailwind)
2. **IMMER** Backup erstellen vor Migration
3. **TESTEN** in allen Browsern (Chrome, Firefox, Safari, Edge)
4. **RESPONSIVE** auf Mobile, Tablet, Desktop testen
5. **PERFORMANCE** mit Lighthouse checken (Target: 90+ Score)

---

**Viel Erfolg! 🚀**
