/**
 * CareerOS — Premium Main JS
 * Command palette, sidebar toggle, toast system
 */
document.addEventListener('DOMContentLoaded', () => {

    // ============================================
    // Mobile Sidebar Toggle
    // ============================================
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    const mobileBtn = document.getElementById('mobileMenuBtn');

    if (mobileBtn && sidebar && overlay) {
        mobileBtn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            overlay.classList.toggle('active');
        });
        overlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
        });
    }

    // ============================================
    // ⌘K Command Palette
    // ============================================
    const cmdOverlay = document.getElementById('cmdOverlay');
    const cmdInput = document.getElementById('cmdInput');
    const cmdResults = document.getElementById('cmdResults');
    const searchTrigger = document.getElementById('searchTrigger');
    let activeIndex = 0;

    const commands = [
        { group: 'Navigation', icon: 'fa-home', label: 'Dashboard', action: '/dashboard', shortcut: '⌘1' },
        { group: 'Navigation', icon: 'fa-route', label: 'Roadmaps', action: '/roadmap', shortcut: '⌘2' },
        { group: 'Navigation', icon: 'fa-columns', label: 'Applications', action: '/applications', shortcut: '⌘3' },
        { group: 'Navigation', icon: 'fa-code', label: 'Coding Analytics', action: '/coding', shortcut: '⌘4' },
        { group: 'Navigation', icon: 'fa-file-alt', label: 'Resume Analyzer', action: '/resume' },
        { group: 'Navigation', icon: 'fa-user-tie', label: 'Interviews', action: '/interviews' },
        { group: 'Navigation', icon: 'fa-robot', label: 'AI Assistant', action: '/assistant' },
        { group: 'Navigation', icon: 'fa-cog', label: 'Settings', action: '/settings' },
        { group: 'AI Actions', icon: 'fa-magic', label: 'Generate AI Roadmap', action: '/roadmap' },
        { group: 'AI Actions', icon: 'fa-file-upload', label: 'Analyze Resume', action: '/resume' },
        { group: 'AI Actions', icon: 'fa-play', label: 'Start Mock Interview', action: '/interviews' },
        { group: 'AI Actions', icon: 'fa-comment-dots', label: 'Chat with AI Tutor', action: '/assistant' },
        { group: 'Quick Actions', icon: 'fa-plus', label: 'Add Application', action: '/applications' },
        { group: 'Quick Actions', icon: 'fa-sync-alt', label: 'Sync LeetCode', action: '/coding' },
    ];

    function openCommandPalette() {
        if (!cmdOverlay) return;
        cmdOverlay.classList.add('active');
        if (cmdInput) {
            cmdInput.value = '';
            cmdInput.focus();
        }
        activeIndex = 0;
        renderResults('');
    }

    function closeCommandPalette() {
        if (!cmdOverlay) return;
        cmdOverlay.classList.remove('active');
    }

    function renderResults(query) {
        if (!cmdResults) return;
        const filtered = commands.filter(c =>
            c.label.toLowerCase().includes(query.toLowerCase())
        );

        // Group results
        const groups = {};
        filtered.forEach(c => {
            if (!groups[c.group]) groups[c.group] = [];
            groups[c.group].push(c);
        });

        let html = '';
        let idx = 0;
        Object.keys(groups).forEach(group => {
            html += `<div class="cmd-group-label">${group}</div>`;
            groups[group].forEach(c => {
                const isActive = idx === activeIndex ? 'active' : '';
                html += `<div class="cmd-item ${isActive}" data-action="${c.action}" data-idx="${idx}">
                    <i class="fas ${c.icon}"></i>
                    <span>${c.label}</span>
                    ${c.shortcut ? `<span class="cmd-shortcut">${c.shortcut}</span>` : ''}
                </div>`;
                idx++;
            });
        });

        if (filtered.length === 0) {
            html = `<div style="padding: 24px; text-align: center; color: var(--text-faint); font-size: 0.857rem;">No results found</div>`;
        }

        cmdResults.innerHTML = html;

        // Click handlers
        cmdResults.querySelectorAll('.cmd-item').forEach(item => {
            item.addEventListener('click', () => {
                window.location.href = item.dataset.action;
            });
            item.addEventListener('mouseenter', () => {
                activeIndex = parseInt(item.dataset.idx);
                updateActiveItem();
            });
        });
    }

    function updateActiveItem() {
        if (!cmdResults) return;
        const items = cmdResults.querySelectorAll('.cmd-item');
        items.forEach((item, i) => {
            item.classList.toggle('active', i === activeIndex);
        });
        // Scroll into view
        const active = cmdResults.querySelector('.cmd-item.active');
        if (active) active.scrollIntoView({ block: 'nearest' });
    }

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // ⌘K / Ctrl+K
        if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
            e.preventDefault();
            if (cmdOverlay && cmdOverlay.classList.contains('active')) {
                closeCommandPalette();
            } else {
                openCommandPalette();
            }
        }

        // Escape
        if (e.key === 'Escape') {
            closeCommandPalette();
        }

        // Arrow navigation inside palette
        if (cmdOverlay && cmdOverlay.classList.contains('active')) {
            const items = cmdResults ? cmdResults.querySelectorAll('.cmd-item') : [];
            if (e.key === 'ArrowDown') {
                e.preventDefault();
                activeIndex = Math.min(activeIndex + 1, items.length - 1);
                updateActiveItem();
            }
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                activeIndex = Math.max(activeIndex - 1, 0);
                updateActiveItem();
            }
            if (e.key === 'Enter' && items[activeIndex]) {
                e.preventDefault();
                window.location.href = items[activeIndex].dataset.action;
            }
        }
    });

    // Search trigger click
    if (searchTrigger) {
        searchTrigger.addEventListener('click', openCommandPalette);
    }

    // Input filtering
    if (cmdInput) {
        cmdInput.addEventListener('input', (e) => {
            activeIndex = 0;
            renderResults(e.target.value);
        });
    }

    // Close on overlay click
    if (cmdOverlay) {
        cmdOverlay.addEventListener('click', (e) => {
            if (e.target === cmdOverlay) closeCommandPalette();
        });
    }

    // ============================================
    // Toast System
    // ============================================
    window.showToast = (message, type = 'success') => {
        const toast = document.createElement('div');
        Object.assign(toast.style, {
            position: 'fixed',
            bottom: '20px',
            right: '20px',
            padding: '10px 16px',
            background: type === 'success' ? 'var(--surface-4)' : 'var(--danger-muted)',
            color: 'var(--text-main)',
            borderRadius: 'var(--radius-lg)',
            border: '1px solid var(--border-default)',
            boxShadow: 'var(--shadow-lg)',
            zIndex: '9999',
            fontSize: '0.857rem',
            fontFamily: 'var(--font-sans)',
            animation: 'fadeInUp 0.3s ease forwards'
        });
        toast.textContent = message;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transform = 'translateY(10px)';
            toast.style.transition = 'all 0.3s ease';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    };

    function notify(message, type = 'success') {
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
        } else {
            console.log(message);
        }
    }

    function appendMessage(container, role, text) {
        const row = document.createElement('div');
        row.className = role === 'user' ? 'flex gap-3 flex-row-reverse mb-4' : 'flex gap-3 mb-4';

        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.style.width = '28px';
        avatar.style.height = '28px';
        avatar.textContent = role === 'user' ? 'KS' : 'AI';
        if (role !== 'user') {
            avatar.style.background = 'var(--primary)';
            avatar.style.fontSize = '0.55rem';
        }

        const bubble = document.createElement('div');
        bubble.className = 'p-3 rounded-lg text-sm';
        bubble.style.maxWidth = '80%';
        bubble.style.background = role === 'user' ? 'var(--primary-muted)' : 'var(--surface-0)';
        if (role === 'user') {
            bubble.style.border = '1px solid rgba(47,129,247,0.3)';
        }
        bubble.textContent = text;

        row.append(avatar, bubble);
        container.appendChild(row);
        container.scrollTop = container.scrollHeight;
    }

    function sendAssistantMessage() {
        const input = document.getElementById('assistantInput');
        const thread = document.getElementById('assistantThread');
        if (!input || !thread) return;

        const message = input.value.trim();
        if (!message) {
            notify('Type a question for the assistant first.');
            input.focus();
            return;
        }

        appendMessage(thread, 'user', message);
        input.value = '';
        appendMessage(thread, 'assistant', 'Here is a focused next step: clarify the target role, identify the weakest topic, and practice one timed problem or answer before moving on.');
    }

    function sendInterviewResponse() {
        const input = document.getElementById('interviewInput');
        const thread = document.getElementById('interviewThread');
        if (!input || !thread) return;

        const message = input.value.trim();
        if (!message) {
            notify('Type an interview response first.');
            input.focus();
            return;
        }

        appendMessage(thread, 'user', message);
        input.value = '';
        appendMessage(thread, 'assistant', 'Good structure. Now add one concrete tradeoff, one scaling constraint, and the metric you would monitor in production.');
    }

    const applicationStatusLabels = {
        applied: 'Applied',
        oa: 'Online Assessment',
        interview: 'Interview',
        offer: 'Offer',
        rejected: 'Rejected'
    };
    let draggedApplicationCard = null;

    function escapeHtml(value) {
        return String(value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function formatApplicationDate(value) {
        if (!value) return '';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return value;
        return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
    }

    function setApplicationFormVisible(visible) {
        const formCard = document.getElementById('applicationFormCard');
        const firstInput = document.getElementById('applicationCompany');
        if (!formCard) return;

        formCard.hidden = !visible;
        if (visible && firstInput) firstInput.focus();
    }

    function applicationFormPayload(form) {
        const data = new FormData(form);
        const payload = {};

        data.forEach((value, key) => {
            const trimmed = String(value).trim();
            if (trimmed) payload[key] = trimmed;
        });

        if (!payload.status) payload.status = 'applied';
        return payload;
    }

    function applicationEmptyState(status) {
        const label = applicationStatusLabels[status] || 'Applications';
        return `<div class="kanban-placeholder">${label} applications appear here</div>`;
    }

    function updateApplicationCounts() {
        Object.keys(applicationStatusLabels).forEach(status => {
            const list = document.querySelector(`[data-application-list="${status}"]`);
            const count = document.querySelector(`[data-application-count="${status}"]`);
            if (!list || !count) return;
            count.textContent = String(list.querySelectorAll('.application-card').length);
            if (list.querySelectorAll('.application-card').length === 0) {
                list.innerHTML = applicationEmptyState(status);
            } else {
                list.querySelector('.kanban-placeholder')?.remove();
            }
        });
    }

    function applicationStatusOptions(selectedStatus) {
        return Object.entries(applicationStatusLabels).map(([value, label]) => {
            const selected = value === selectedStatus ? 'selected' : '';
            return `<option value="${value}" ${selected}>${label}</option>`;
        }).join('');
    }

    function renderApplicationCard(application) {
        const card = document.createElement('div');
        card.className = 'kanban-card application-card';
        card.draggable = true;
        card.dataset.applicationId = application.id;
        card.dataset.applicationStatus = application.status;

        const deadline = application.deadline ? `<span class="text-xs text-warning">${formatApplicationDate(application.deadline)}</span>` : '';
        const tag = application.tag ? `<span class="badge badge-neutral">${escapeHtml(application.tag)}</span>` : '';
        const source = application.source ? `<span class="text-xs text-faint">${escapeHtml(application.source)}</span>` : '';
        const notes = application.notes ? `<div class="text-xs text-faint mt-2">${escapeHtml(application.notes)}</div>` : '';

        card.innerHTML = `
            <div class="flex justify-between items-start mb-2">
                <h4 class="font-semibold text-sm">${escapeHtml(application.company)}</h4>
                ${deadline || `<span class="text-xs text-faint">saved</span>`}
            </div>
            <div class="text-xs text-muted mb-2">${escapeHtml(application.role)}</div>
            <div class="flex items-center gap-2 mb-3">
                ${tag}
                ${source}
            </div>
            ${notes}
            <div class="flex items-center gap-2 pt-3 mt-3 border-t">
                <select class="input-field" data-application-status-select style="height:30px;padding:4px 8px;font-size:0.7rem;">
                    ${applicationStatusOptions(application.status)}
                </select>
                <button class="icon-btn text-danger" type="button" data-application-delete aria-label="Delete application">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;

        setupApplicationCard(card);
        return card;
    }

    function setupApplicationCard(card) {
        card.addEventListener('dragstart', () => {
            draggedApplicationCard = card;
            card.style.opacity = '0.5';
        });

        card.addEventListener('dragend', () => {
            card.style.opacity = '1';
            draggedApplicationCard = null;
        });

        const statusSelect = card.querySelector('[data-application-status-select]');
        statusSelect?.addEventListener('change', async () => {
            await moveApplication(card, statusSelect.value);
        });

        const deleteButton = card.querySelector('[data-application-delete]');
        deleteButton?.addEventListener('click', async () => {
            const applicationId = card.dataset.applicationId;
            if (!applicationId) return;
            if (!confirm('Delete this application from CareerOS?')) return;

            try {
                await window.api.deleteApplication(applicationId);
                card.remove();
                updateApplicationCounts();
                notify('Application deleted.');
            } catch (error) {
                notify(error.message || 'Could not delete application.', 'error');
            }
        });
    }

    async function moveApplication(card, status) {
        const applicationId = card.dataset.applicationId;
        const currentStatus = card.dataset.applicationStatus;
        if (!applicationId || !status || status === currentStatus) return;

        const targetList = document.querySelector(`[data-application-list="${status}"]`);
        const previousList = document.querySelector(`[data-application-list="${currentStatus}"]`);
        if (!targetList) return;

        targetList.prepend(card);
        card.dataset.applicationStatus = status;
        updateApplicationCounts();

        try {
            await window.api.updateApplicationStatus(applicationId, status);
            notify(`Application moved to ${applicationStatusLabels[status]}.`);
        } catch (error) {
            previousList?.prepend(card);
            card.dataset.applicationStatus = currentStatus;
            const select = card.querySelector('[data-application-status-select]');
            if (select) select.value = currentStatus;
            updateApplicationCounts();
            notify(error.message || 'Could not update application.', 'error');
        }
    }

    function renderApplications(applications) {
        Object.keys(applicationStatusLabels).forEach(status => {
            const list = document.querySelector(`[data-application-list="${status}"]`);
            if (list) list.innerHTML = '';
        });

        applications.forEach(application => {
            const list = document.querySelector(`[data-application-list="${application.status}"]`);
            if (list) list.appendChild(renderApplicationCard(application));
        });

        updateApplicationCounts();
    }

    async function loadApplications() {
        const board = document.getElementById('applicationsBoard');
        if (!board || !window.api) return;

        try {
            const applications = await window.api.listApplications();
            renderApplications(applications);
        } catch (error) {
            Object.keys(applicationStatusLabels).forEach(status => {
                const list = document.querySelector(`[data-application-list="${status}"]`);
                if (list) list.innerHTML = `<div class="kanban-placeholder">PostgreSQL unavailable</div>`;
            });
            notify(error.message || 'Could not load applications.', 'error');
        }
    }

    function setupApplicationBoard() {
        const board = document.getElementById('applicationsBoard');
        const form = document.getElementById('applicationForm');
        if (!board) return;

        document.querySelectorAll('[data-application-status]').forEach(column => {
            column.addEventListener('dragover', (e) => {
                e.preventDefault();
            });

            column.addEventListener('drop', async (e) => {
                e.preventDefault();
                if (!draggedApplicationCard) return;
                await moveApplication(draggedApplicationCard, column.dataset.applicationStatus);
            });
        });

        form?.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitButton = form.querySelector('button[type="submit"]');
            const originalText = submitButton ? submitButton.innerHTML : '';
            if (submitButton) {
                submitButton.disabled = true;
                submitButton.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Saving...';
            }

            try {
                const application = await window.api.createApplication(applicationFormPayload(form));
                const list = document.querySelector(`[data-application-list="${application.status}"]`);
                list?.prepend(renderApplicationCard(application));
                form.reset();
                setApplicationFormVisible(false);
                updateApplicationCounts();
                notify('Application saved to PostgreSQL.');
            } catch (error) {
                notify(error.message || 'Could not save application.', 'error');
            } finally {
                if (submitButton) {
                    submitButton.disabled = false;
                    submitButton.innerHTML = originalText;
                }
            }
        });

        loadApplications();
    }

    function chooseFile(accept, successMessage) {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = accept;
        input.addEventListener('change', () => {
            if (input.files && input.files.length > 0) {
                notify(successMessage);
            }
            input.remove();
        });
        input.click();
    }

    document.addEventListener('submit', (e) => {
        const form = e.target.closest('form[data-action="save-settings"]');
        if (!form) return;

        e.preventDefault();
        const button = form.querySelector('button[type="submit"]');
        const originalText = button ? button.innerHTML : '';
        if (button) {
            button.disabled = true;
            button.innerHTML = '<i class="fas fa-circle-notch fa-spin"></i> Saving...';
        }

        setTimeout(() => {
            if (button) {
                button.disabled = false;
                button.innerHTML = originalText;
            }
            notify('Settings saved locally.');
        }, 500);
    });

    document.addEventListener('click', (e) => {
        const navigation = e.target.closest('[data-navigate]');
        if (navigation) {
            e.preventDefault();
            window.location.href = navigation.dataset.navigate;
            return;
        }

        const assistantPrompt = e.target.closest('[data-assistant-prompt]');
        if (assistantPrompt) {
            const input = document.getElementById('assistantInput');
            if (input) {
                input.value = assistantPrompt.dataset.assistantPrompt;
                input.focus();
            }
            return;
        }

        const settingsTab = e.target.closest('[data-settings-tab]');
        if (settingsTab) {
            document.querySelectorAll('[data-settings-tab]').forEach(button => {
                const active = button === settingsTab;
                button.classList.toggle('text-primary', active);
                button.classList.toggle('text-muted', !active);
                button.style.background = active ? 'var(--primary-muted)' : 'transparent';
            });
            notify(`${settingsTab.dataset.settingsTab} settings selected.`);
            return;
        }

        const themeOption = e.target.closest('[data-theme-option]');
        if (themeOption) {
            document.querySelectorAll('[data-theme-option]').forEach(button => {
                const active = button === themeOption;
                button.classList.toggle('text-main', active);
                button.classList.toggle('text-faint', !active);
                button.style.background = active ? 'var(--surface-4)' : 'transparent';
            });
            document.documentElement.dataset.theme = themeOption.dataset.themeOption.toLowerCase();
            notify(`${themeOption.dataset.themeOption} theme selected.`);
            return;
        }

        const actionEl = e.target.closest('[data-action]');
        if (!actionEl) return;

        const action = actionEl.dataset.action;
        if (actionEl.tagName === 'A') {
            e.preventDefault();
        }

        switch (action) {
            case 'password-reset':
                notify('Password reset instructions are ready for the entered email.');
                break;
            case 'social-login':
                notify(`${actionEl.dataset.provider} login is not connected in this local demo. Use the email form to continue.`);
                break;
            case 'coming-soon':
                notify(`${actionEl.dataset.label || 'This page'} is coming soon.`);
                break;
            case 'show-notifications':
                actionEl.querySelector('.notification-dot')?.remove();
                notify('No new notifications.');
                break;
            case 'assistant-send':
                sendAssistantMessage();
                break;
            case 'start-interview':
                document.getElementById('interviewTimer')?.replaceChildren(document.createTextNode('44:59'));
                notify('New mock interview started.');
                break;
            case 'interview-send':
                sendInterviewResponse();
                break;
            case 'mic-toggle': {
                const active = actionEl.getAttribute('aria-pressed') !== 'true';
                actionEl.setAttribute('aria-pressed', String(active));
                actionEl.style.background = active ? 'var(--danger-muted)' : '';
                notify(active ? 'Microphone practice mode enabled.' : 'Microphone practice mode disabled.');
                break;
            }
            case 'view-report':
                notify(`${actionEl.dataset.report || 'Interview'} report opened in demo mode.`);
                break;
            case 'show-application-form':
                setApplicationFormVisible(true);
                break;
            case 'hide-application-form':
                setApplicationFormVisible(false);
                break;
            case 'regenerate-roadmap': {
                const progressText = document.getElementById('roadmapProgressText');
                const progressBar = document.getElementById('roadmapProgressBar');
                if (progressText && progressBar) {
                    progressText.textContent = '40%';
                    progressBar.style.width = '40%';
                }
                notify('Roadmap regenerated with updated progress.');
                break;
            }
            case 'upload-resume':
                chooseFile('.pdf,.doc,.docx', 'Resume selected for analysis.');
                break;
            case 'upload-avatar':
                chooseFile('image/*', 'Profile picture selected.');
                break;
            case 'remove-avatar':
                notify('Profile picture removed locally.');
                break;
            case 'delete-account':
                notify('Account deletion is disabled in this local demo.');
                break;
            case 'share-profile':
                if (navigator.clipboard) {
                    navigator.clipboard.writeText(window.location.href)
                        .then(() => notify('Profile link copied.'))
                        .catch(() => notify('Profile link is ready to share.'));
                } else {
                    notify('Profile link is ready to share.');
                }
                break;
            case 'view-achievements':
                notify('All visible achievements are shown.');
                break;
            default:
                notify('Action completed.');
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.target.id === 'assistantInput') {
            e.preventDefault();
            sendAssistantMessage();
        }
        if ((e.metaKey || e.ctrlKey) && e.key === 'Enter' && e.target.id === 'interviewInput') {
            e.preventDefault();
            sendInterviewResponse();
        }
    });

    document.querySelectorAll('.roadmap-task').forEach(task => {
        task.addEventListener('change', () => {
            const label = task.closest('label');
            const text = label ? label.querySelector('span') : null;
            if (text) {
                text.classList.toggle('line-through', task.checked);
                text.classList.toggle('text-muted', task.checked);
            }
            notify(task.checked ? 'Roadmap task marked complete.' : 'Roadmap task reopened.');
        });
    });

    setupApplicationBoard();
});
