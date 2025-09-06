// static/js/app.js - SOFORT hinzufügen:
document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ App JavaScript geladen');
    
    // Fix 1: Sidebar Toggle
    initSidebarToggle();
    
    // Fix 2: Form Handling
    initFormHandling();
    
    // Fix 3: Button States
    initButtonStates();
});

function initSidebarToggle() {
    const toggle = document.getElementById('sidebar-tab');
    const sidebar = document.querySelector('.sidebar');
    const body = document.body;
    
    if (toggle && sidebar) {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            
            sidebar.classList.toggle('active');
            body.classList.toggle('sidebar-open');
            
            console.log('✅ Sidebar toggled');
        });
        
        // Overlay click to close
        document.addEventListener('click', function(e) {
            if (e.target.classList.contains('sidebar-overlay')) {
                sidebar.classList.remove('active');
                body.classList.remove('sidebar-open');
            }
        });
    } else {
        console.error('❌ Sidebar elements not found');
    }
}

function initFormHandling() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            const submitBtn = form.querySelector('button[type="submit"]');
            
            if (submitBtn) {
                // Prevent double submission
                submitBtn.disabled = true;
                submitBtn.dataset.originalText = submitBtn.textContent;
                submitBtn.textContent = 'Wird verarbeitet...';
                
                // Re-enable after 3 seconds as fallback
                setTimeout(function() {
                    submitBtn.disabled = false;
                    submitBtn.textContent = submitBtn.dataset.originalText;
                }, 3000);
            }
            
            console.log('✅ Form submitted');
        });
    });
    
    console.log(`✅ ${forms.length} Forms initialized`);
}

function initButtonStates() {
    // Add click feedback to all buttons
    const buttons = document.querySelectorAll('button, .btn');
    
    buttons.forEach(function(button) {
        button.addEventListener('click', function() {
            if (!button.disabled) {
                button.style.transform = 'translateY(1px)';
                
                setTimeout(function() {
                    button.style.transform = '';
                }, 100);
            }
        });
    });
    
    console.log(`✅ ${buttons.length} Buttons initialized`);
}

// Global error handler
window.addEventListener('error', function(e) {
    console.error('❌ JavaScript Error:', e.error);
});