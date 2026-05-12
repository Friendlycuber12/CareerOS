/**
 * CareerOS — Auth Scripts
 * Handles social login simulation, form validation, password strength
 */

const PROFILE_KEY = 'careeros_profile';

function saveProfile(data) {
    const existing = JSON.parse(localStorage.getItem(PROFILE_KEY) || '{}');
    localStorage.setItem(PROFILE_KEY, JSON.stringify({ ...existing, ...data }));
}

document.addEventListener('DOMContentLoaded', () => {

    // ── Password Visibility Toggle ─────────────────────────────────────────
    document.querySelectorAll('.password-toggle-btn').forEach(btn => {
        btn.addEventListener('click', e => {
            e.preventDefault();
            const input = btn.closest('.password-field-wrapper').querySelector('input');
            const icon = btn.querySelector('i');
            if (input.type === 'password') {
                input.type = 'text';
                icon.className = 'fas fa-eye-slash';
            } else {
                input.type = 'password';
                icon.className = 'fas fa-eye';
            }
        });
    });

    // ── Password Strength Meter ────────────────────────────────────────────
    const passwordInput = document.getElementById('password');
    const strengthBar = document.getElementById('strengthBar');
    if (passwordInput && strengthBar) {
        passwordInput.addEventListener('input', () => {
            const val = passwordInput.value;
            let strength = 0;
            if (val.length >= 8) strength++;
            if (/[A-Z]/.test(val)) strength++;
            if (/[0-9]/.test(val)) strength++;
            if (/[^A-Za-z0-9]/.test(val)) strength++;
            const widths = ['0%', '25%', '50%', '75%', '100%'];
            const colors = ['', '#EF4444', '#F59E0B', '#3B82F6', '#22C55E'];
            strengthBar.style.width = widths[strength];
            strengthBar.style.backgroundColor = colors[strength];
        });
    }

    // ── Social Login (GitHub / Google) ─────────────────────────────────────
    function showSocialLoading(provider) {
        const overlay = document.getElementById('socialLoading');
        const title = document.getElementById('socialLoadingTitle');
        const msg = document.getElementById('socialLoadingMsg');
        if (!overlay) return;
        title.textContent = `Connecting to ${provider}...`;
        msg.textContent = `Please wait while we authenticate you with ${provider}`;
        overlay.classList.add('active');
    }

    function completeSocialLogin(provider, userData) {
        saveProfile({
            firstName: userData.firstName,
            lastName: userData.lastName,
            email: userData.email,
            avatar: provider.toLowerCase(),
            loginProvider: provider,
            loggedIn: true,
        });
        setTimeout(() => {
            window.location.href = '/dashboard';
        }, 1400);
    }

    function handleGitHubLogin() {
        showSocialLoading('GitHub');
        // In production: window.location.href = '/auth/github';
        // Demo: simulate successful auth
        setTimeout(() => {
            completeSocialLogin('GitHub', {
                firstName: 'Keshav',
                lastName: 'Soni',
                email: 'keshav@github.com',
            });
        }, 2000);
    }

    function handleGoogleLogin() {
        showSocialLoading('Google');
        // In production: window.location.href = '/auth/google';
        // Demo: simulate successful auth
        setTimeout(() => {
            completeSocialLogin('Google', {
                firstName: 'Keshav',
                lastName: 'Soni',
                email: 'keshav@gmail.com',
            });
        }, 2000);
    }

    const githubBtn = document.getElementById('githubLoginBtn');
    const googleBtn = document.getElementById('googleLoginBtn');
    if (githubBtn) githubBtn.addEventListener('click', handleGitHubLogin);
    if (googleBtn) googleBtn.addEventListener('click', handleGoogleLogin);

    // ── Login Form ─────────────────────────────────────────────────────────
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        loginForm.addEventListener('submit', e => {
            e.preventDefault();
            const btn = document.getElementById('loginSubmitBtn');
            const email = document.getElementById('email').value.trim();
            const name = email.split('@')[0];
            const parts = name.split(/[._-]/);
            const firstName = parts[0] ? parts[0].charAt(0).toUpperCase() + parts[0].slice(1) : 'User';
            const lastName = parts[1] ? parts[1].charAt(0).toUpperCase() + parts[1].slice(1) : '';

            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-circle-notch fa-spin" style="margin-right:8px;"></i> Signing in...';

            saveProfile({ firstName, lastName, email, loggedIn: true, loginProvider: 'email' });

            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 500);
        });
    }

    // ── Signup Form ────────────────────────────────────────────────────────
    const signupForm = document.getElementById('signupForm');
    if (signupForm) {
        signupForm.addEventListener('submit', e => {
            e.preventDefault();
            const btn = document.getElementById('signupSubmitBtn');
            const firstName = document.getElementById('firstName')?.value.trim() || '';
            const lastName = document.getElementById('lastName')?.value.trim() || '';
            const email = document.getElementById('email')?.value.trim() || '';
            const university = document.getElementById('university')?.value.trim() || '';

            btn.disabled = true;
            btn.innerHTML = '<i class="fas fa-circle-notch fa-spin" style="margin-right:8px;"></i> Creating account...';

            saveProfile({ firstName, lastName, email, university, loggedIn: true, loginProvider: 'email' });

            setTimeout(() => {
                window.location.href = '/dashboard';
            }, 600);
        });
    }
});
