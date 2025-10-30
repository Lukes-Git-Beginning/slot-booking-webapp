/**
 * Cosmetics Effects System
 * Implementiert alle visuellen und akustischen Effekte aus dem Shop
 */

class CosmeticsEffects {
    constructor() {
        this.activeEffects = [];
        this.canvas = null;
        this.ctx = null;
        this.particles = [];
        this.animationFrameId = null;
        this.isAnimating = false;
        this.lastFrameTime = 0;
        this.targetFPS = 30; // Limit to 30 FPS instead of 60
        this.frameInterval = 1000 / this.targetFPS;
        this.eventListeners = []; // Track listeners for cleanup
        this.init();
    }

    init() {
        // Create canvas for particle effects
        this.canvas = document.createElement('canvas');
        this.canvas.id = 'cosmetics-canvas';
        this.canvas.style.position = 'fixed';
        this.canvas.style.top = '0';
        this.canvas.style.left = '0';
        this.canvas.style.width = '100%';
        this.canvas.style.height = '100%';
        this.canvas.style.pointerEvents = 'none';
        this.canvas.style.zIndex = '9999';
        document.body.appendChild(this.canvas);

        this.ctx = this.canvas.getContext('2d');
        this.resizeCanvas();

        // Debounce resize events
        let resizeTimeout;
        const resizeHandler = () => {
            clearTimeout(resizeTimeout);
            resizeTimeout = setTimeout(() => this.resizeCanvas(), 150);
        };
        window.addEventListener('resize', resizeHandler);
        this.eventListeners.push({ target: window, type: 'resize', handler: resizeHandler });

        // Load user's active effects from backend
        this.loadActiveEffects();
    }

    resizeCanvas() {
        this.canvas.width = window.innerWidth;
        this.canvas.height = window.innerHeight;
    }

    async loadActiveEffects() {
        try {
            const response = await fetch('/api/cosmetics/active-effects');
            const data = await response.json();
            if (data.success) {
                this.activeEffects = data.effects || [];
                this.activateEffects();
            }
        } catch (error) {
            console.log('No active effects loaded');
        }
    }

    activateEffects() {
        this.activeEffects.forEach(effectId => {
            switch(effectId) {
                case 'sparkle_trail':
                    this.enableSparkleTrail();
                    break;
                case 'confetti_explosion':
                    this.enableConfettiExplosion();
                    break;
                case 'screen_shake':
                    this.enableScreenShake();
                    break;
                case 'keyboard_sounds':
                    this.enableKeyboardSounds();
                    break;
                case 'booking_fanfare':
                    this.enableBookingFanfare();
                    break;
            }
        });
    }

    // ===== SPARKLE TRAIL EFFECT =====
    enableSparkleTrail() {
        const clickHandler = (e) => {
            for (let i = 0; i < 8; i++) {
                this.createSparkle(e.clientX, e.clientY);
            }
            this.startAnimation(); // Start animation only when particles are created
        };
        document.addEventListener('click', clickHandler);
        this.eventListeners.push({ target: document, type: 'click', handler: clickHandler });
    }

    createSparkle(x, y) {
        const sparkle = {
            x: x + (Math.random() - 0.5) * 30,
            y: y + (Math.random() - 0.5) * 30,
            size: Math.random() * 4 + 2,
            speedX: (Math.random() - 0.5) * 3,
            speedY: (Math.random() - 0.5) * 3 - 1,
            life: 1,
            decay: 0.02,
            color: `hsl(${Math.random() * 60 + 30}, 100%, 70%)` // Gold sparkles
        };
        this.particles.push(sparkle);
    }

    // ===== CONFETTI EXPLOSION EFFECT =====
    enableConfettiExplosion() {
        // Listen for achievement events
        const achievementHandler = (e) => {
            this.triggerConfetti(window.innerWidth / 2, window.innerHeight / 2);
        };
        document.addEventListener('achievement-unlocked', achievementHandler);
        this.eventListeners.push({ target: document, type: 'achievement-unlocked', handler: achievementHandler });

        // Also trigger on booking success
        const bookingHandler = (e) => {
            this.triggerConfetti(window.innerWidth / 2, window.innerHeight / 2);
        };
        document.addEventListener('booking-success', bookingHandler);
        this.eventListeners.push({ target: document, type: 'booking-success', handler: bookingHandler });
    }

    triggerConfetti(x, y) {
        const colors = ['#d4af6a', '#207487', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

        for (let i = 0; i < 50; i++) {
            const angle = (Math.PI * 2 * i) / 50;
            const speed = Math.random() * 5 + 3;

            this.particles.push({
                x: x,
                y: y,
                size: Math.random() * 8 + 4,
                speedX: Math.cos(angle) * speed,
                speedY: Math.sin(angle) * speed - 2,
                life: 1,
                decay: 0.015,
                color: colors[Math.floor(Math.random() * colors.length)],
                rotation: Math.random() * Math.PI * 2,
                rotationSpeed: (Math.random() - 0.5) * 0.2
            });
        }
        this.startAnimation(); // Start animation when confetti is triggered
    }

    // ===== SCREEN SHAKE EFFECT =====
    enableScreenShake() {
        const shakeHandler = () => {
            this.triggerScreenShake();
        };
        document.addEventListener('achievement-unlocked', shakeHandler);
        this.eventListeners.push({ target: document, type: 'achievement-unlocked', handler: shakeHandler });
    }

    triggerScreenShake() {
        const duration = 500;
        const intensity = 10;
        const start = Date.now();

        const shake = () => {
            const elapsed = Date.now() - start;
            const progress = elapsed / duration;

            if (progress < 1) {
                const currentIntensity = intensity * (1 - progress);
                const x = (Math.random() - 0.5) * currentIntensity;
                const y = (Math.random() - 0.5) * currentIntensity;

                document.body.style.transform = `translate(${x}px, ${y}px)`;
                requestAnimationFrame(shake);
            } else {
                document.body.style.transform = '';
            }
        };

        shake();
    }

    // ===== KEYBOARD SOUNDS =====
    enableKeyboardSounds() {
        const sounds = [
            'data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuFzvHalj0JHmm98OScTgwJUb...',
        ];

        const keyHandler = () => {
            // Play subtle click sound (simplified for demo)
            const audio = new Audio();
            audio.volume = 0.1;
            // In production, load actual sound files
        };
        document.addEventListener('keydown', keyHandler);
        this.eventListeners.push({ target: document, type: 'keydown', handler: keyHandler });
    }

    // ===== BOOKING FANFARE =====
    enableBookingFanfare() {
        const fanfareHandler = () => {
            this.playFanfare();
        };
        document.addEventListener('booking-success', fanfareHandler);
        this.eventListeners.push({ target: document, type: 'booking-success', handler: fanfareHandler });
    }

    playFanfare() {
        // Success sound effect (simplified)
        const audioContext = new (window.AudioContext || window.webkitAudioContext)();
        const oscillator = audioContext.createOscillator();
        const gainNode = audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(audioContext.destination);

        oscillator.frequency.value = 523.25; // C5
        gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

        oscillator.start(audioContext.currentTime);
        oscillator.stop(audioContext.currentTime + 0.5);
    }

    // ===== ANIMATION LOOP =====
    startAnimation() {
        if (!this.isAnimating && this.particles.length > 0) {
            this.isAnimating = true;
            this.lastFrameTime = performance.now();
            this.animate();
        }
    }

    stopAnimation() {
        if (this.animationFrameId) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
        this.isAnimating = false;
    }

    animate() {
        if (!this.isAnimating) return;

        const currentTime = performance.now();
        const deltaTime = currentTime - this.lastFrameTime;

        // FPS throttling - only render if enough time has passed
        if (deltaTime < this.frameInterval) {
            this.animationFrameId = requestAnimationFrame(() => this.animate());
            return;
        }

        this.lastFrameTime = currentTime - (deltaTime % this.frameInterval);

        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

        // Update and draw particles
        for (let i = this.particles.length - 1; i >= 0; i--) {
            const p = this.particles[i];

            // Update position
            p.x += p.speedX;
            p.y += p.speedY;
            p.speedY += 0.2; // Gravity

            // Update life
            p.life -= p.decay;

            // Rotate if applicable
            if (p.rotation !== undefined) {
                p.rotation += p.rotationSpeed;
            }

            // Draw particle
            if (p.life > 0) {
                this.ctx.save();
                this.ctx.globalAlpha = p.life;
                this.ctx.fillStyle = p.color;

                if (p.rotation !== undefined) {
                    // Confetti
                    this.ctx.translate(p.x, p.y);
                    this.ctx.rotate(p.rotation);
                    this.ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size);
                } else {
                    // Sparkle
                    this.ctx.beginPath();
                    this.ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
                    this.ctx.fill();
                }

                this.ctx.restore();
            } else {
                // Remove dead particles
                this.particles.splice(i, 1);
            }
        }

        // Stop animation when no particles left
        if (this.particles.length === 0) {
            this.stopAnimation();
        } else {
            this.animationFrameId = requestAnimationFrame(() => this.animate());
        }
    }

    // ===== CLEANUP =====
    cleanup() {
        // Remove all event listeners
        this.eventListeners.forEach(({ target, type, handler }) => {
            target.removeEventListener(type, handler);
        });
        this.eventListeners = [];

        // Stop animation
        this.stopAnimation();

        // Clear particles
        this.particles = [];

        // Remove canvas
        if (this.canvas && this.canvas.parentNode) {
            this.canvas.parentNode.removeChild(this.canvas);
        }
    }

    // ===== TRIGGER EVENTS (for testing) =====
    triggerAchievementUnlocked() {
        document.dispatchEvent(new CustomEvent('achievement-unlocked'));
    }

    triggerBookingSuccess() {
        document.dispatchEvent(new CustomEvent('booking-success'));
    }
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        window.cosmeticsEffects = new CosmeticsEffects();
    });
} else {
    window.cosmeticsEffects = new CosmeticsEffects();
}
