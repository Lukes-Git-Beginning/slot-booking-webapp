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

        window.addEventListener('resize', () => this.resizeCanvas());

        // Start animation loop
        this.animate();

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
        document.addEventListener('click', (e) => {
            for (let i = 0; i < 8; i++) {
                this.createSparkle(e.clientX, e.clientY);
            }
        });
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
        document.addEventListener('achievement-unlocked', (e) => {
            this.triggerConfetti(window.innerWidth / 2, window.innerHeight / 2);
        });

        // Also trigger on booking success
        document.addEventListener('booking-success', (e) => {
            this.triggerConfetti(window.innerWidth / 2, window.innerHeight / 2);
        });
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
    }

    // ===== SCREEN SHAKE EFFECT =====
    enableScreenShake() {
        document.addEventListener('achievement-unlocked', () => {
            this.triggerScreenShake();
        });
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

        document.addEventListener('keydown', () => {
            // Play subtle click sound (simplified for demo)
            const audio = new Audio();
            audio.volume = 0.1;
            // In production, load actual sound files
        });
    }

    // ===== BOOKING FANFARE =====
    enableBookingFanfare() {
        document.addEventListener('booking-success', () => {
            this.playFanfare();
        });
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
    animate() {
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
                this.particles.splice(i, 1);
            }
        }

        requestAnimationFrame(() => this.animate());
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
