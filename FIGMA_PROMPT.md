# 🎨 Figma AI Prompt - Business Tool Hub Design System

## 📋 Kontext für Figma AI

Kopiere diesen Prompt in Figma AI und lass das System dein Design-System erstellen:

---

## PROMPT START

```
Create a comprehensive design system for a "Business Tool Hub" web application with the following specifications:

### PROJECT OVERVIEW
- Name: Central Business Tool Hub
- Purpose: Multi-tool platform for consultants (Slot-Booking, T2-Closer-System, Analytics)
- Target Users: Business consultants, admins, coaches
- Platform: Web application (Desktop + Mobile responsive)
- Tech Stack: Tailwind CSS + DaisyUI

### DESIGN STYLE
- Modern glassmorphism aesthetic
- Professional yet approachable
- Dark mode primary (with light mode support)
- Smooth animations and transitions
- Clean, minimal clutter
- High contrast for readability

### COLOR PALETTE

**Primary Colors:**
- Primary Gold: #d4af6a (Warm, professional)
- Primary Dark: #c2ae7f (Hover states)
- Secondary Teal: #207487 (Accent color)
- Accent Navy: #294c5d (Secondary accent)
- Gray: #77726d (Muted text)

**Semantic Colors:**
- Success: #10b981 (Green - confirmations, success states)
- Warning: #f59e0b (Orange - warnings, important notices)
- Error: #ef4444 (Red - errors, destructive actions)
- Info: #3b82f6 (Blue - information, neutral alerts)

**Background (Dark Mode):**
- Primary BG: Linear gradient from #0f172a to #294c5d
- Card BG: rgba(18, 24, 32, 0.65) with backdrop-blur
- Overlay: rgba(255, 255, 255, 0.12) borders

**Background (Light Mode):**
- Primary BG: Linear gradient from #f5f5f4 to #e7e5e4
- Card BG: rgba(255, 255, 255, 0.90) with backdrop-blur
- Overlay: rgba(212, 175, 106, 0.25) borders

### TYPOGRAPHY

**Font Family:**
- Primary: Inter (Google Fonts)
- Fallback: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif

**Font Sizes:**
- H1: 48px / 3rem (Page titles)
- H2: 36px / 2.25rem (Section headers)
- H3: 24px / 1.5rem (Card titles)
- Body: 16px / 1rem (Default text)
- Small: 14px / 0.875rem (Captions, meta info)
- Tiny: 12px / 0.75rem (Badges, labels)

**Font Weights:**
- Light: 300 (Subtle text)
- Regular: 400 (Body text)
- Medium: 500 (Emphasized text)
- Semibold: 600 (Subheadings)
- Bold: 700 (Headings)
- Extrabold: 800 (Hero titles)

### SPACING SYSTEM

Use 8px grid system:
- xs: 4px
- sm: 8px
- md: 16px
- lg: 24px
- xl: 32px
- 2xl: 48px
- 3xl: 64px

### COMPONENT LIBRARY

Create the following components with Dark + Light mode variants:

#### 1. BUTTONS
- Primary Button (Gold gradient)
- Secondary Button (Teal)
- Ghost Button (Transparent)
- Outlined Button (Border only)
- Icon Button (Circle)
- Button sizes: Small, Medium, Large

States: Default, Hover, Active, Disabled, Loading

#### 2. CARDS
- Glass Card (Glassmorphism with backdrop-blur)
- Tool Card (With icon, title, description, status badge)
- Stat Card (For metrics/numbers)
- Profile Card (User info)

Variants: Default, Hover (subtle scale + shadow), Active

#### 3. NAVIGATION
- Top Navigation Bar (Sticky, glassmorphism)
  - Logo (left)
  - User dropdown (right)
  - Theme toggle (right)
- Sidebar Navigation (Collapsible for mobile)
- Breadcrumbs

#### 4. FORMS
- Text Input
- Select Dropdown
- Checkbox
- Radio Button
- Toggle Switch
- Date Picker
- Time Picker

States: Default, Focus, Error, Disabled, Success

#### 5. MODALS & DIALOGS
- Modal (Center overlay)
- Drawer (Slide from right)
- Alert Dialog (Confirmation)
- Toast Notification (Top-right corner)

#### 6. BADGES & TAGS
- Status Badge (Success, Warning, Error, Info)
- Role Badge (Admin, User, Coach)
- Count Badge (Notification count)

#### 7. DATA DISPLAY
- Table (Responsive, sortable headers)
- List (Vertical cards)
- Grid (2, 3, 4 columns responsive)
- Calendar Widget (Month view)

#### 8. FEEDBACK
- Toast Notifications (Success, Error, Warning, Info)
- Loading Spinner (Tailwind spin animation)
- Progress Bar
- Skeleton Loader (For loading states)

#### 9. NAVIGATION ELEMENTS
- Tab Bar (Horizontal tabs)
- Pagination
- Stepper (Multi-step forms)

### LAYOUT TEMPLATES

Design 5 complete page templates:

#### 1. DASHBOARD TEMPLATE
- Top navigation
- Welcome header with user greeting
- Grid of tool cards (3 columns desktop, 1 column mobile)
- Quick stats section
- Admin quick access (if admin)
- Footer

#### 2. LIST VIEW TEMPLATE
- Top navigation
- Page header with filters
- Table or card list
- Pagination
- Sidebar filters (collapsible on mobile)

#### 3. DETAIL VIEW TEMPLATE
- Top navigation
- Breadcrumbs
- Hero section with key info
- Content tabs
- Related items section
- Action buttons (sticky footer on mobile)

#### 4. CALENDAR VIEW TEMPLATE
- Top navigation
- Calendar widget (month/week view toggle)
- Time slot grid
- Booking modal
- Legend for slot statuses

#### 5. SETTINGS TEMPLATE
- Top navigation
- Sidebar menu (Collapsible on mobile)
- Settings content area
- Save/Cancel buttons (sticky footer)

### GLASSMORPHISM GUIDELINES

Dark Mode:
- Background: rgba(18, 24, 32, 0.65)
- Backdrop-filter: blur(20px) saturate(180%)
- Border: 1px solid rgba(255, 255, 255, 0.12)
- Shadow: Subtle glow on hover

Light Mode:
- Background: rgba(255, 255, 255, 0.90)
- Backdrop-filter: blur(20px) saturate(150%)
- Border: 1px solid rgba(212, 175, 106, 0.25)
- Shadow: 0 8px 32px rgba(120, 113, 108, 0.15)

### ICONOGRAPHY

Use Lucide Icons (https://lucide.dev):
- Consistent 24px size for primary icons
- 16px for inline icons
- Use stroke-width: 2px
- Colors: Match text color or use primary/secondary colors

Common icons:
- calendar-check (Slot-booking)
- users (User management)
- bar-chart (Analytics)
- settings (Settings)
- bell (Notifications)
- shield-check (Admin)
- arrow-right (CTAs)
- x (Close)
- check (Success)
- alert-triangle (Warning)

### ANIMATIONS & TRANSITIONS

- Page load: Fade in + slide up (AOS library)
- Card hover: Scale(1.02) + translateY(-4px) + shadow
- Button hover: Subtle scale(1.05)
- Modal open: Fade in + scale(0.95 → 1)
- Toast: Slide in from right
- Theme toggle: Smooth color transition (0.3s)

Timing:
- Fast: 0.15s (Micro-interactions)
- Medium: 0.3s (Modals, transitions)
- Slow: 0.6s (Page transitions)

### RESPONSIVE BREAKPOINTS

- Mobile: 320px - 640px (1 column)
- Tablet: 641px - 1024px (2 columns)
- Desktop: 1025px+ (3-4 columns)

Mobile-first approach:
- Stack cards vertically on mobile
- Hamburger menu for navigation
- Full-width modals on mobile
- Larger touch targets (min 44px)

### ACCESSIBILITY

- Color contrast: WCAG AA minimum (4.5:1 for text)
- Focus indicators: 2px solid ring with offset
- Keyboard navigation: Tab order, Enter/Space for buttons
- ARIA labels for icons and interactive elements
- Skip to content link
- Alt text for all images

### DARK MODE vs LIGHT MODE

Ensure all components have:
1. Dark mode variant (primary)
2. Light mode variant (softer colors, better contrast)
3. Smooth theme toggle animation
4. Persistent theme preference (localStorage)

Light mode adjustments:
- Reduce transparency on glass cards (0.90 instead of 0.65)
- Increase text contrast (near-black instead of white)
- Softer shadows
- Less vibrant accent colors

### EXPORT REQUIREMENTS

For each component:
1. Create in both Dark and Light modes
2. Include all states (default, hover, active, disabled)
3. Add annotations for spacing, colors, font sizes
4. Export as Figma components (reusable)
5. Generate CSS variables for Tailwind config

For templates:
1. Desktop version (1440px width)
2. Tablet version (768px width)
3. Mobile version (375px width)
4. Interactive prototype with transitions

### ADDITIONAL NOTES

- Use auto-layout for flexible components
- Create component variants for easy swapping
- Use Figma variables for colors and spacing
- Add comments/descriptions to complex components
- Organize in logical folders (Components, Templates, Colors, Typography)

### DELIVERABLES

1. Design System Overview (Single page with all colors, typography, spacing)
2. Component Library (All components in Dark + Light mode)
3. 5 Page Templates (Fully designed, responsive)
4. Interactive Prototype (Clickable demo)
5. Developer Handoff (CSS variables, Tailwind classes, spacing values)
```

## PROMPT END

---

## 🎯 Was du nach dem Figma AI-Run bekommst:

1. **Design System Page** mit allen Farben, Fonts, Spacing
2. **45+ Komponenten** (Buttons, Cards, Forms, etc.) in Dark + Light
3. **5 vollständige Templates** (Dashboard, List, Detail, Calendar, Settings)
4. **Interaktiver Prototyp** zum Klicken und Testen
5. **Dev Handoff** mit Tailwind-CSS-Klassen

---

## 📝 Zusätzliche Figma AI Prompts (Optional)

### Für spezifische Komponenten:

```
Create a glassmorphism slot booking card with:
- Time display (e.g., "09:00 - 09:30")
- Availability indicator (Green dot if available, Red if full)
- Consultant name
- Capacity indicator (e.g., "2/4 slots")
- Hover state with scale + shadow animation
- Dark and Light mode variants
```

```
Design a notification toast component with:
- Icon (left side, colored based on type)
- Title and message
- Close button (top right)
- Optional action buttons
- Auto-dismiss after 5 seconds
- Slide-in animation from right
- Types: Success (green), Error (red), Warning (orange), Info (blue)
```

---

## 🚀 Workflow nach Figma-Erstellung:

1. **Review** das generierte Design in Figma
2. **Anpassen** Farben/Abstände nach Bedarf
3. **Exportieren** CSS-Variablen aus Figma Dev Mode
4. **Implementieren** Components in HTML mit Tailwind-Klassen
5. **Testen** in allen Browsern & Geräten
6. **Iterieren** basierend auf User-Feedback

---

**Viel Erfolg mit Figma AI! 🎨**
