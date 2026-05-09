/**
 * CareerOS — Premium Chart Configuration
 * Vercel/Stripe-inspired analytics visuals
 */
document.addEventListener('DOMContentLoaded', () => {
    // Global defaults
    Chart.defaults.color = '#8b949e';
    Chart.defaults.font.family = "'Inter', sans-serif";
    Chart.defaults.font.size = 11;
    Chart.defaults.animation.duration = 800;
    Chart.defaults.animation.easing = 'easeOutQuart';

    const tooltipConfig = {
        backgroundColor: '#161b22',
        titleColor: '#e6edf3',
        bodyColor: '#8b949e',
        borderColor: '#30363d',
        borderWidth: 1,
        padding: 10,
        displayColors: false,
        cornerRadius: 8,
        titleFont: { weight: '600', size: 12 },
        bodyFont: { size: 11 },
        caretSize: 0,
    };

    const gridConfig = {
        color: 'rgba(48,54,61,0.5)',
        drawBorder: false,
        lineWidth: 0.5,
    };

    // ---- Activity Chart (Dashboard) ----
    const activityEl = document.getElementById('activityChart');
    if (activityEl) {
        const ctx = activityEl.getContext('2d');
        const gradient = ctx.createLinearGradient(0, 0, 0, 260);
        gradient.addColorStop(0, 'rgba(47,129,247,0.15)');
        gradient.addColorStop(1, 'rgba(47,129,247,0.0)');

        new Chart(activityEl, {
            type: 'line',
            data: {
                labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                datasets: [{
                    label: 'Problems Solved',
                    data: [2, 5, 3, 8, 4, 1, 6],
                    borderColor: '#2f81f7',
                    borderWidth: 2,
                    backgroundColor: gradient,
                    tension: 0.4,
                    pointBackgroundColor: '#0d1117',
                    pointBorderColor: '#2f81f7',
                    pointBorderWidth: 2,
                    pointRadius: 0,
                    pointHoverRadius: 5,
                    fill: true,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                plugins: {
                    legend: { display: false },
                    tooltip: tooltipConfig,
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: gridConfig,
                        border: { display: false },
                        ticks: { padding: 8 },
                    },
                    x: {
                        grid: { display: false },
                        border: { display: false },
                        ticks: { padding: 8 },
                    }
                }
            }
        });
    }

    // ---- Skills Radar (Coding page) ----
    const skillsEl = document.getElementById('skillsChart');
    if (skillsEl) {
        new Chart(skillsEl, {
            type: 'radar',
            data: {
                labels: ['Arrays', 'Strings', 'Trees', 'Graphs', 'DP', 'Math'],
                datasets: [{
                    label: 'Proficiency',
                    data: [80, 90, 60, 40, 50, 70],
                    backgroundColor: 'rgba(47,129,247,0.08)',
                    borderColor: '#2f81f7',
                    pointBackgroundColor: '#2f81f7',
                    pointBorderColor: '#0d1117',
                    pointHoverBackgroundColor: '#0d1117',
                    pointHoverBorderColor: '#2f81f7',
                    borderWidth: 1.5,
                    pointRadius: 3,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: tooltipConfig,
                },
                scales: {
                    r: {
                        angleLines: { color: 'rgba(48,54,61,0.4)' },
                        grid: { color: 'rgba(48,54,61,0.3)' },
                        pointLabels: {
                            color: '#8b949e',
                            font: { size: 10, weight: '500' },
                        },
                        ticks: { display: false, max: 100, min: 0 },
                    }
                }
            }
        });
    }
});
