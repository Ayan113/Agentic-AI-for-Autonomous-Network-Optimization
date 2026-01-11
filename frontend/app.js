/**
 * Agentic AI Network Optimizer - Frontend Application
 */

const API_BASE = 'http://localhost:8000';

// State
let state = {
    connected: false,
    metrics: null,
    decisions: [],
    activities: [],
    cycleCount: 0,
    lastCycle: null
};

// DOM Elements
const elements = {
    connectionStatus: document.getElementById('connectionStatus'),
    healthScore: document.getElementById('healthScore'),
    healthRing: document.getElementById('healthRing'),
    totalNodes: document.getElementById('totalNodes'),
    healthyNodes: document.getElementById('healthyNodes'),
    unhealthyNodes: document.getElementById('unhealthyNodes'),
    runCycleBtn: document.getElementById('runCycleBtn'),
    refreshBtn: document.getElementById('refreshBtn'),
    scenarioSelect: document.getElementById('scenarioSelect'),
    cycleCount: document.getElementById('cycleCount'),
    lastCycle: document.getElementById('lastCycle'),
    avgLatency: document.getElementById('avgLatency'),
    avgBandwidth: document.getElementById('avgBandwidth'),
    avgPacketLoss: document.getElementById('avgPacketLoss'),
    avgCpu: document.getElementById('avgCpu'),
    avgMemory: document.getElementById('avgMemory'),
    maxLatency: document.getElementById('maxLatency'),
    nodesGrid: document.getElementById('nodesGrid'),
    activityFeed: document.getElementById('activityFeed'),
    decisionsList: document.getElementById('decisionsList'),
    toastContainer: document.getElementById('toastContainer'),
    // Metric bars
    latencyBar: document.getElementById('latencyBar'),
    bandwidthBar: document.getElementById('bandwidthBar'),
    packetLossBar: document.getElementById('packetLossBar'),
    cpuBar: document.getElementById('cpuBar'),
    memoryBar: document.getElementById('memoryBar'),
    maxLatencyBar: document.getElementById('maxLatencyBar'),
    // Agents
    monitorAgent: document.getElementById('monitorAgent'),
    decisionAgent: document.getElementById('decisionAgent'),
    actionAgent: document.getElementById('actionAgent'),
    coordinatorAgent: document.getElementById('coordinatorAgent')
};

// API Functions
async function fetchAPI(endpoint, options = {}) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            ...options,
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return await response.json();
    } catch (error) {
        console.error(`API Error (${endpoint}):`, error);
        throw error;
    }
}

async function checkConnection() {
    try {
        await fetchAPI('/health');
        setConnected(true);
        return true;
    } catch {
        setConnected(false);
        return false;
    }
}

function setConnected(connected) {
    state.connected = connected;
    const status = elements.connectionStatus;

    if (connected) {
        status.classList.add('connected');
        status.classList.remove('error');
        status.querySelector('.status-text').textContent = 'Connected';
    } else {
        status.classList.remove('connected');
        status.classList.add('error');
        status.querySelector('.status-text').textContent = 'Disconnected';
    }
}

// Data Fetching
async function fetchMetrics() {
    try {
        const data = await fetchAPI('/metrics');
        state.metrics = data;
        updateMetricsUI(data);
        return data;
    } catch (error) {
        console.error('Failed to fetch metrics:', error);
    }
}

async function fetchStatus() {
    try {
        const data = await fetchAPI('/status');
        updateAgentsUI(data);
        updateCycleInfo(data);
        return data;
    } catch (error) {
        console.error('Failed to fetch status:', error);
    }
}

async function fetchDecisions() {
    try {
        const data = await fetchAPI('/decisions?limit=10');
        state.decisions = data.decisions || [];
        updateDecisionsUI(state.decisions);
        return data;
    } catch (error) {
        console.error('Failed to fetch decisions:', error);
    }
}

async function runCycle() {
    elements.runCycleBtn.disabled = true;
    elements.runCycleBtn.innerHTML = '<span class="btn-icon">⏳</span> Running...';

    // Animate agents
    activateAgent('coordinatorAgent');

    try {
        addActivity('🚀', 'Cycle Started', 'Running optimization cycle...');

        // Phase 1: Monitor
        activateAgent('monitorAgent');
        await delay(500);

        const result = await fetchAPI('/cycle', { method: 'POST' });

        // Phase 2: Decision
        activateAgent('decisionAgent');
        await delay(500);

        // Phase 3: Action (if needed)
        const cycleResult = result.results?.[0];
        if (cycleResult?.phases?.action?.executed) {
            activateAgent('actionAgent');
            await delay(500);
        }

        // Update UI
        await fetchMetrics();
        await fetchStatus();
        await fetchDecisions();

        // Add activity
        const healthScore = cycleResult?.phases?.monitor?.health_score?.toFixed(1) || '--';
        const actionsCount = cycleResult?.phases?.decision?.actions_recommended || 0;

        if (actionsCount > 0) {
            addActivity('⚡', 'Actions Executed', `${actionsCount} corrective actions taken`);
            showToast('success', 'Cycle Complete', `Executed ${actionsCount} actions`);
        } else {
            addActivity('✅', 'Network Healthy', `Health score: ${healthScore}`);
            showToast('success', 'Cycle Complete', 'Network is healthy, no action needed');
        }

        state.cycleCount++;
        state.lastCycle = new Date();
        updateCycleDisplay();

    } catch (error) {
        showToast('error', 'Cycle Failed', error.message);
        addActivity('❌', 'Cycle Failed', error.message);
    } finally {
        deactivateAllAgents();
        elements.runCycleBtn.disabled = false;
        elements.runCycleBtn.innerHTML = '<span class="btn-icon">▶</span> Run Cycle';
    }
}

async function triggerScenario(scenario) {
    if (!scenario) return;

    try {
        await fetchAPI('/simulate', {
            method: 'POST',
            body: JSON.stringify({ scenario })
        });

        const scenarioNames = {
            'high_traffic': '🔥 High Traffic',
            'outage': '💥 Node Outage',
            'gradual_degradation': '📉 Degradation',
            'recovery': '✨ Recovery',
            'normal': '✅ Normal'
        };

        addActivity('🎯', 'Scenario Triggered', scenarioNames[scenario] || scenario);
        showToast('info', 'Scenario Applied', `${scenarioNames[scenario] || scenario} activated`);

        await fetchMetrics();

    } catch (error) {
        showToast('error', 'Scenario Failed', error.message);
    }

    elements.scenarioSelect.value = '';
}

// UI Update Functions
function updateMetricsUI(data) {
    if (!data) return;

    const summary = data.summary || {};
    const health = data.health || 0;
    const metrics = data.metrics || {};

    // Update health score
    updateHealthScore(health);

    // Update node counts
    elements.totalNodes.textContent = summary.node_count || 0;
    elements.healthyNodes.textContent = summary.healthy_nodes || 0;
    elements.unhealthyNodes.textContent = summary.unhealthy_nodes || 0;

    // Update metrics
    const avgLatency = summary.avg_latency || 0;
    const avgBandwidth = summary.avg_bandwidth || 0;
    const avgPacketLoss = summary.avg_packet_loss || 0;
    const avgCpu = summary.avg_cpu || 0;
    const avgMemory = summary.avg_memory || 0;
    const maxLatency = summary.max_latency || 0;

    elements.avgLatency.textContent = avgLatency.toFixed(1);
    elements.avgBandwidth.textContent = avgBandwidth.toFixed(0);
    elements.avgPacketLoss.textContent = avgPacketLoss.toFixed(2);
    elements.avgCpu.textContent = avgCpu.toFixed(1);
    elements.avgMemory.textContent = avgMemory.toFixed(1);
    elements.maxLatency.textContent = maxLatency.toFixed(1);

    // Update bars
    updateMetricBar(elements.latencyBar, avgLatency, 200, avgLatency > 100);
    updateMetricBar(elements.bandwidthBar, avgBandwidth, 1000);
    updateMetricBar(elements.packetLossBar, avgPacketLoss, 10, avgPacketLoss > 5);
    updateMetricBar(elements.cpuBar, avgCpu, 100, avgCpu > 80);
    updateMetricBar(elements.memoryBar, avgMemory, 100, avgMemory > 85);
    updateMetricBar(elements.maxLatencyBar, maxLatency, 300, maxLatency > 100);

    // Update nodes grid
    updateNodesGrid(metrics.nodes || []);
}

function updateHealthScore(health) {
    const score = Math.round(health);
    elements.healthScore.textContent = score;

    // Update ring
    const circumference = 2 * Math.PI * 54;
    const offset = circumference - (score / 100) * circumference;
    elements.healthRing.style.strokeDashoffset = offset;

    // Update color based on health
    let color;
    if (score >= 80) {
        color = '#10b981';
    } else if (score >= 60) {
        color = '#f59e0b';
    } else {
        color = '#ef4444';
    }
    elements.healthRing.style.stroke = color;
}

function updateMetricBar(element, value, max, isWarning = false) {
    const percentage = Math.min((value / max) * 100, 100);
    element.style.width = `${percentage}%`;

    element.classList.remove('warning', 'danger');
    if (isWarning) {
        element.classList.add(value > max * 0.8 ? 'danger' : 'warning');
    }
}

function updateNodesGrid(nodes) {
    if (!nodes || nodes.length === 0) {
        elements.nodesGrid.innerHTML = `
            <div class="activity-empty" style="grid-column: span 5;">
                <span>🖥️</span>
                <p>No nodes data</p>
            </div>
        `;
        return;
    }

    elements.nodesGrid.innerHTML = nodes.map(node => {
        const health = calculateNodeHealth(node);
        let status = 'healthy';
        if (health < 50) status = 'critical';
        else if (health < 75) status = 'warning';

        return `
            <div class="node-item ${status}" title="${node.node_id}: ${health.toFixed(0)}%">
                <div class="node-icon">🖥️</div>
                <div class="node-id">${node.node_id.replace('node_', 'N')}</div>
                <div class="node-health">${health.toFixed(0)}%</div>
            </div>
        `;
    }).join('');
}

function calculateNodeHealth(node) {
    let score = 100;

    if (node.latency > 50) score -= Math.min(25, (node.latency - 50) * 0.25);
    score -= node.packet_loss * 4;
    if (node.bandwidth < 500) score -= Math.min(15, (500 - node.bandwidth) * 0.03);
    if (node.cpu_usage > 70) score -= Math.min(20, (node.cpu_usage - 70) * 0.67);
    if (node.memory_usage > 70) score -= Math.min(15, (node.memory_usage - 70) * 0.5);

    return Math.max(0, score);
}

function updateAgentsUI(status) {
    if (!status) return;

    updateAgentStatus(elements.monitorAgent, status.monitor);
    updateAgentStatus(elements.decisionAgent, status.decision);
    updateAgentStatus(elements.actionAgent, status.action);
    updateAgentStatus(elements.coordinatorAgent, status.coordinator);
}

function updateAgentStatus(element, agentStatus) {
    if (!element || !agentStatus) return;

    const statusText = element.querySelector('.agent-status');
    if (statusText) {
        statusText.textContent = agentStatus.status || 'Unknown';
    }
}

function activateAgent(agentId) {
    const agent = elements[agentId];
    if (agent) {
        agent.classList.add('active');
    }
}

function deactivateAllAgents() {
    ['monitorAgent', 'decisionAgent', 'actionAgent', 'coordinatorAgent'].forEach(id => {
        if (elements[id]) {
            elements[id].classList.remove('active');
        }
    });
}

function updateCycleInfo(status) {
    if (!status?.cycles) return;

    state.cycleCount = status.cycles.total || 0;
    if (status.cycles.last_cycle) {
        state.lastCycle = new Date(status.cycles.last_cycle);
    }

    updateCycleDisplay();
}

function updateCycleDisplay() {
    elements.cycleCount.textContent = state.cycleCount;

    if (state.lastCycle) {
        elements.lastCycle.textContent = formatTime(state.lastCycle);
    }
}

function updateDecisionsUI(decisions) {
    if (!decisions || decisions.length === 0) {
        elements.decisionsList.innerHTML = `
            <div class="activity-empty">
                <span>🧠</span>
                <p>No decisions yet</p>
            </div>
        `;
        return;
    }

    elements.decisionsList.innerHTML = decisions.slice(0, 5).map(d => {
        const decision = d.decision || {};
        const actionRequired = decision.action_required;
        const actions = decision.recommended_actions || [];
        const reasoning = decision.reasoning || 'No reasoning provided';
        const timestamp = d.timestamp ? new Date(d.timestamp) : new Date();

        return `
            <div class="decision-item">
                <div class="decision-header">
                    <span class="decision-badge ${actionRequired ? 'action-required' : 'no-action'}">
                        ${actionRequired ? '⚡ Action Required' : '✅ No Action'}
                    </span>
                    <span class="decision-time">${formatTime(timestamp)}</span>
                </div>
                <div class="decision-reasoning">${reasoning.substring(0, 150)}${reasoning.length > 150 ? '...' : ''}</div>
                ${actions.length > 0 ? `
                    <div class="decision-actions">
                        ${actions.map(a => `
                            <span class="action-tag">
                                <span>${getActionIcon(a.action)}</span>
                                ${a.action}
                            </span>
                        `).join('')}
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

function getActionIcon(action) {
    const icons = {
        'optimize_routing': '🔀',
        'reduce_traffic': '📉',
        'load_balance': '⚖️',
        'clear_cache': '🧹',
        'request_bandwidth': '📶',
        'restart_service': '🔄',
        'alert': '🔔',
        'scale_up': '📈',
        'scale_down': '📉'
    };
    return icons[action] || '⚡';
}

// Activity Feed
function addActivity(icon, title, description) {
    const activity = {
        icon,
        title,
        description,
        time: new Date()
    };

    state.activities.unshift(activity);
    state.activities = state.activities.slice(0, 20);

    renderActivities();
}

function renderActivities() {
    if (state.activities.length === 0) {
        elements.activityFeed.innerHTML = `
            <div class="activity-empty">
                <span>🔍</span>
                <p>Run a cycle to see activity</p>
            </div>
        `;
        return;
    }

    elements.activityFeed.innerHTML = state.activities.map(a => `
        <div class="activity-item">
            <div class="activity-icon">${a.icon}</div>
            <div class="activity-content">
                <div class="activity-title">${a.title}</div>
                <div class="activity-description">${a.description}</div>
            </div>
            <div class="activity-time">${formatTime(a.time)}</div>
        </div>
    `).join('');
}

// Toast Notifications
function showToast(type, title, message) {
    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️'
    };

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-icon">${icons[type]}</div>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
    `;

    elements.toastContainer.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'toastIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

// Utilities
function formatTime(date) {
    if (!date) return '--';
    const d = new Date(date);
    return d.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
}

function delay(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Event Listeners
function setupEventListeners() {
    elements.runCycleBtn.addEventListener('click', runCycle);
    elements.refreshBtn.addEventListener('click', async () => {
        elements.refreshBtn.disabled = true;
        await Promise.all([fetchMetrics(), fetchStatus(), fetchDecisions()]);
        elements.refreshBtn.disabled = false;
        showToast('info', 'Refreshed', 'Data updated');
    });
    elements.scenarioSelect.addEventListener('change', (e) => {
        triggerScenario(e.target.value);
    });
}

// Initialize
async function init() {
    console.log('🚀 Initializing Agentic AI Network Optimizer Dashboard...');

    setupEventListeners();

    // Check connection
    const connected = await checkConnection();

    if (connected) {
        await Promise.all([
            fetchMetrics(),
            fetchStatus(),
            fetchDecisions()
        ]);
        addActivity('🟢', 'Connected', 'Dashboard connected to API');
    } else {
        addActivity('🔴', 'Disconnected', 'API not available. Start the server with: python run.py api');
        showToast('warning', 'API Offline', 'Start the server: python run.py api');
    }

    // Auto-refresh every 10 seconds if connected
    setInterval(async () => {
        if (state.connected) {
            const stillConnected = await checkConnection();
            if (stillConnected) {
                await fetchMetrics();
            }
        } else {
            await checkConnection();
        }
    }, 10000);
}

// Start
document.addEventListener('DOMContentLoaded', init);
