# 🚀 Tailwind + DaisyUI Quick Reference

## 📦 Meistgenutzte Klassen für Business Tool Hub

### 🎨 Glassmorphism Card

```html
<div class="glass rounded-2xl p-6 hover:bg-white/10 transition-all">
    <!-- Content -->
</div>
```

**Breakdown:**
- `glass` → Custom CSS-Klasse (backdrop-blur, rgba background)
- `rounded-2xl` → 16px border-radius
- `p-6` → 24px padding
- `hover:bg-white/10` → 10% white overlay on hover
- `transition-all` → Smooth transitions

---

### 🔘 Buttons

```html
<!-- Primary Button -->
<button class="btn btn-primary gap-2">
    <i data-lucide="save"></i>
    Speichern
</button>

<!-- Secondary Button -->
<button class="btn btn-secondary gap-2">
    <i data-lucide="arrow-right"></i>
    Weiter
</button>

<!-- Ghost Button -->
<button class="btn btn-ghost">Abbrechen</button>

<!-- Outlined Button -->
<button class="btn btn-outline">Details</button>

<!-- Icon-Only Button (Circle) -->
<button class="btn btn-circle btn-ghost">
    <i data-lucide="x" class="w-5 h-5"></i>
</button>

<!-- Button Sizes -->
<button class="btn btn-xs">Tiny</button>
<button class="btn btn-sm">Small</button>
<button class="btn btn-md">Medium (default)</button>
<button class="btn btn-lg">Large</button>
```

**DaisyUI Button Variants:**
- `btn-primary` → Gold gradient (#d4af6a)
- `btn-secondary` → Teal (#207487)
- `btn-accent` → Navy (#294c5d)
- `btn-success` → Green (#10b981)
- `btn-warning` → Orange (#f59e0b)
- `btn-error` → Red (#ef4444)
- `btn-ghost` → Transparent
- `btn-outline` → Border only

---

### 🏷️ Badges

```html
<!-- Success Badge -->
<div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-success/20 border border-success/40 text-success text-xs font-semibold">
    <span class="w-2 h-2 bg-success rounded-full animate-pulse"></span>
    Verfügbar
</div>

<!-- Warning Badge -->
<div class="badge badge-warning gap-2">
    <i data-lucide="alert-triangle" class="w-3 h-3"></i>
    Beta
</div>

<!-- Count Badge -->
<div class="badge badge-primary">3</div>
```

---

### 📋 Grid Layouts

```html
<!-- Responsive 3-Column Grid -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
    <div class="glass rounded-2xl p-6">Card 1</div>
    <div class="glass rounded-2xl p-6">Card 2</div>
    <div class="glass rounded-2xl p-6">Card 3</div>
</div>

<!-- 2-Column Sidebar Layout -->
<div class="grid grid-cols-1 md:grid-cols-4 gap-6">
    <aside class="md:col-span-1">
        <!-- Sidebar -->
    </aside>
    <main class="md:col-span-3">
        <!-- Main Content -->
    </main>
</div>
```

---

### 🔲 Flexbox

```html
<!-- Horizontal Layout (Space-between) -->
<div class="flex items-center justify-between gap-4">
    <div>Left Content</div>
    <div>Right Content</div>
</div>

<!-- Vertical Stack -->
<div class="flex flex-col gap-4">
    <div>Item 1</div>
    <div>Item 2</div>
</div>

<!-- Centered Content -->
<div class="flex items-center justify-center min-h-screen">
    <div>Centered Content</div>
</div>
```

---

### 🎭 Modals (DaisyUI)

```html
<!-- Modal Trigger Button -->
<button onclick="my_modal.showModal()" class="btn btn-primary">
    Open Modal
</button>

<!-- Modal -->
<dialog id="my_modal" class="modal">
    <div class="modal-box bg-base-200 max-w-2xl">
        <!-- Header -->
        <div class="flex items-center gap-3 mb-6">
            <div class="w-12 h-12 rounded-xl bg-gradient-to-br from-primary/20 to-secondary/20 flex items-center justify-center">
                <i data-lucide="info" class="w-6 h-6 text-primary"></i>
            </div>
            <h3 class="text-xl font-bold">Modal Title</h3>
        </div>

        <!-- Content -->
        <p class="text-white/70">Modal content here...</p>

        <!-- Actions -->
        <div class="modal-action">
            <button class="btn btn-primary">Confirm</button>
            <button class="btn btn-ghost" onclick="my_modal.close()">Cancel</button>
        </div>
    </div>

    <!-- Backdrop (click to close) -->
    <form method="dialog" class="modal-backdrop">
        <button>close</button>
    </form>
</dialog>
```

---

### 🔔 Toast Notifications

```html
<!-- Success Toast -->
<div class="alert alert-success shadow-lg">
    <div>
        <i data-lucide="check-circle" class="w-6 h-6"></i>
        <span>Erfolgreich gespeichert!</span>
    </div>
</div>

<!-- Error Toast -->
<div class="alert alert-error shadow-lg">
    <div>
        <i data-lucide="x-circle" class="w-6 h-6"></i>
        <span>Fehler beim Speichern!</span>
    </div>
</div>

<!-- Warning Toast -->
<div class="alert alert-warning shadow-lg">
    <div>
        <i data-lucide="alert-triangle" class="w-6 h-6"></i>
        <span>Achtung: Änderungen nicht gespeichert!</span>
    </div>
</div>
```

---

### 📝 Forms

```html
<!-- Text Input -->
<div class="form-control">
    <label class="label">
        <span class="label-text">Username</span>
    </label>
    <input type="text" placeholder="Enter username" class="input input-bordered" />
</div>

<!-- Select Dropdown -->
<div class="form-control">
    <label class="label">
        <span class="label-text">Choose option</span>
    </label>
    <select class="select select-bordered">
        <option>Option 1</option>
        <option>Option 2</option>
    </select>
</div>

<!-- Checkbox -->
<div class="form-control">
    <label class="label cursor-pointer gap-3">
        <span class="label-text">Remember me</span>
        <input type="checkbox" class="checkbox checkbox-primary" />
    </label>
</div>

<!-- Toggle Switch -->
<div class="form-control">
    <label class="label cursor-pointer gap-3">
        <span class="label-text">Enable notifications</span>
        <input type="checkbox" class="toggle toggle-primary" checked />
    </label>
</div>
```

---

### 🎯 Positioning

```html
<!-- Fixed Top Right (Theme Toggle) -->
<button class="fixed top-6 right-6 z-50 btn btn-circle">
    <i data-lucide="sun"></i>
</button>

<!-- Fixed Bottom Right (Support Chat) -->
<button class="fixed bottom-6 right-6 z-50 btn btn-circle btn-primary">
    <i data-lucide="message-circle"></i>
</button>

<!-- Sticky Navigation -->
<nav class="sticky top-0 z-50 glass backdrop-blur-xl">
    <!-- Navigation content -->
</nav>

<!-- Centered Overlay -->
<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
    <!-- Modal content -->
</div>
```

---

### 🌈 Colors & Opacity

```html
<!-- Text Colors -->
<p class="text-white">White text</p>
<p class="text-white/70">70% opacity white</p>
<p class="text-primary">Primary color (#d4af6a)</p>
<p class="text-secondary">Secondary color (#207487)</p>
<p class="text-success">Success (green)</p>
<p class="text-warning">Warning (orange)</p>
<p class="text-error">Error (red)</p>

<!-- Background Colors -->
<div class="bg-primary">Primary background</div>
<div class="bg-white/10">10% white overlay</div>
<div class="bg-success/20">20% success overlay</div>

<!-- Gradients -->
<div class="bg-gradient-to-br from-primary to-secondary">
    Gradient background
</div>
```

---

### 📐 Spacing

```html
<!-- Padding -->
<div class="p-4">16px padding (all sides)</div>
<div class="px-6 py-4">24px horizontal, 16px vertical</div>
<div class="pt-8 pb-4">32px top, 16px bottom</div>

<!-- Margin -->
<div class="m-4">16px margin (all sides)</div>
<div class="mb-8">32px bottom margin</div>
<div class="mx-auto">Auto horizontal margin (center)</div>

<!-- Gap (for Flex/Grid) -->
<div class="flex gap-4">16px gap between items</div>
<div class="grid gap-6">24px gap between grid items</div>
```

**Spacing Scale:**
- `1` = 4px
- `2` = 8px
- `3` = 12px
- `4` = 16px
- `5` = 20px
- `6` = 24px
- `8` = 32px
- `12` = 48px
- `16` = 64px

---

### 📏 Sizing

```html
<!-- Width -->
<div class="w-full">100% width</div>
<div class="w-1/2">50% width</div>
<div class="w-64">256px width (16rem)</div>
<div class="max-w-7xl">1280px max-width</div>

<!-- Height -->
<div class="h-screen">100vh height</div>
<div class="min-h-screen">Minimum 100vh</div>
<div class="h-64">256px height</div>

<!-- Icons -->
<i class="w-4 h-4">16px icon</i>
<i class="w-5 h-5">20px icon</i>
<i class="w-6 h-6">24px icon</i>
```

---

### ✨ Animations & Transitions

```html
<!-- Hover Scale -->
<div class="hover:scale-105 transition-transform">
    Scales 5% on hover
</div>

<!-- Hover Shadow -->
<div class="hover:shadow-2xl transition-shadow">
    Shadow on hover
</div>

<!-- Opacity Fade -->
<div class="opacity-0 hover:opacity-100 transition-opacity">
    Fades in on hover
</div>

<!-- Pulse (for badges) -->
<span class="animate-pulse">Pulsing element</span>

<!-- Spin (for loaders) -->
<i class="animate-spin">Loading...</i>

<!-- Smooth Transitions -->
<div class="transition-all duration-300 ease-out">
    Smooth transition (300ms)
</div>
```

---

### 📱 Responsive Design

```html
<!-- Hidden on Mobile, Visible on Desktop -->
<div class="hidden md:block">Desktop only</div>

<!-- Visible on Mobile, Hidden on Desktop -->
<div class="md:hidden">Mobile only</div>

<!-- Responsive Text Sizes -->
<h1 class="text-2xl md:text-4xl lg:text-5xl">
    32px mobile, 48px tablet, 60px desktop
</h1>

<!-- Responsive Grid Columns -->
<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
    <!-- 1 column mobile, 2 tablet, 4 desktop -->
</div>

<!-- Responsive Padding -->
<div class="p-4 md:p-8 lg:p-12">
    16px mobile, 32px tablet, 48px desktop
</div>
```

**Breakpoints:**
- `sm:` ≥ 640px
- `md:` ≥ 768px
- `lg:` ≥ 1024px
- `xl:` ≥ 1280px
- `2xl:` ≥ 1536px

---

### 🎨 Custom Hub Classes

```html
<!-- Glass Card (Custom) -->
<div class="glass rounded-2xl p-6">
    Glassmorphism card with backdrop-blur
</div>

<!-- Gradient Background (Custom) -->
<div class="gradient-bg">
    Animated gradient background
</div>

<!-- Glow Effect (Custom) -->
<button class="glow-primary">
    Button with glow effect
</button>

<!-- Theme Toggle -->
<button class="theme-toggle" @click="toggleTheme()">
    <i data-lucide="sun"></i>
</button>
```

---

### 🔧 Utility Combinations

```html
<!-- Centered Flex Container -->
<div class="flex items-center justify-center min-h-screen">
    Centered vertically and horizontally
</div>

<!-- Card with Icon Header -->
<div class="glass rounded-2xl p-6 hover:bg-white/10 transition-all">
    <div class="flex items-center gap-3 mb-4">
        <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-secondary flex items-center justify-center">
            <i data-lucide="calendar" class="w-5 h-5 text-white"></i>
        </div>
        <h3 class="text-xl font-bold">Card Title</h3>
    </div>
    <p class="text-white/70">Card content</p>
</div>

<!-- Responsive Container -->
<div class="container mx-auto px-4 py-8 max-w-7xl">
    Content with max-width and auto margins
</div>
```

---

### 🎯 AOS (Animate On Scroll) Attributes

```html
<!-- Fade Up -->
<div data-aos="fade-up">Fades in from bottom</div>

<!-- Fade Down -->
<div data-aos="fade-down">Fades in from top</div>

<!-- Zoom In -->
<div data-aos="zoom-in">Zooms in</div>

<!-- Delayed Animation -->
<div data-aos="fade-up" data-aos-delay="200">
    Delayed 200ms
</div>

<!-- Custom Duration -->
<div data-aos="fade-up" data-aos-duration="800">
    800ms animation
</div>
```

---

## 📚 Cheat Sheet Summary

| Task | Tailwind Class |
|------|---------------|
| Glass Card | `glass rounded-2xl p-6` |
| Primary Button | `btn btn-primary` |
| Success Badge | `badge badge-success` |
| 3-Col Grid | `grid grid-cols-1 md:grid-cols-3 gap-6` |
| Center Flex | `flex items-center justify-center` |
| Full Width | `w-full` |
| Max Width Container | `max-w-7xl mx-auto` |
| Hide on Mobile | `hidden md:block` |
| Hover Scale | `hover:scale-105 transition-transform` |
| Gradient BG | `bg-gradient-to-br from-primary to-secondary` |

---

## 🔗 Helpful Resources

- **Tailwind Docs:** https://tailwindcss.com/docs
- **DaisyUI Components:** https://daisyui.com/components/
- **Lucide Icons:** https://lucide.dev/icons/
- **AOS Library:** https://michalsnik.github.io/aos/

---

**Happy Coding! 🚀**
