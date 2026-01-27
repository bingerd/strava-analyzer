// Strava Analyzer Dashboard - Multi-User with Authentication
// Handles login, token management, and activity visualizations

let activities = [];
let charts = {};
let currentAthleteId = null;
let authToken = null;

// DOM Elements
const loginForm = document.getElementById('loginForm');
const loginBtn = document.getElementById('loginBtn');
const loginError = document.getElementById('loginError');
const dashboardControls = document.getElementById('dashboardControls');
const dashboardHint = document.getElementById('dashboardHint');
const loadUsersBtn = document.getElementById('loadUsers');
const loadDataBtn = document.getElementById('loadData');
const logoutBtn = document.getElementById('logoutBtn');
const apiUrlInput = document.getElementById('apiUrl');
const usernameInput = document.getElementById('username');
const passwordInput = document.getElementById('password');
const userSelect = document.getElementById('userSelect');
const dashboardContent = document.getElementById('dashboardContent');
const dashboardError = document.getElementById('dashboardError');
const authStatus = document.getElementById('authStatus');

// Ensure URL has a protocol
function ensureProtocol(url) {
    url = url.trim().replace(/\/$/, '');
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
        return 'https://' + url;
    }
    return url;
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    // Set default API URL based on current location (works for both local and production)
    const defaultApiUrl = window.location.origin;
    apiUrlInput.value = defaultApiUrl;

    // Check for stored token
    const storedToken = localStorage.getItem('authToken');
    const storedApiUrl = localStorage.getItem('apiUrl');

    if (storedToken) {
        authToken = storedToken;
        if (storedApiUrl) apiUrlInput.value = storedApiUrl;
        verifyAndShowDashboard();
    }

    // Event Listeners
    loginBtn.addEventListener('click', login);
    logoutBtn.addEventListener('click', logout);
    loadUsersBtn.addEventListener('click', loadUsers);
    loadDataBtn.addEventListener('click', loadActivities);
    userSelect.addEventListener('change', onUserSelect);

    // Enter key to login
    passwordInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') login();
    });
});

// Smooth scroll for navigation
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    });
});

// Login function
async function login() {
    const apiUrl = ensureProtocol(apiUrlInput.value);
    const username = usernameInput.value.trim();
    const password = passwordInput.value;

    if (!apiUrl || !username || !password) {
        showLoginError('Please fill in all fields');
        return;
    }

    loginBtn.textContent = 'Logging in...';
    loginBtn.disabled = true;
    hideLoginError();

    try {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        const response = await fetch(`${apiUrl}/api/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Login failed');
        }

        const data = await response.json();
        authToken = data.access_token;

        // Store in localStorage
        localStorage.setItem('authToken', authToken);
        localStorage.setItem('apiUrl', apiUrl);

        showDashboard();
        loadUsers();

    } catch (error) {
        console.error('Login error:', error);
        showLoginError(error.message);
    } finally {
        loginBtn.textContent = 'Login';
        loginBtn.disabled = false;
    }
}

// Verify stored token and show dashboard
async function verifyAndShowDashboard() {
    const apiUrl = ensureProtocol(apiUrlInput.value);

    try {
        const response = await fetch(`${apiUrl}/api/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` },
        });

        if (response.ok) {
            showDashboard();
            loadUsers();
        } else {
            logout();
        }
    } catch (error) {
        console.error('Token verification failed:', error);
        logout();
    }
}

// Logout function
function logout() {
    authToken = null;
    localStorage.removeItem('authToken');
    showLoginForm();
    authStatus.textContent = '';
    authStatus.className = 'auth-status';
}

// Show login form
function showLoginForm() {
    loginForm.classList.remove('hidden');
    dashboardControls.classList.add('hidden');
    dashboardHint.classList.add('hidden');
    dashboardContent.classList.add('hidden');
}

// Show dashboard
function showDashboard() {
    loginForm.classList.add('hidden');
    dashboardControls.classList.remove('hidden');
    dashboardHint.classList.remove('hidden');
    authStatus.textContent = 'Logged in';
    authStatus.className = 'auth-status logged-in';
}

// Show/hide login error
function showLoginError(message) {
    loginError.textContent = message;
    loginError.classList.remove('hidden');
}

function hideLoginError() {
    loginError.classList.add('hidden');
}

// Handle user selection
function onUserSelect() {
    currentAthleteId = userSelect.value;
    loadDataBtn.disabled = !currentAthleteId;
}

// Authenticated fetch helper
async function authFetch(url, options = {}) {
    const headers = {
        ...options.headers,
        'Authorization': `Bearer ${authToken}`,
    };
    return fetch(url, { ...options, headers });
}

// Load registered users from API
async function loadUsers() {
    const apiUrl = ensureProtocol(apiUrlInput.value);

    loadUsersBtn.textContent = 'Loading...';
    loadUsersBtn.disabled = true;
    hideError();

    try {
        const response = await authFetch(`${apiUrl}/auth/users`);

        if (response.status === 401) {
            logout();
            showLoginError('Session expired. Please login again.');
            return;
        }

        if (!response.ok) {
            throw new Error(`API returned ${response.status}`);
        }

        const data = await response.json();
        const users = data.users || [];

        // Populate user dropdown
        userSelect.innerHTML = '<option value="">Select a user...</option>';
        users.forEach(user => {
            const option = document.createElement('option');
            option.value = user.athlete_id;
            option.textContent = user.athlete_name || `Athlete ${user.athlete_id}`;
            userSelect.appendChild(option);
        });

        userSelect.disabled = users.length === 0;

        if (users.length === 0) {
            showError('No users registered. Authorize a user at /auth/authorize');
        } else if (users.length === 1) {
            userSelect.value = users[0].athlete_id;
            onUserSelect();
        }

    } catch (error) {
        console.error('Error loading users:', error);
        showError(`Failed to load users: ${error.message}`);
    } finally {
        loadUsersBtn.textContent = 'Load Users';
        loadUsersBtn.disabled = false;
    }
}

// Load activities from API
async function loadActivities() {
    const apiUrl = ensureProtocol(apiUrlInput.value);

    if (!currentAthleteId) {
        showError('Please select a user first');
        return;
    }

    loadDataBtn.textContent = 'Loading...';
    loadDataBtn.disabled = true;
    hideError();

    try {
        const response = await authFetch(`${apiUrl}/activities/?athlete_id=${currentAthleteId}`);

        if (response.status === 401) {
            logout();
            showLoginError('Session expired. Please login again.');
            return;
        }

        if (!response.ok) {
            throw new Error(`API returned ${response.status}`);
        }

        activities = await response.json();

        if (!Array.isArray(activities) || activities.length === 0) {
            showError('No activities found for this user.');
            return;
        }

        renderDashboard();
        dashboardContent.classList.remove('hidden');

    } catch (error) {
        console.error('Error loading activities:', error);
        showError(`Failed to load activities: ${error.message}`);
    } finally {
        loadDataBtn.textContent = 'Load Activities';
        loadDataBtn.disabled = false;
    }
}

function showError(message) {
    dashboardError.textContent = message;
    dashboardError.classList.remove('hidden');
    dashboardContent.classList.add('hidden');
}

function hideError() {
    dashboardError.classList.add('hidden');
}

// Render the dashboard with all visualizations
function renderDashboard() {
    renderStats();
    renderDistanceChart();
    renderTypeChart();
    renderWeeklyChart();
    renderElevationChart();
    renderActivitiesTable();
}

// Calculate and display summary statistics
function renderStats() {
    const totalActivities = activities.length;
    const totalDistance = activities.reduce((sum, a) => sum + (a.distance || 0), 0) / 1000;
    const totalTime = activities.reduce((sum, a) => sum + (a.moving_time || 0), 0) / 3600;
    const totalElevation = activities.reduce((sum, a) => sum + (a.total_elevation_gain || 0), 0);

    document.getElementById('totalActivities').textContent = totalActivities;
    document.getElementById('totalDistance').textContent = totalDistance.toFixed(1);
    document.getElementById('totalTime').textContent = totalTime.toFixed(1);
    document.getElementById('totalElevation').textContent = totalElevation.toFixed(0);
}

// Distance over time chart
function renderDistanceChart() {
    const ctx = document.getElementById('distanceChart').getContext('2d');

    const sorted = [...activities]
        .sort((a, b) => new Date(a.start_date) - new Date(b.start_date))
        .slice(-30);

    const labels = sorted.map(a => formatDate(a.start_date));
    const data = sorted.map(a => (a.distance || 0) / 1000);

    if (charts.distance) charts.distance.destroy();

    charts.distance = new Chart(ctx, {
        type: 'line',
        data: {
            labels,
            datasets: [{
                label: 'Distance (km)',
                data,
                borderColor: '#fc4c02',
                backgroundColor: 'rgba(252, 76, 2, 0.1)',
                fill: true,
                tension: 0.3,
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true } }
        }
    });
}

// Activities by type pie chart
function renderTypeChart() {
    const ctx = document.getElementById('typeChart').getContext('2d');

    const typeCounts = {};
    activities.forEach(a => {
        const type = a.type || 'Unknown';
        typeCounts[type] = (typeCounts[type] || 0) + 1;
    });

    const labels = Object.keys(typeCounts);
    const data = Object.values(typeCounts);
    const colors = generateColors(labels.length);

    if (charts.type) charts.type.destroy();

    charts.type = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{ data, backgroundColor: colors }]
        },
        options: {
            responsive: true,
            plugins: { legend: { position: 'right' } }
        }
    });
}

// Weekly activity bar chart
function renderWeeklyChart() {
    const ctx = document.getElementById('weeklyChart').getContext('2d');

    const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
    const dayCounts = new Array(7).fill(0);

    activities.forEach(a => {
        const day = new Date(a.start_date).getDay();
        dayCounts[day]++;
    });

    if (charts.weekly) charts.weekly.destroy();

    charts.weekly = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: dayNames,
            datasets: [{
                label: 'Activities',
                data: dayCounts,
                backgroundColor: '#fc4c02',
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true } }
        }
    });
}

// Elevation profile chart
function renderElevationChart() {
    const ctx = document.getElementById('elevationChart').getContext('2d');

    const sorted = [...activities]
        .filter(a => a.total_elevation_gain > 0)
        .sort((a, b) => new Date(a.start_date) - new Date(b.start_date))
        .slice(-20);

    const labels = sorted.map(a => formatDate(a.start_date));
    const data = sorted.map(a => a.total_elevation_gain || 0);

    if (charts.elevation) charts.elevation.destroy();

    charts.elevation = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Elevation Gain (m)',
                data,
                backgroundColor: 'rgba(252, 76, 2, 0.7)',
            }]
        },
        options: {
            responsive: true,
            plugins: { legend: { display: false } },
            scales: { y: { beginAtZero: true } }
        }
    });
}

// Recent activities table
function renderActivitiesTable() {
    const tbody = document.querySelector('#activitiesTable tbody');

    const recent = [...activities]
        .sort((a, b) => new Date(b.start_date) - new Date(a.start_date))
        .slice(0, 10);

    tbody.innerHTML = recent.map(a => `
        <tr>
            <td>${formatDate(a.start_date)}</td>
            <td>${a.name || 'Untitled'}</td>
            <td>${a.type || 'Unknown'}</td>
            <td>${((a.distance || 0) / 1000).toFixed(2)} km</td>
            <td>${formatDuration(a.moving_time || 0)}</td>
            <td>${(a.total_elevation_gain || 0).toFixed(0)} m</td>
        </tr>
    `).join('');
}

// Helper: Format date
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// Helper: Format duration from seconds
function formatDuration(seconds) {
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) {
        return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
}

// Helper: Generate colors for charts
function generateColors(count) {
    const baseColors = [
        '#fc4c02', '#ff8c00', '#ffa500', '#ffcc00',
        '#4CAF50', '#2196F3', '#9C27B0', '#E91E63',
        '#00BCD4', '#795548'
    ];

    const colors = [];
    for (let i = 0; i < count; i++) {
        colors.push(baseColors[i % baseColors.length]);
    }
    return colors;
}

// Demo mode with sample data
function loadDemoData() {
    activities = [
        { id: 1, name: 'Morning Run', type: 'Run', distance: 5200, moving_time: 1800, total_elevation_gain: 45, start_date: '2025-01-20T07:00:00Z' },
        { id: 2, name: 'Lunch Ride', type: 'Ride', distance: 25000, moving_time: 3600, total_elevation_gain: 320, start_date: '2025-01-19T12:00:00Z' },
        { id: 3, name: 'Evening Walk', type: 'Walk', distance: 3000, moving_time: 2400, total_elevation_gain: 20, start_date: '2025-01-18T18:00:00Z' },
        { id: 4, name: 'Trail Run', type: 'Run', distance: 12000, moving_time: 4500, total_elevation_gain: 280, start_date: '2025-01-17T09:00:00Z' },
        { id: 5, name: 'Commute', type: 'Ride', distance: 8000, moving_time: 1500, total_elevation_gain: 50, start_date: '2025-01-16T08:00:00Z' },
    ];

    renderDashboard();
    dashboardContent.classList.remove('hidden');
}

window.loadDemoData = loadDemoData;
