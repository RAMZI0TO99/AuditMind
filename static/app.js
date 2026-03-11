// --- State Management ---
let jwtToken = localStorage.getItem('token');
let isFetchingReport = false;

// --- DOM Elements ---
const authSection = document.getElementById('auth-section');
const dashboardSection = document.getElementById('dashboard-section');
const authStatus = document.getElementById('auth-status');
const emailInput = document.getElementById('email-input');
const passwordInput = document.getElementById('password-input');
const userGreeting = document.getElementById('user-greeting');
const tierBadge = document.getElementById('tier-badge');

const upgradeHeaderBtn = document.getElementById('upgrade-header-btn');
const manageBillingBtn = document.getElementById('manage-billing-btn');
const upgradeKbBtn = document.getElementById('upgrade-kb-btn');
const kbLockOverlay = document.getElementById('kb-lock-overlay');

const uploadForm = document.getElementById('upload-form');
const fileInput = document.getElementById('file-input');
const statusContainer = document.getElementById('status-container');
const statusText = document.getElementById('status-text');
const reportContainer = document.getElementById('report-container');
const findingsList = document.getElementById('findings-list');

const ruleUploadForm = document.getElementById('rule-upload-form');
const ruleFileInput = document.getElementById('rule-file-input');
const ruleFilenameDisplay = document.getElementById('rule-filename-display');
const ruleUploadStatus = document.getElementById('rule-upload-status');

// --- Handle Stripe Redirects & URL Clean up ---
const urlParams = new URLSearchParams(window.location.search);

if (urlParams.get('success') === 'true') {
    setTimeout(() => {
        alert("🎉 Payment Successful! Welcome to Compliance Guard Pro.");
        window.history.replaceState({}, document.title, window.location.pathname);
        if (jwtToken) fetchUserProfile(); 
    }, 1000);
}

if (urlParams.get('canceled') === 'true') {
    alert("Checkout was canceled. You are still on the Basic tier.");
    window.history.replaceState({}, document.title, window.location.pathname);
}

// --- User Profile & Tier Logic ---
async function fetchUserProfile() {
    try {
        const response = await fetch('/api/me', {
            headers: { 'Authorization': `Bearer ${jwtToken}` }
        });
        if (!response.ok) {
            if (response.status === 401) logoutUser();
            throw new Error("Failed to load profile");
        }
        const data = await response.json();
        
        userGreeting.innerText = data.email;
        
        if (data.tier === 'pro') {
            tierBadge.innerText = 'PRO ACCOUNT';
            tierBadge.className = 'px-2 py-0.5 text-[10px] font-bold rounded bg-purple-100 text-purple-700 uppercase tracking-widest mt-1';
            upgradeHeaderBtn.classList.add('hidden');
            manageBillingBtn.classList.remove('hidden'); // Show billing for Pro
            kbLockOverlay.classList.add('hidden'); // Unlock features
        } else {
            tierBadge.innerText = 'BASIC TIER';
            tierBadge.className = 'px-2 py-0.5 text-[10px] font-bold rounded bg-gray-200 text-gray-600 uppercase tracking-widest mt-1';
            upgradeHeaderBtn.classList.remove('hidden');
            manageBillingBtn.classList.add('hidden'); // Hide billing for Basic
            kbLockOverlay.classList.remove('hidden'); // Show padlock
        }
    } catch (error) {
        console.error(error);
    }
}

// --- Stripe Checkout & Portal Logic ---
async function triggerCheckout(event) {
    try {
        const button = event.target;
        button.innerText = "Loading...";
        
        const response = await fetch('/api/create-checkout-session', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${jwtToken}` }
        });
        const data = await response.json();
        window.location.href = data.url; 
    } catch (error) {
        alert("Failed to initiate checkout. Please try again.");
        event.target.innerText = "Upgrade to Pro";
    }
}

upgradeHeaderBtn.addEventListener('click', triggerCheckout);
upgradeKbBtn.addEventListener('click', triggerCheckout);

manageBillingBtn.addEventListener('click', async (e) => {
    try {
        const button = e.target;
        button.innerText = "Loading...";
        
        const response = await fetch('/api/create-portal-session', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${jwtToken}` }
        });
        
        if (!response.ok) throw new Error("Failed to load portal");
        
        const data = await response.json();
        window.location.href = data.url;
    } catch (error) {
        alert("Failed to open billing portal. Please try again.");
        e.target.innerText = "Manage Billing";
    }
});

// --- Core UI Functions ---
function resetDashboardState() {
    fileInput.value = '';
    ruleFileInput.value = '';
    ruleFilenameDisplay.innerText = 'No file selected';
    ruleUploadStatus.innerText = '';
    statusContainer.classList.add('hidden');
    reportContainer.classList.add('hidden');
    findingsList.innerHTML = '';
    statusText.innerText = '> Waiting for system ready...';
    statusText.className = 'text-green-400 text-sm animate-pulse';
    isFetchingReport = false;
}

function showDashboard() {
    authSection.classList.add('hidden');
    dashboardSection.classList.remove('hidden');
    fetchUserProfile(); 
}

function logoutUser() {
    localStorage.removeItem('token');
    jwtToken = null;
    resetDashboardState();
    dashboardSection.classList.add('hidden');
    authSection.classList.remove('hidden');
    emailInput.value = '';
    passwordInput.value = '';
}

if (jwtToken) {
    showDashboard();
}

// --- Authentication Logic ---
document.getElementById('signup-btn').addEventListener('click', async (e) => {
    e.preventDefault();
    try {
        const response = await fetch('/api/signup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email: emailInput.value, password: passwordInput.value })
        });
        const data = await response.json();
        if (response.ok) {
            authStatus.innerText = "Account created! Please log in.";
            authStatus.className = "text-sm mt-4 text-center text-green-600 font-semibold";
            passwordInput.value = '';
        } else {
            throw new Error(data.detail || "Signup failed");
        }
    } catch (error) {
        authStatus.innerText = error.message;
        authStatus.className = "text-sm mt-4 text-center text-red-600 font-semibold";
    }
});

document.getElementById('login-btn').addEventListener('click', async (e) => {
    e.preventDefault();
    const formData = new URLSearchParams();
    formData.append('username', emailInput.value);
    formData.append('password', passwordInput.value);

    try {
        const response = await fetch('/api/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
        });
        const data = await response.json();
        if (response.ok) {
            jwtToken = data.access_token;
            localStorage.setItem('token', jwtToken);
            emailInput.value = '';
            passwordInput.value = '';
            authStatus.innerText = '';
            resetDashboardState(); 
            showDashboard();
        } else {
            throw new Error(data.detail || "Login failed");
        }
    } catch (error) {
        authStatus.innerText = error.message;
        authStatus.className = "text-sm mt-4 text-center text-red-600 font-semibold";
    }
});

document.getElementById('logout-btn').addEventListener('click', (e) => {
    e.preventDefault();
    logoutUser();
});

// --- Rulebook UI Logic ---
ruleFileInput.addEventListener('change', (e) => {
    if (e.target.files.length > 0) {
        ruleFilenameDisplay.innerText = e.target.files[0].name;
        ruleFilenameDisplay.classList.add('text-purple-600');
    }
});

ruleUploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!ruleFileInput.files[0]) {
        ruleUploadStatus.innerText = "Please select a .md or .txt file first.";
        ruleUploadStatus.className = "text-xs text-center mt-3 font-semibold text-red-500";
        return;
    }

    ruleUploadStatus.innerText = "Syncing to Server...";
    ruleUploadStatus.className = "text-xs text-center mt-3 font-semibold text-gray-500";

    const formData = new FormData();
    formData.append('file', ruleFileInput.files[0]);

    try {
        const response = await fetch('/api/rules/upload', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${jwtToken}` },
            body: formData
        });
        
        if (response.status === 403) {
            ruleUploadStatus.innerText = "Please upgrade to Pro first.";
            ruleUploadStatus.className = "text-xs text-center mt-3 font-semibold text-red-500";
            return;
        }
        if (!response.ok) throw new Error("Failed to upload rules");

        ruleUploadStatus.innerText = "Rules successfully updated!";
        ruleUploadStatus.className = "text-xs text-center mt-3 font-semibold text-green-600";
        ruleFileInput.value = '';
        setTimeout(() => { ruleUploadStatus.innerText = ''; }, 3000);

    } catch (error) {
        ruleUploadStatus.innerText = error.message;
        ruleUploadStatus.className = "text-xs text-center mt-3 font-semibold text-red-500";
    }
});

// --- Contract Upload Pipeline Logic ---
uploadForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    if (!fileInput.files[0]) return alert("Please select a file.");

    reportContainer.classList.add('hidden');
    statusContainer.classList.remove('hidden');
    statusText.innerText = "> Uploading document...";
    statusText.className = 'text-green-400 text-sm animate-pulse';
    findingsList.innerHTML = '';
    isFetchingReport = false;

    const formData = new FormData();
    formData.append('file', fileInput.files[0]);

    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${jwtToken}` },
            body: formData
        });
        
        if (!response.ok) {
            if (response.status === 401) return logoutUser();
            throw new Error(`Server returned status ${response.status}`);
        }
        
        const data = await response.json();
        connectWebSocket(data.document_id);

    } catch (error) {
        statusText.innerText = `> Error: ${error.message}`;
        statusText.className = 'text-red-400 text-sm';
    }
});

function connectWebSocket(documentId) {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.host;
    const ws = new WebSocket(`${wsProtocol}//${wsHost}/ws/documents/${documentId}`);

    ws.onopen = () => {
        statusText.innerText = "> Connection established. Synchronizing with AI...";
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        statusText.innerText = data.agent ? `> [${data.agent} Agent]: ${data.message}` : `> ${data.message}`;

        if (data.status === 'completed') {
            ws.close();
            fetchReport(documentId);
        } else if (data.status === 'failed') {
            ws.close();
            statusText.className = 'text-red-400 text-sm';
        }
    };

    ws.onclose = () => { if (!reportContainer.classList.contains('hidden') === false) fetchReport(documentId); };
    ws.onerror = () => fetchReport(documentId);
}

async function fetchReport(documentId) {
    if (isFetchingReport || !reportContainer.classList.contains('hidden')) return;
    isFetchingReport = true;

    try {
        statusText.innerText = "> Fetching final report...";
        const response = await fetch(`/api/documents/${documentId}/report`, {
            headers: { 'Authorization': `Bearer ${jwtToken}` }
        });
        if (!response.ok) throw new Error("Failed to load report");
        
        const data = await response.json();
        findingsList.innerHTML = '';
        renderFindings(data.findings);
        
        statusContainer.classList.add('hidden');
        reportContainer.classList.remove('hidden');
    } catch (error) {
        statusText.innerText = `> Failed to load report: ${error.message}`;
        statusText.className = 'text-red-400 text-sm';
    } finally {
        isFetchingReport = false;
    }
}

function renderFindings(findings) {
    if (findings.length === 0) {
        findingsList.innerHTML = `<p class="text-gray-600 bg-white p-6 rounded-lg shadow border-l-4 border-green-500 font-medium">No high-risk clauses found. Document looks compliant!</p>`;
        return;
    }

    findings.forEach(finding => {
        const card = document.createElement('div');
        card.className = "bg-white p-6 rounded-lg shadow-md border-l-4 border-red-500";
        const confidence = finding.confidence_score ? (finding.confidence_score * 100).toFixed(0) : "100";
        
        card.innerHTML = `
            <div class="flex justify-between items-start mb-2">
                <h3 class="text-lg font-bold text-red-600">Risk Flagged</h3>
                <span class="text-sm font-mono bg-gray-100 px-2 py-1 rounded">Confidence: ${confidence}%</span>
            </div>
            <p class="text-sm text-gray-500 mb-4 font-semibold">Citation: ${finding.rule_citation || "Policy Violation"}</p>
            <div class="mb-4"><p class="text-xs text-gray-400 uppercase tracking-wider font-bold mb-1">Original Text</p>
            <p class="text-gray-700 bg-red-50 p-3 rounded text-sm">${finding.original_text}</p></div>
            <div class="mb-4"><p class="text-xs text-gray-400 uppercase tracking-wider font-bold mb-1">Issue</p>
            <p class="text-gray-700 text-sm">${finding.issue_description}</p></div>
            <div><p class="text-xs text-gray-400 uppercase tracking-wider font-bold mb-1">Suggested Rewrite</p>
            <p class="text-green-800 bg-green-50 p-3 rounded text-sm">${finding.suggested_rewrite}</p></div>
        `;
        findingsList.appendChild(card);
    });
}