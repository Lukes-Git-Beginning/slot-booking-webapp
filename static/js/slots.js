// ============================================================================
// Slot Booking Webapp - Main JavaScript
// Extracted from index.html for better caching and maintainability
// ============================================================================

// ============================================================================
// ACHIEVEMENT SYSTEM
// ============================================================================
class AchievementSystem {
  constructor() {
    this.notificationQueue = [];
    this.isShowingNotification = false;
    this.pollingInterval = 60000;
    this.maxPollingInterval = 300000;
    this.lastActivity = Date.now();
    this.isPageVisible = true;
    this.consecutiveEmptyResponses = 0;
    this.init();
  }

  init() {
    this.setupPageVisibilityAPI();
    this.setupActivityTracking();
    this.checkForNewBadges();
    this.startSmartPolling();
  }

  setupPageVisibilityAPI() {
    document.addEventListener('visibilitychange', () => {
      this.isPageVisible = !document.hidden;
      if (this.isPageVisible) {
        this.resetPollingInterval();
      } else {
        this.slowDownPolling();
      }
    });
  }

  setupActivityTracking() {
    const activityEvents = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart'];
    let activityThrottle = null;

    const updateActivity = () => {
      this.lastActivity = Date.now();
      this.resetPollingInterval();
    };

    activityEvents.forEach(event => {
      document.addEventListener(event, () => {
        if (!activityThrottle) {
          activityThrottle = setTimeout(() => {
            updateActivity();
            activityThrottle = null;
          }, 5000);
        }
      }, { passive: true });
    });
  }

  startSmartPolling() {
    this.scheduleNextPoll();
  }

  scheduleNextPoll() {
    if (this.pollTimer) clearTimeout(this.pollTimer);

    const interval = this.calculatePollingInterval();
    this.pollTimer = setTimeout(() => {
      this.checkForNewBadges().then(() => {
        this.scheduleNextPoll();
      });
    }, interval);
  }

  calculatePollingInterval() {
    const now = Date.now();
    const timeSinceActivity = now - this.lastActivity;

    if (!this.isPageVisible) {
      return Math.min(this.maxPollingInterval, this.pollingInterval * 3);
    }

    if (timeSinceActivity < 120000) {
      return this.pollingInterval;
    }

    const inactiveMinutes = Math.floor(timeSinceActivity / 60000);
    const backoffFactor = Math.min(Math.pow(1.5, inactiveMinutes), 5);
    return Math.min(this.maxPollingInterval, this.pollingInterval * backoffFactor);
  }

  resetPollingInterval() {
    this.pollingInterval = 60000;
    this.consecutiveEmptyResponses = 0;
  }

  slowDownPolling() {
    this.pollingInterval = Math.min(this.maxPollingInterval, this.pollingInterval * 2);
  }

  async checkForNewBadges() {
    try {
      if (!this.isPageVisible && (Date.now() - this.lastActivity) > 600000) {
        return;
      }

      const response = await fetch('/api/user/badges');
      if (response.ok) {
        const data = await response.json();

        if (data.new_badges && data.new_badges.length > 0) {
          this.resetPollingInterval();
          this.consecutiveEmptyResponses = 0;

          for (const badge of data.new_badges) {
            this.showAchievementNotification(badge);
          }

          await fetch('/api/user/badges/mark-seen', { method: 'POST' });
        } else {
          this.consecutiveEmptyResponses++;
          if (this.consecutiveEmptyResponses >= 5) {
            this.pollingInterval = Math.min(this.maxPollingInterval, this.pollingInterval * 1.2);
          }
        }
      } else {
        this.slowDownPolling();
      }
    } catch (error) {
      console.error('Error checking for new badges:', error);
      this.slowDownPolling();
    }
  }

  showAchievementNotification(badge) {
    this.notificationQueue.push(badge);
    if (!this.isShowingNotification) {
      this.processNotificationQueue();
    }
  }

  async processNotificationQueue() {
    if (this.notificationQueue.length === 0) {
      this.isShowingNotification = false;
      return;
    }

    this.isShowingNotification = true;
    const badge = this.notificationQueue.shift();

    const notification = this.createNotificationElement(badge);
    document.getElementById('achievementContainer').appendChild(notification);

    if (badge.rarity === 'legendary' || badge.rarity === 'mythic') {
      this.createConfetti();
    }

    requestAnimationFrame(() => {
      notification.classList.add('show');
    });

    const hideTimeout = setTimeout(() => {
      this.hideNotification(notification);
    }, 5000);

    const closeBtn = notification.querySelector('.achievement-close');
    closeBtn.addEventListener('click', () => {
      clearTimeout(hideTimeout);
      this.hideNotification(notification);
    });

    setTimeout(() => {
      this.processNotificationQueue();
    }, 6000);
  }

  createNotificationElement(badge) {
    const notification = document.createElement('div');
    notification.className = `achievement-notification glass rounded-2xl overflow-hidden rarity-${badge.rarity}`;

    notification.innerHTML = `
      <div class="bg-gradient-to-r from-primary/20 to-secondary/20 p-4 flex items-center justify-between border-b border-white/10">
        <h4 class="font-bold text-primary uppercase text-sm">Achievement Unlocked!</h4>
        <button class="achievement-close btn btn-ghost btn-sm btn-circle">
          <i data-lucide="x" class="w-4 h-4"></i>
        </button>
      </div>
      <div class="p-6 text-center">
        <div class="achievement-badge rarity-${badge.rarity} mx-auto">
          ${badge.emoji}
        </div>
        <h3 class="text-xl font-bold text-white mb-2">${badge.name}</h3>
        <p class="text-sm text-white/70 mb-3">${badge.description}</p>
        <span class="badge badge-${badge.rarity === 'mythic' ? 'error' : badge.rarity === 'legendary' ? 'warning' : 'primary'}">
          ✨ ${badge.rarity.charAt(0).toUpperCase() + badge.rarity.slice(1)}
        </span>
      </div>
    `;

    // Re-initialize Lucide icons in the notification
    setTimeout(() => lucide.createIcons(), 100);

    return notification;
  }

  hideNotification(notification) {
    notification.classList.remove('show');
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 500);
  }

  createConfetti() {
    const colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#f9ca24', '#f0932b', '#eb4d4b', '#6c5ce7'];

    for (let i = 0; i < 50; i++) {
      const confetti = document.createElement('div');
      confetti.className = 'confetti';
      confetti.style.left = Math.random() * 100 + '%';
      confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
      confetti.style.top = '-10px';

      document.body.appendChild(confetti);

      setTimeout(() => {
        if (confetti.parentNode) {
          confetti.parentNode.removeChild(confetti);
        }
      }, 3000);
    }
  }
}

// ============================================================================
// CSP-COMPLIANT WRAPPER FUNCTIONS FOR DATA-ACTION ATTRIBUTES
// ============================================================================

// Modal helpers
window.closeModal = function(e, modalId) {
  const modal = document.getElementById(modalId);
  if (modal && modal.close) modal.close();
};

// Quick action wrappers for index.html
window.quickActionToggleSidebar = function(e) {
  toggleSidebarInternal();
  document.getElementById('quickActionsModal').close();
};

window.quickActionNavigate = function(e, url) {
  document.getElementById('quickActionsModal').close();
  window.location.href = url;
};

window.quickActionDay = function(e, direction) {
  document.getElementById('quickActionsModal').close();
  if (window.currentDateStr) {
    window.navigateDay(direction, window.currentDateStr);
  }
};

// Expose slot functions to global scope for data-action
// Note: toggleSidebar is assigned after its definition below
window.expandAll = function(e) { expandAllSlots(); };
window.collapseAll = function(e) { collapseAllSlots(); };
window.jumpToEvening = function(e) { jumpToEveningSlot(); };
window.toggleSlot = function(e) {
  // Handle SVG elements: traverse up from ownerSVGElement if needed
  let element = e.target;
  if (element.ownerSVGElement) {
    element = element.ownerSVGElement;
  }

  // Find the slot-section ancestor
  const section = element.closest('.slot-section');
  if (section) {
    const header = section.querySelector('.slot-header');
    if (header) toggleSlotInternal(header);
  }
};

// Navigate to a specific week (for sidebar links)
window.navigateToWeek = function(e) {
  const target = e.target.closest('[data-action="navigateToWeek"]');
  if (target && target.dataset.url) {
    window.location.href = target.dataset.url;
  }
};

// Form submission wrapper
window.handleBookingSubmitForm = function(e) {
  e.preventDefault();
  const form = e.target.closest('form');
  if (handleBookingSubmit(form)) {
    form.submit();
  }
};

// ============================================================================
// SIDEBAR TOGGLE
// ============================================================================
let sidebarOpen = false;

function toggleSidebarInternal() {
  sidebarOpen = !sidebarOpen;
  const sidebar = document.getElementById('sidebar');
  const mainContent = document.getElementById('mainContent');
  const sidebarToggle = document.getElementById('sidebarToggle');

  if (sidebarOpen) {
    sidebar.classList.remove('-translate-x-full');
    sidebar.classList.remove('pointer-events-none');
    mainContent.classList.add('md:ml-80');
    sidebarToggle.classList.add('md:left-[21rem]');
  } else {
    sidebar.classList.add('-translate-x-full');
    sidebar.classList.add('pointer-events-none');
    mainContent.classList.remove('md:ml-80');
    sidebarToggle.classList.remove('md:left-[21rem]');
  }

  localStorage.setItem('sidebar-open', sidebarOpen);

  // Re-initialize Lucide icons
  setTimeout(() => lucide.createIcons(), 100);
}

// Expose to global scope
window.toggleSidebar = toggleSidebarInternal;

// Restore sidebar state
if (localStorage.getItem('sidebar-open') === 'true' && window.innerWidth >= 768) {
  toggleSidebarInternal();
}

// ============================================================================
// SLOT COLLAPSE/EXPAND
// ============================================================================
function toggleSlotInternal(header) {
  const section = header.parentElement;
  const content = section.querySelector('.slot-content');
  const isExpanded = section.classList.contains('expanded');

  if (isExpanded) {
    content.style.maxHeight = '0';
    content.classList.add('collapsed');
    section.classList.remove('expanded');
  } else {
    content.style.maxHeight = content.scrollHeight + 'px';
    content.classList.remove('collapsed');
    section.classList.add('expanded');
  }
}

function expandAllSlots() {
  document.querySelectorAll('.slot-section').forEach(section => {
    const content = section.querySelector('.slot-content');
    content.style.maxHeight = content.scrollHeight + 'px';
    content.classList.remove('collapsed');
    section.classList.add('expanded');
  });
}

function collapseAllSlots() {
  document.querySelectorAll('.slot-section').forEach(section => {
    const content = section.querySelector('.slot-content');
    content.style.maxHeight = '0';
    content.classList.add('collapsed');
    section.classList.remove('expanded');
  });
}

function jumpToEveningSlot() {
  const eveningSlot = document.querySelector('[data-hour="18:00"]');
  if (eveningSlot) {
    eveningSlot.scrollIntoView({ behavior: 'smooth', block: 'center' });
    const header = eveningSlot.querySelector('.slot-header');
    if (!eveningSlot.classList.contains('expanded')) {
      toggleSlotInternal(header);
    }
  }
}

// Collapse all on mobile by default
if (window.innerWidth < 768) {
  collapseAllSlots();
}

// ============================================================================
// BOOKING FORM HANDLING
// ============================================================================
function handleBookingSubmit(form) {
  const btn = form.querySelector('button[type="submit"]');
  const btnText = btn.querySelector('.button-text');
  const spinner = btn.querySelector('.loading');

  btn.disabled = true;
  btnText.classList.add('hidden');
  spinner.classList.remove('hidden');

  return true;
}

// ============================================================================
// NAVIGATION
// ============================================================================
// Note: navigateDay requires template variable injection - will be handled inline
window.navigateDay = function(direction, currentDateStr) {
  const currentDate = new Date(currentDateStr);
  currentDate.setDate(currentDate.getDate() + direction);

  // Skip weekends
  if (currentDate.getDay() === 0) {
    currentDate.setDate(currentDate.getDate() + (direction > 0 ? 1 : -2));
  } else if (currentDate.getDay() === 6) {
    currentDate.setDate(currentDate.getDate() + (direction > 0 ? 2 : -1));
  }

  const dateStr = currentDate.toISOString().split('T')[0];
  window.location.href = `/slots/day/${dateStr}`;
}

// ============================================================================
// LEVEL UP CHECK
// ============================================================================
window.checkForLevelUp = function() {
  fetch('/api/level/check-up')
    .then(response => response.json())
    .then(data => {
      if (data.level_up) {
        showLevelUpModal(data.level_up);
      }
    })
    .catch(error => console.error('Level up check error:', error));
}

function showLevelUpModal(levelUpData) {
  document.getElementById('oldLevel').textContent = levelUpData.old_level;
  document.getElementById('newLevel').textContent = levelUpData.new_level;
  document.getElementById('xpGained').textContent = levelUpData.xp_gained;

  document.getElementById('levelUpModal').showModal();

  // Confetti
  const colors = ['#fbbf24', '#ef4444', '#3b82f6', '#10b981', '#8b5cf6'];
  for (let i = 0; i < 100; i++) {
    const confetti = document.createElement('div');
    confetti.className = 'confetti';
    confetti.style.left = Math.random() * 100 + '%';
    confetti.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
    confetti.style.top = '-10px';
    document.body.appendChild(confetti);
    setTimeout(() => confetti.remove(), 3000);
  }

  // Re-initialize Lucide icons
  setTimeout(() => lucide.createIcons(), 100);
}

// ============================================================================
// KEYBOARD SHORTCUTS
// ============================================================================
// Note: scoreboardUrl needs to be injected from template
window.setupKeyboardShortcuts = function(scoreboardUrl) {
  document.addEventListener('keydown', function(e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') {
      return;
    }

    // Ctrl/Cmd + K - Quick Actions
    if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
      e.preventDefault();
      document.getElementById('quickActionsModal').showModal();
      return;
    }

    // Single key shortcuts
    switch(e.key.toLowerCase()) {
      case 's':
        e.preventDefault();
        toggleSidebarInternal();
        break;
      case 'm':
        e.preventDefault();
        window.location.href = "/slots/my-calendar";
        break;
      case 'p':
        e.preventDefault();
        window.location.href = scoreboardUrl;
        break;
      case 'e':
        e.preventDefault();
        jumpToEvening();
        break;
      case 'arrowright':
        e.preventDefault();
        if (window.currentDateStr) {
          window.navigateDay(1, window.currentDateStr);
        }
        break;
      case 'arrowleft':
        e.preventDefault();
        if (window.currentDateStr) {
          window.navigateDay(-1, window.currentDateStr);
        }
        break;
    }
  });
}

// ============================================================================
// INITIALIZE
// ============================================================================

// Direct event listener for sidebar toggle button
// Script loads at end of body, so DOM is already ready - execute immediately
;(function initSidebarToggle() {
  const sidebarToggleBtn = document.getElementById('sidebarToggle');
  if (sidebarToggleBtn) {
    console.log('✅ Sidebar toggle button found, attaching listener');
    sidebarToggleBtn.addEventListener('click', function(e) {
      e.preventDefault();
      e.stopPropagation();
      console.log('🔄 Sidebar toggle clicked');
      toggleSidebarInternal();
    });
  } else {
    console.error('❌ Sidebar toggle button #sidebarToggle not found!');
  }
})();

setTimeout(() => {
  lucide.createIcons();
}, 100);
