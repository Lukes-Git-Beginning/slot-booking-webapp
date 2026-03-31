/**
 * Finanzberatung Notifications - SSE Client for Real-Time Upload Notifications
 *
 * Works in two modes:
 * - Session detail: live feed cards + toast notifications (sessionId set)
 * - Global (any Hub page): toast notifications only (sessionId = null)
 *
 * Features:
 * - EventSource SSE connection with auto-reconnect (exponential backoff)
 * - Toast notifications (slide-in bottom-right, auto-dismiss 5s)
 * - Live feed document cards with file icon, size, timestamp, status
 * - Notification sound with localStorage toggle
 * - Connection status indicator
 * - Missed event fetch on reconnect via REST
 * - Double-connect guard
 */

/* exported FinanzNotifications */
var FinanzNotifications = (function() {
    'use strict';

    // Double-connect guard
    if (window._finanzNotificationsActive) {
        return window._FinanzNotificationsClass || function() {};
    }

    /**
     * @param {Object} options
     * @param {number|null} options.sessionId - Session ID for detail mode, null for global
     * @param {string} options.username - Current logged-in username
     * @param {HTMLElement|null} options.feedContainer - DOM element for live feed (detail only)
     */
    function FinanzNotifications(options) {
        options = options || {};
        this.sessionId = options.sessionId || null;
        this.username = options.username || '';
        this.feedContainer = options.feedContainer || null;
        this.soundEnabled = localStorage.getItem('finanz_sound') !== 'false';
        this.evtSource = null;
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
        this.lastEventId = null;
        this.reconnectTimer = null;
        this._statusEl = null;
        this._toastContainer = null;
        this._audioCtx = null;
    }

    /**
     * Connect to the SSE endpoint.
     */
    FinanzNotifications.prototype.connect = function() {
        // Double-connect guard
        if (window._finanzNotificationsActive) {
            return;
        }
        window._finanzNotificationsActive = true;

        var self = this;
        var url;

        if (this.sessionId) {
            url = '/finanzberatung/sse/stream/' + this.sessionId;
        } else {
            url = '/finanzberatung/sse/global';
        }

        try {
            this.evtSource = new EventSource(url);
        } catch (e) {
            window._finanzNotificationsActive = false;
            return;
        }

        this.evtSource.onopen = function() {
            self.reconnectDelay = 1000;
            self._updateStatus('connected');
        };

        // Listen for 'new_upload' events
        this.evtSource.addEventListener('new_upload', function(e) {
            try {
                var data = JSON.parse(e.data);
                self.handleEvent(data, e.lastEventId);
            } catch (err) {
                // Ignore parse errors
            }
        });

        // Generic message handler (fallback)
        this.evtSource.onmessage = function(e) {
            if (!e.data || e.data.trim() === '') return;
            try {
                var data = JSON.parse(e.data);
                if (data && data.original_filename) {
                    self.handleEvent(data, e.lastEventId);
                }
            } catch (err) {
                // Ignore
            }
        };

        this.evtSource.onerror = function() {
            self._updateStatus('disconnected');
            if (self.evtSource) {
                self.evtSource.close();
                self.evtSource = null;
            }
            window._finanzNotificationsActive = false;
            self.reconnect();
        };
    };

    /**
     * Disconnect and clean up.
     */
    FinanzNotifications.prototype.disconnect = function() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (this.evtSource) {
            this.evtSource.close();
            this.evtSource = null;
        }
        window._finanzNotificationsActive = false;
    };

    /**
     * Handle an incoming upload event.
     */
    FinanzNotifications.prototype.handleEvent = function(data, eventId) {
        if (eventId) {
            this.lastEventId = eventId;
        }

        this.showToast(data);

        if (this.feedContainer) {
            this.addToFeed(data);
        }

        this.playSound();
    };

    /**
     * Show a toast notification (slide-in bottom-right, auto-dismiss 5s).
     */
    FinanzNotifications.prototype.showToast = function(data) {
        var container = this._getToastContainer();
        if (!container) return;

        var filename = data.original_filename || 'Dokument';
        var customer = data.customer_name || 'Kunde';
        var sessionId = data.session_id;

        var toast = document.createElement('div');
        toast.className = 'alert shadow-lg border-l-4 border-primary bg-base-200 cursor-pointer animate-slide-in-right';
        toast.style.cssText = 'min-width: 320px; max-width: 420px; margin-bottom: 0.5rem;';

        toast.innerHTML =
            '<div class="flex items-center gap-3 w-full">' +
                '<div class="w-10 h-10 rounded-lg bg-gradient-to-br from-primary/20 to-secondary/20 flex items-center justify-center flex-shrink-0">' +
                    '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><line x1="10" y1="9" x2="8" y2="9"/></svg>' +
                '</div>' +
                '<div class="flex-1 min-w-0">' +
                    '<p class="text-sm font-bold truncate">Neues Dokument</p>' +
                    '<p class="text-xs opacity-70 truncate">' + _escapeHtml(filename) + ' von ' + _escapeHtml(customer) + '</p>' +
                '</div>' +
            '</div>';

        // Click navigates to session detail
        if (sessionId) {
            toast.addEventListener('click', function() {
                window.location.href = '/finanzberatung/sessions/' + sessionId;
            });
        }

        container.appendChild(toast);

        // Auto-dismiss after 5 seconds
        setTimeout(function() {
            toast.classList.remove('animate-slide-in-right');
            toast.classList.add('animate-slide-out-right');
            setTimeout(function() {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 5000);
    };

    /**
     * Add a document card to the live feed container (session detail only).
     */
    FinanzNotifications.prototype.addToFeed = function(data) {
        if (!this.feedContainer) return;

        // Remove "no uploads" placeholder if present
        var placeholder = this.feedContainer.querySelector('.text-center.py-4');
        if (placeholder) {
            placeholder.remove();
        }

        var card = document.createElement('div');
        card.className = 'flex items-center gap-2 text-sm py-1';
        card.style.cssText = 'animation: slideInFromTop 0.3s ease-out;';

        var fileSize = _formatFileSize(data.file_size);
        var now = new Date();
        var timeStr = ('0' + now.getHours()).slice(-2) + ':' + ('0' + now.getMinutes()).slice(-2);

        card.innerHTML =
            '<span style="opacity: 0.7;">' + _escapeHtml(timeStr) + '</span>' +
            '<span class="font-medium">' + _escapeHtml(data.original_filename || 'Dokument') + '</span>' +
            '<span class="text-xs" style="opacity: 0.6;">' + _escapeHtml(fileSize) + '</span>';

        // Prepend (newest first)
        if (this.feedContainer.firstChild) {
            var wrapper = this.feedContainer.querySelector('.space-y-2');
            if (wrapper) {
                wrapper.insertBefore(card, wrapper.firstChild);
            } else {
                var newWrapper = document.createElement('div');
                newWrapper.className = 'space-y-2';
                while (this.feedContainer.firstChild) {
                    newWrapper.appendChild(this.feedContainer.firstChild);
                }
                newWrapper.insertBefore(card, newWrapper.firstChild);
                this.feedContainer.appendChild(newWrapper);
            }
        } else {
            var wrap = document.createElement('div');
            wrap.className = 'space-y-2';
            wrap.appendChild(card);
            this.feedContainer.appendChild(wrap);
        }

        // Also add document to the Dokumente section
        this._addToDocumentsList(data);
    };

    /**
     * Add a new document card to the #documents-list section.
     */
    FinanzNotifications.prototype._addToDocumentsList = function(data) {
        var docList = document.getElementById('documents-list');
        if (!docList) return;

        // Remove empty-state placeholder
        var emptyPlaceholder = docList.querySelector('.text-center.py-6');
        if (emptyPlaceholder) {
            emptyPlaceholder.remove();
        }

        var fileSize = _formatFileSize(data.file_size);
        var mimeType = data.mime_type || '';
        var statusBadge = _getStatusBadge(data.status);

        // Determine file icon
        var iconName = 'file';
        var iconColor = 'text-base-content/40';
        if (mimeType.indexOf('pdf') !== -1) {
            iconName = 'file-text';
            iconColor = 'text-red-400';
        } else if (mimeType.indexOf('image') !== -1) {
            iconName = 'image';
            iconColor = 'text-blue-400';
        }

        var docCard = document.createElement('div');
        docCard.className = 'flex items-center gap-3 p-3 rounded-lg bg-base-200/50 hover:bg-base-200 transition-colors';
        docCard.style.cssText = 'animation: slideInFromTop 0.3s ease-out;';

        var now = new Date();
        var dateStr = ('0' + now.getDate()).slice(-2) + '.' +
            ('0' + (now.getMonth() + 1)).slice(-2) + '.' +
            now.getFullYear() + ' ' +
            ('0' + now.getHours()).slice(-2) + ':' +
            ('0' + now.getMinutes()).slice(-2);

        docCard.innerHTML =
            '<div class="w-10 h-10 rounded-lg bg-base-200 flex items-center justify-center flex-shrink-0">' +
                '<i data-lucide="' + iconName + '" class="w-5 h-5 ' + iconColor + '"></i>' +
            '</div>' +
            '<div class="flex-1 min-w-0">' +
                '<p class="text-sm font-semibold truncate">' + _escapeHtml(data.original_filename || 'Dokument') + '</p>' +
                '<p class="text-xs text-base-content/40">' + _escapeHtml(fileSize) + ' &middot; ' + _escapeHtml(dateStr) + '</p>' +
            '</div>' +
            '<div>' + statusBadge + '</div>';

        // Get or create wrapper
        var wrapper = docList.querySelector('.space-y-2');
        if (!wrapper) {
            wrapper = document.createElement('div');
            wrapper.className = 'space-y-2';
            docList.appendChild(wrapper);
        }
        wrapper.insertBefore(docCard, wrapper.firstChild);

        // Re-render lucide icons for new elements
        if (window.lucide) {
            window.lucide.createIcons();
        }

        // Update count badge
        var countBadge = docList.closest('.finanz-card')
            ? docList.closest('.finanz-card').querySelector('h2 .badge.badge-sm')
            : null;
        if (countBadge) {
            var current = parseInt(countBadge.textContent, 10) || 0;
            countBadge.textContent = current + 1;
        } else {
            // Create badge if it doesn't exist yet
            var heading = docList.closest('.finanz-card')
                ? docList.closest('.finanz-card').querySelector('h2')
                : null;
            if (heading && !heading.querySelector('.badge')) {
                var badge = document.createElement('span');
                badge.className = 'badge badge-sm badge-ghost';
                badge.textContent = '1';
                heading.appendChild(badge);
            }
        }
    };

    /**
     * Play a subtle notification sound.
     */
    FinanzNotifications.prototype.playSound = function() {
        if (!this.soundEnabled) return;

        try {
            if (!this._audioCtx) {
                var AC = window.AudioContext || window.webkitAudioContext;
                if (!AC) return;
                this._audioCtx = new AC();
            }

            var ctx = this._audioCtx;
            var osc = ctx.createOscillator();
            var gain = ctx.createGain();

            osc.connect(gain);
            gain.connect(ctx.destination);

            osc.type = 'sine';
            osc.frequency.setValueAtTime(880, ctx.currentTime);
            osc.frequency.setValueAtTime(1100, ctx.currentTime + 0.08);

            gain.gain.setValueAtTime(0.15, ctx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.2);

            osc.start(ctx.currentTime);
            osc.stop(ctx.currentTime + 0.2);
        } catch (e) {
            // Audio not available -- ignore
        }
    };

    /**
     * Toggle notification sound on/off. Persists to localStorage.
     */
    FinanzNotifications.prototype.toggleSound = function() {
        this.soundEnabled = !this.soundEnabled;
        localStorage.setItem('finanz_sound', this.soundEnabled ? 'true' : 'false');

        // Update toggle button state
        var btn = document.getElementById('finanz-sound-toggle');
        if (btn) {
            btn.classList.toggle('btn-active', this.soundEnabled);
            var icon = btn.querySelector('[data-sound-icon]');
            if (icon) {
                icon.setAttribute('data-lucide', this.soundEnabled ? 'volume-2' : 'volume-x');
                if (typeof lucide !== 'undefined') {
                    lucide.createIcons();
                }
            }
        }

        return this.soundEnabled;
    };

    /**
     * Reconnect with exponential backoff. Fetch missed events on reconnect.
     */
    FinanzNotifications.prototype.reconnect = function() {
        var self = this;

        this._updateStatus('reconnecting');

        this.reconnectTimer = setTimeout(function() {
            // Fetch missed events before reconnecting (session mode only)
            if (self.sessionId && self.lastEventId) {
                self._fetchMissedEvents();
            }

            self.connect();
        }, this.reconnectDelay);

        // Exponential backoff: 1s, 2s, 4s, 8s, 16s, max 30s
        this.reconnectDelay = Math.min(
            self.reconnectDelay * 2,
            self.maxReconnectDelay
        );
    };

    /**
     * Fetch missed events via REST endpoint on reconnect.
     */
    FinanzNotifications.prototype._fetchMissedEvents = function() {
        if (!this.sessionId || !this.lastEventId) return;

        var self = this;
        var url = '/finanzberatung/sessions/' + this.sessionId + '/documents?since=' + encodeURIComponent(this.lastEventId);

        fetch(url, { credentials: 'same-origin' })
            .then(function(resp) {
                if (!resp.ok) return [];
                return resp.json();
            })
            .then(function(docs) {
                if (!Array.isArray(docs)) return;
                docs.forEach(function(doc) {
                    if (self.feedContainer) {
                        self.addToFeed(doc);
                    }
                });
            })
            .catch(function() {
                // Ignore fetch errors during reconnect
            });
    };

    /**
     * Update the connection status indicator.
     */
    FinanzNotifications.prototype._updateStatus = function(state) {
        var el = this._getStatusElement();
        if (!el) return;

        var dot = el.querySelector('.status-dot');
        var text = el.querySelector('.status-text');

        if (!dot || !text) return;

        switch (state) {
            case 'connected':
                dot.className = 'status-dot w-2 h-2 rounded-full bg-success inline-block';
                text.textContent = 'Verbunden';
                text.className = 'status-text text-xs text-success';
                break;
            case 'disconnected':
                dot.className = 'status-dot w-2 h-2 rounded-full bg-error inline-block';
                text.textContent = 'Verbindung unterbrochen...';
                text.className = 'status-text text-xs text-error';
                break;
            case 'reconnecting':
                dot.className = 'status-dot w-2 h-2 rounded-full bg-warning inline-block animate-pulse';
                text.textContent = 'Verbinde...';
                text.className = 'status-text text-xs text-warning';
                break;
        }
    };

    /**
     * Get or create the toast container element.
     */
    FinanzNotifications.prototype._getToastContainer = function() {
        if (this._toastContainer) return this._toastContainer;

        this._toastContainer = document.getElementById('finanz-toast-container');
        if (!this._toastContainer) {
            this._toastContainer = document.createElement('div');
            this._toastContainer.id = 'finanz-toast-container';
            this._toastContainer.className = 'fixed bottom-4 right-4 z-50 flex flex-col items-end gap-2';
            document.body.appendChild(this._toastContainer);
        }
        return this._toastContainer;
    };

    /**
     * Get the connection status indicator element (only on session detail).
     */
    FinanzNotifications.prototype._getStatusElement = function() {
        if (this._statusEl) return this._statusEl;
        this._statusEl = document.getElementById('finanz-sse-status');
        return this._statusEl;
    };

    // =========================================================================
    // Helper functions
    // =========================================================================

    function _escapeHtml(str) {
        if (!str) return '';
        var div = document.createElement('div');
        div.appendChild(document.createTextNode(str));
        return div.innerHTML;
    }

    function _getFileIcon(mimeType) {
        mimeType = mimeType || '';
        if (mimeType.indexOf('pdf') !== -1) {
            return '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-red-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>';
        }
        if (mimeType.indexOf('image') !== -1) {
            return '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-blue-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>';
        }
        return '<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-gray-400" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>';
    }

    function _formatFileSize(bytes) {
        if (!bytes || bytes === 0) return '0 KB';
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    function _formatRelativeTime(isoStr) {
        if (!isoStr) return 'gerade eben';

        var then = new Date(isoStr);
        var now = new Date();
        var diffSec = Math.floor((now - then) / 1000);

        if (diffSec < 5) return 'gerade eben';
        if (diffSec < 60) return 'vor ' + diffSec + (diffSec === 1 ? ' Sekunde' : ' Sekunden');
        var mins = Math.floor(diffSec / 60);
        if (diffSec < 3600) return 'vor ' + mins + (mins === 1 ? ' Minute' : ' Minuten');
        var hrs = Math.floor(diffSec / 3600);
        if (diffSec < 86400) return 'vor ' + hrs + (hrs === 1 ? ' Stunde' : ' Stunden');
        return then.toLocaleDateString('de-DE');
    }

    function _getStatusBadge(status) {
        switch (status) {
            case 'uploaded':
                return '<span class="badge badge-ghost badge-xs">Hochgeladen</span>';
            case 'extracted':
                return '<span class="badge badge-info badge-xs">Extrahiert</span>';
            case 'classified':
                return '<span class="badge badge-success badge-xs">Klassifiziert</span>';
            case 'analyzed':
                return '<span class="badge badge-primary badge-xs">Analysiert</span>';
            case 'error':
                return '<span class="badge badge-error badge-xs">Fehler</span>';
            default:
                return '<span class="badge badge-ghost badge-xs">' + _escapeHtml(status || '') + '</span>';
        }
    }

    // Store reference for double-connect guard
    window._FinanzNotificationsClass = FinanzNotifications;

    return FinanzNotifications;
})();
