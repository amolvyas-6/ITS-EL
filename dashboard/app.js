/**
 * app.js — Interactive Dashboard for Crowd Movement Simulation
 *
 * Features:
 *  - Real-time graph visualization with density-scaled nodes
 *  - Animated simulation playback
 *  - Crowd density heatmap (before/after/difference)
 *  - Stationary distribution comparison chart
 *  - Mean first passage time comparison
 *  - Transition matrix heatmap
 *  - Key observations auto-generated from data
 */

// ═══════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════

const NODE_COLORS = {
    entrance: '#58a6ff',
    exit:     '#3fb950',
    gate:     '#d29922',
    corridor: '#8b949e',
    platform: '#f85149',
};

const COLORS = {
    bg:          '#0d1117',
    bgCard:      '#161b22',
    border:      '#30363d',
    borderLight: '#21262d',
    textPrimary: '#e6edf3',
    textSecondary: '#8b949e',
    textMuted:   '#484f58',
    accentBlue:  '#58a6ff',
    accentGreen: '#3fb950',
    accentRed:   '#f85149',
    accentYellow:'#d29922',
};

// ═══════════════════════════════════════════════════════════════════════
// STATE
// ═══════════════════════════════════════════════════════════════════════

let DATA = null;
let currentTimestep = 0;
let currentView = 'before'; // 'before' | 'after'
let currentHeatmap = 'before';
let currentMatrix = 'before';
let isPlaying = false;
let playInterval = null;
let animSpeed = 500;
const DPR = window.devicePixelRatio || 1;

// ═══════════════════════════════════════════════════════════════════════
// DATA LOADING
// ═══════════════════════════════════════════════════════════════════════

async function loadData() {
    try {
        const response = await fetch('simulation_data.json');
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        DATA = await response.json();
        onDataLoaded();
    } catch (err) {
        console.error('Failed to load simulation data:', err);
        document.getElementById('status-badge').innerHTML =
            '<span class="pulse" style="background:var(--accent-red)"></span> Data Error — Run main.py first';
    }
}

function onDataLoaded() {
    // Update status
    const badge = document.getElementById('status-badge');
    badge.innerHTML = '<span class="pulse active"></span> Simulation Loaded';

    // Update stats
    document.querySelector('#stat-nodes .stat-value').textContent = DATA.nodes.length;
    document.querySelector('#stat-edges .stat-value').textContent = DATA.edges.length;
    document.querySelector('#stat-steps .stat-value').textContent = DATA.n_steps;
    document.querySelector('#stat-bottlenecks .stat-value').textContent = DATA.bottlenecks.length;

    // Compute improvement metric — use mean steps to exit reduction
    const nonExitNodesForStat = DATA.nodes.filter(n => n.type !== 'exit');
    let totalMFPTBefore = 0, totalMFPTAfter = 0;
    for (const n of nonExitNodesForStat) {
        totalMFPTBefore += DATA.mfpt_before[String(n.id)] || 0;
        totalMFPTAfter  += DATA.mfpt_after[String(n.id)]  || 0;
    }
    let congReductionPct = 0;
    if (totalMFPTBefore > 0) {
        congReductionPct = ((totalMFPTBefore - totalMFPTAfter) / totalMFPTBefore * 100).toFixed(0);
    }
    document.querySelector('#stat-improvement .stat-value').textContent = `~${congReductionPct}%`;
    document.querySelector('#stat-improvement .stat-label').textContent = 'Flow Improvement';

    // Set slider max
    document.getElementById('time-slider').max = DATA.n_steps;

    // Draw everything
    drawGraph();
    drawHeatmap();
    drawStationary();
    drawMFPT();
    drawTransitionMatrix();
    updateDistributionList();
    generateObservations();
}

// ═══════════════════════════════════════════════════════════════════════
// CANVAS HELPERS
// ═══════════════════════════════════════════════════════════════════════

function setupCanvas(canvas, width, height) {
    canvas.width = width * DPR;
    canvas.height = height * DPR;
    canvas.style.width = width + 'px';
    canvas.style.height = height + 'px';
    const ctx = canvas.getContext('2d');
    ctx.scale(DPR, DPR);
    return ctx;
}

function clearCanvas(ctx, width, height) {
    ctx.fillStyle = COLORS.bg;
    ctx.fillRect(0, 0, width, height);
}

function lerpColor(c1, c2, t) {
    // c1, c2 are hex strings
    const r1 = parseInt(c1.slice(1,3), 16);
    const g1 = parseInt(c1.slice(3,5), 16);
    const b1 = parseInt(c1.slice(5,7), 16);
    const r2 = parseInt(c2.slice(1,3), 16);
    const g2 = parseInt(c2.slice(3,5), 16);
    const b2 = parseInt(c2.slice(5,7), 16);
    const r = Math.round(r1 + (r2 - r1) * t);
    const g = Math.round(g1 + (g2 - g1) * t);
    const b = Math.round(b1 + (b2 - b1) * t);
    return `rgb(${r},${g},${b})`;
}

function densityColor(density) {
    if (density < 0.05) return lerpColor('#161b22', '#1a3a5c', density / 0.05);
    if (density < 0.15) return lerpColor('#1a3a5c', '#d29922', (density - 0.05) / 0.10);
    return lerpColor('#d29922', '#f85149', Math.min((density - 0.15) / 0.35, 1));
}

function diffColor(diff) {
    if (diff < -0.01) return lerpColor('#0d1117', '#3fb950', Math.min(Math.abs(diff) / 0.15, 1));
    if (diff > 0.01)  return lerpColor('#0d1117', '#f85149', Math.min(diff / 0.15, 1));
    return '#161b22';
}

// ═══════════════════════════════════════════════════════════════════════
// 1. GRAPH VISUALIZATION
// ═══════════════════════════════════════════════════════════════════════

function drawGraph() {
    const canvas = document.getElementById('graph-canvas');
    const W = canvas.parentElement.clientWidth - 48;
    const H = 450;
    const ctx = setupCanvas(canvas, W, H);
    clearCanvas(ctx, W, H);

    if (!DATA) return;

    const history = currentView === 'before' ? DATA.history_before : DATA.history_after;
    const dist = history[currentTimestep];

    // Compute coordinate mapping
    const xs = DATA.nodes.map(n => n.x);
    const ys = DATA.nodes.map(n => n.y);
    const minX = Math.min(...xs) - 0.5, maxX = Math.max(...xs) + 0.5;
    const minY = Math.min(...ys) - 0.5, maxY = Math.max(...ys) + 0.5;

    const pad = 60;
    const scaleX = (W - 2 * pad) / (maxX - minX);
    const scaleY = (H - 2 * pad) / (maxY - minY);

    function tx(x) { return pad + (x - minX) * scaleX; }
    function ty(y) { return H - pad - (y - minY) * scaleY; }

    // Draw edges
    ctx.strokeStyle = COLORS.border;
    ctx.lineWidth = 2;
    for (const edge of DATA.edges) {
        const src = DATA.nodes.find(n => n.id === edge.source);
        const tgt = DATA.nodes.find(n => n.id === edge.target);
        if (!src || !tgt) continue;

        ctx.beginPath();
        ctx.moveTo(tx(src.x), ty(src.y));
        ctx.lineTo(tx(tgt.x), ty(tgt.y));
        ctx.stroke();

        // Edge weight label
        const mx = (tx(src.x) + tx(tgt.x)) / 2;
        const my = (ty(src.y) + ty(tgt.y)) / 2;
        ctx.font = '9px Inter';
        ctx.fillStyle = COLORS.textMuted;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(edge.weight.toFixed(1), mx, my - 8);
    }

    // Draw nodes
    for (let i = 0; i < DATA.nodes.length; i++) {
        const node = DATA.nodes[i];
        const x = tx(node.x);
        const y = ty(node.y);
        const density = dist[i];
        const baseRadius = 18;
        const radius = baseRadius + density * 80;

        // Glow for congested nodes
        if (density > 0.15) {
            const gradient = ctx.createRadialGradient(x, y, radius, x, y, radius * 2.5);
            gradient.addColorStop(0, 'rgba(248,81,73,0.3)');
            gradient.addColorStop(1, 'transparent');
            ctx.fillStyle = gradient;
            ctx.beginPath();
            ctx.arc(x, y, radius * 2.5, 0, Math.PI * 2);
            ctx.fill();
        }

        // Node circle
        const color = density > 0.15 ? COLORS.accentRed :
                      density > 0.05 ? COLORS.accentYellow :
                      NODE_COLORS[node.type] || COLORS.textSecondary;

        ctx.beginPath();
        ctx.arc(x, y, radius, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = COLORS.border;
        ctx.lineWidth = 2;
        ctx.stroke();

        // Density text
        if (density > 0.005) {
            ctx.font = 'bold 10px JetBrains Mono';
            ctx.fillStyle = '#fff';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(density.toFixed(2), x, y);
        }

        // Label below node
        ctx.font = '9px Inter';
        ctx.fillStyle = COLORS.textSecondary;
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        ctx.fillText(node.label, x, y + radius + 5);
    }

    // Title
    ctx.font = 'bold 13px Inter';
    ctx.fillStyle = COLORS.textPrimary;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    const viewLabel = currentView === 'before' ? 'Original Flow' : 'Optimized Flow';
    ctx.fillText(`${viewLabel} — t = ${currentTimestep}`, pad, 12);
}

// ═══════════════════════════════════════════════════════════════════════
// 2. DENSITY HEATMAP
// ═══════════════════════════════════════════════════════════════════════

function drawHeatmap() {
    const canvas = document.getElementById('heatmap-canvas');
    const W = canvas.parentElement.clientWidth - 48;
    const H = 380;
    const ctx = setupCanvas(canvas, W, H);
    clearCanvas(ctx, W, H);

    if (!DATA) return;

    const nNodes = DATA.nodes.length;
    const nSteps = DATA.n_steps + 1;

    const padL = 130, padR = 60, padT = 40, padB = 50;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;
    const cellW = plotW / nSteps;
    const cellH = plotH / nNodes;

    let histData;
    if (currentHeatmap === 'diff') {
        histData = DATA.history_before.map((row, t) =>
            row.map((val, i) => DATA.history_after[t][i] - val)
        );
    } else {
        histData = currentHeatmap === 'before' ? DATA.history_before : DATA.history_after;
    }

    // Draw cells
    for (let t = 0; t < nSteps; t++) {
        for (let j = 0; j < nNodes; j++) {
            const val = histData[t][j];
            const x = padL + t * cellW;
            const y = padT + j * cellH;

            ctx.fillStyle = currentHeatmap === 'diff' ? diffColor(val) : densityColor(val);
            ctx.fillRect(x, y, cellW + 0.5, cellH + 0.5);

            // Text for high values
            if (Math.abs(val) > 0.12 && cellW > 18) {
                ctx.font = '8px JetBrains Mono';
                ctx.fillStyle = '#fff';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(val.toFixed(2), x + cellW / 2, y + cellH / 2);
            }
        }
    }

    // Time step indicator (vertical line)
    const indicatorX = padL + currentTimestep * cellW + cellW / 2;
    ctx.strokeStyle = COLORS.accentBlue;
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(indicatorX, padT);
    ctx.lineTo(indicatorX, padT + plotH);
    ctx.stroke();
    ctx.setLineDash([]);

    // Y-axis labels (node names)
    ctx.font = '9px Inter';
    ctx.fillStyle = COLORS.textSecondary;
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    for (let j = 0; j < nNodes; j++) {
        ctx.fillText(DATA.nodes[j].label, padL - 8, padT + j * cellH + cellH / 2);
    }

    // X-axis labels (time steps)
    ctx.textAlign = 'center';
    ctx.textBaseline = 'top';
    const stepInterval = Math.max(1, Math.floor(nSteps / 10));
    for (let t = 0; t < nSteps; t += stepInterval) {
        ctx.fillText(`t=${t}`, padL + t * cellW + cellW / 2, padT + plotH + 6);
    }

    // Title
    ctx.font = 'bold 12px Inter';
    ctx.fillStyle = COLORS.textPrimary;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    const hmLabel = currentHeatmap === 'diff' ? 'Difference (After − Before)' :
                    currentHeatmap === 'before' ? 'Before Optimization' : 'After Optimization';
    ctx.fillText(`Crowd Density — ${hmLabel}`, padL, 10);

    // Color bar
    const barX = W - padR + 10;
    const barW = 15;
    const barH = plotH;
    for (let y = 0; y < barH; y++) {
        const t = 1 - y / barH;
        const val = currentHeatmap === 'diff' ? (t - 0.5) * 0.3 : t * 0.5;
        ctx.fillStyle = currentHeatmap === 'diff' ? diffColor(val) : densityColor(val);
        ctx.fillRect(barX, padT + y, barW, 1);
    }
    ctx.strokeStyle = COLORS.border;
    ctx.strokeRect(barX, padT, barW, barH);

    ctx.font = '8px JetBrains Mono';
    ctx.textAlign = 'left';
    ctx.fillStyle = COLORS.textSecondary;
    if (currentHeatmap === 'diff') {
        ctx.fillText('+0.15', barX + barW + 4, padT);
        ctx.fillText('0', barX + barW + 4, padT + barH / 2);
        ctx.fillText('-0.15', barX + barW + 4, padT + barH);
    } else {
        ctx.fillText('0.50', barX + barW + 4, padT);
        ctx.fillText('0', barX + barW + 4, padT + barH);
    }
}

// ═══════════════════════════════════════════════════════════════════════
// 3. STATIONARY DISTRIBUTION
// ═══════════════════════════════════════════════════════════════════════

function drawStationary() {
    const canvas = document.getElementById('stationary-canvas');
    const W = canvas.parentElement.clientWidth - 48;
    const H = 320;
    const ctx = setupCanvas(canvas, W, H);
    clearCanvas(ctx, W, H);

    if (!DATA) return;

    const n = DATA.nodes.length;
    const padL = 40, padR = 20, padT = 40, padB = 80;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;
    const barW = plotW / n * 0.35;
    const gap = plotW / n;

    const maxVal = Math.max(...DATA.stationary_before, ...DATA.stationary_after);

    // Bars
    for (let i = 0; i < n; i++) {
        const x = padL + i * gap;
        const vb = DATA.stationary_before[i];
        const va = DATA.stationary_after[i];
        const hb = (vb / maxVal) * plotH;
        const ha = (va / maxVal) * plotH;

        // Before bar
        ctx.fillStyle = COLORS.accentRed;
        ctx.globalAlpha = 0.8;
        ctx.fillRect(x, padT + plotH - hb, barW, hb);

        // After bar
        ctx.fillStyle = COLORS.accentGreen;
        ctx.fillRect(x + barW + 2, padT + plotH - ha, barW, ha);
        ctx.globalAlpha = 1;

        // Label
        ctx.save();
        ctx.translate(x + barW, padT + plotH + 8);
        ctx.rotate(Math.PI / 4);
        ctx.font = '8px Inter';
        ctx.fillStyle = COLORS.textSecondary;
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        ctx.fillText(DATA.nodes[i].label, 0, 0);
        ctx.restore();
    }

    // Axes
    ctx.strokeStyle = COLORS.border;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padL, padT);
    ctx.lineTo(padL, padT + plotH);
    ctx.lineTo(padL + plotW, padT + plotH);
    ctx.stroke();

    // Y-axis ticks
    ctx.font = '9px JetBrains Mono';
    ctx.fillStyle = COLORS.textSecondary;
    ctx.textAlign = 'right';
    for (let i = 0; i <= 4; i++) {
        const val = (maxVal * i / 4);
        const y = padT + plotH - (plotH * i / 4);
        ctx.fillText(val.toFixed(2), padL - 5, y + 3);
        ctx.strokeStyle = COLORS.borderLight;
        ctx.beginPath();
        ctx.moveTo(padL, y);
        ctx.lineTo(padL + plotW, y);
        ctx.stroke();
    }

    // Legend
    ctx.fillStyle = COLORS.accentRed;
    ctx.fillRect(padL + plotW - 130, 10, 12, 12);
    ctx.fillStyle = COLORS.accentGreen;
    ctx.fillRect(padL + plotW - 130, 26, 12, 12);
    ctx.font = '10px Inter';
    ctx.fillStyle = COLORS.textSecondary;
    ctx.textAlign = 'left';
    ctx.fillText('Before', padL + plotW - 114, 20);
    ctx.fillText('After', padL + plotW - 114, 36);

    // Title
    ctx.font = 'bold 12px Inter';
    ctx.fillStyle = COLORS.textPrimary;
    ctx.textAlign = 'left';
    ctx.fillText('Stationary Distribution (π)', padL, 20);
}

// ═══════════════════════════════════════════════════════════════════════
// 4. MEAN FIRST PASSAGE TIME
// ═══════════════════════════════════════════════════════════════════════

function drawMFPT() {
    const canvas = document.getElementById('mfpt-canvas');
    const W = canvas.parentElement.clientWidth - 48;
    const H = 320;
    const ctx = setupCanvas(canvas, W, H);
    clearCanvas(ctx, W, H);

    if (!DATA) return;

    // Filter nodes that have MFPT > 0
    const entries = DATA.nodes.filter(n => {
        const val = DATA.mfpt_before[String(n.id)];
        return val && val > 0;
    });

    const n = entries.length;
    const padL = 130, padR = 20, padT = 40, padB = 20;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;
    const barH = plotH / n * 0.35;
    const gap = plotH / n;

    const maxVal = Math.max(
        ...entries.map(e => DATA.mfpt_before[String(e.id)] || 0),
        ...entries.map(e => DATA.mfpt_after[String(e.id)] || 0)
    );

    for (let i = 0; i < n; i++) {
        const node = entries[i];
        const y = padT + i * gap;
        const vb = DATA.mfpt_before[String(node.id)] || 0;
        const va = DATA.mfpt_after[String(node.id)] || 0;
        const wb = (vb / maxVal) * plotW;
        const wa = (va / maxVal) * plotW;

        // Before bar
        ctx.fillStyle = COLORS.accentRed;
        ctx.globalAlpha = 0.8;
        ctx.fillRect(padL, y, wb, barH);

        // After bar
        ctx.fillStyle = COLORS.accentGreen;
        ctx.fillRect(padL, y + barH + 2, wa, barH);
        ctx.globalAlpha = 1;

        // Label
        ctx.font = '9px Inter';
        ctx.fillStyle = COLORS.textSecondary;
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        ctx.fillText(node.label, padL - 8, y + barH);

        // Values
        ctx.font = '8px JetBrains Mono';
        ctx.textAlign = 'left';
        ctx.fillStyle = COLORS.textMuted;
        ctx.fillText(vb.toFixed(1), padL + wb + 4, y + barH / 2);
        ctx.fillText(va.toFixed(1), padL + wa + 4, y + barH + 2 + barH / 2);
    }

    // Legend
    ctx.fillStyle = COLORS.accentRed;
    ctx.fillRect(padL + plotW - 80, 10, 12, 12);
    ctx.fillStyle = COLORS.accentGreen;
    ctx.fillRect(padL + plotW - 80, 26, 12, 12);
    ctx.font = '10px Inter';
    ctx.fillStyle = COLORS.textSecondary;
    ctx.textAlign = 'left';
    ctx.fillText('Before', padL + plotW - 64, 20);
    ctx.fillText('After', padL + plotW - 64, 36);

    // Title
    ctx.font = 'bold 12px Inter';
    ctx.fillStyle = COLORS.textPrimary;
    ctx.textAlign = 'left';
    ctx.fillText('Mean Steps to Exit', padL, 20);
}

// ═══════════════════════════════════════════════════════════════════════
// 5. TRANSITION MATRIX
// ═══════════════════════════════════════════════════════════════════════

function drawTransitionMatrix() {
    const canvas = document.getElementById('matrix-canvas');
    const W = canvas.parentElement.clientWidth - 48;
    const H = 520;
    const ctx = setupCanvas(canvas, W, H);
    clearCanvas(ctx, W, H);

    if (!DATA) return;

    const T = currentMatrix === 'before' ?
        DATA.transition_matrix_before : DATA.transition_matrix_after;
    const n = T.length;

    const padL = 130, padR = 60, padT = 50, padB = 100;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;
    const cellW = plotW / n;
    const cellH = plotH / n;

    const maxVal = Math.max(...T.flat().filter(v => v < 0.999));

    // Draw cells
    for (let i = 0; i < n; i++) {
        for (let j = 0; j < n; j++) {
            const val = T[i][j];
            const x = padL + j * cellW;
            const y = padT + i * cellH;

            if (val > 0.001) {
                const t = val / Math.max(maxVal, 0.01);
                ctx.fillStyle = lerpColor('#161b22', '#58a6ff', Math.min(t, 1));
                ctx.fillRect(x, y, cellW - 1, cellH - 1);

                if (cellW > 20 && val > 0.02) {
                    ctx.font = '7px JetBrains Mono';
                    ctx.fillStyle = t > 0.5 ? '#fff' : COLORS.textMuted;
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillText(val.toFixed(2), x + cellW / 2, y + cellH / 2);
                }
            }
        }
    }

    // Row/column labels
    ctx.font = '8px Inter';
    ctx.fillStyle = COLORS.textSecondary;
    for (let i = 0; i < n; i++) {
        // Row labels (left)
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        ctx.fillText(DATA.nodes[i].label, padL - 6, padT + i * cellH + cellH / 2);

        // Column labels (bottom, rotated)
        ctx.save();
        ctx.translate(padL + i * cellW + cellW / 2, padT + plotH + 8);
        ctx.rotate(Math.PI / 4);
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        ctx.fillText(DATA.nodes[i].label, 0, 0);
        ctx.restore();
    }

    // Borders
    ctx.strokeStyle = COLORS.border;
    ctx.lineWidth = 1;
    ctx.strokeRect(padL, padT, plotW, plotH);

    // Title
    const matLabel = currentMatrix === 'before' ? 'Original' : 'Optimized';
    ctx.font = 'bold 12px Inter';
    ctx.fillStyle = COLORS.textPrimary;
    ctx.textAlign = 'left';
    ctx.textBaseline = 'top';
    ctx.fillText(`Transition Matrix — ${matLabel}`, padL, 15);
}

// ═══════════════════════════════════════════════════════════════════════
// 6. DISTRIBUTION LIST
// ═══════════════════════════════════════════════════════════════════════

function updateDistributionList() {
    if (!DATA) return;

    const history = currentView === 'before' ? DATA.history_before : DATA.history_after;
    const dist = history[currentTimestep];
    const container = document.getElementById('distribution-list');

    // Sort by density descending
    const sorted = DATA.nodes.map((n, i) => ({ ...n, density: dist[i], index: i }))
        .sort((a, b) => b.density - a.density);

    container.innerHTML = sorted.map(n => {
        const pct = (n.density * 100).toFixed(1);
        const barWidth = Math.min(n.density / 0.5 * 100, 100);
        const isCongested = n.density > 0.15;
        const color = NODE_COLORS[n.type] || COLORS.textSecondary;
        const barColor = isCongested ? COLORS.accentRed : color;

        return `
        <div class="dist-item ${isCongested ? 'congested' : ''}">
            <span class="type-dot" style="background:${color}"></span>
            <span class="node-name">${n.label}</span>
            <span class="node-value">${pct}%</span>
            <span class="bar-bg">
                <span class="bar-fill" style="width:${barWidth}%;background:${barColor}"></span>
            </span>
        </div>`;
    }).join('');
}

// ═══════════════════════════════════════════════════════════════════════
// 7. OBSERVATIONS
// ═══════════════════════════════════════════════════════════════════════

function generateObservations() {
    if (!DATA) return;

    const container = document.getElementById('observations-content');
    const bottleneckNames = DATA.bottlenecks.map(id => {
        const node = DATA.nodes.find(n => n.id === id);
        return node ? node.label : `Node ${id}`;
    });

    // Compute stats
    let totalReduction = 0;
    let count = 0;
    for (const bn of DATA.bottlenecks) {
        const idx = DATA.nodes.findIndex(n => n.id === bn);
        if (idx >= 0) {
            const peakB = Math.max(...DATA.history_before.map(h => h[idx]));
            const peakA = Math.max(...DATA.history_after.map(h => h[idx]));
            totalReduction += peakB - peakA;
            count++;
        }
    }
    const avgReduction = count > 0 ? (totalReduction / count * 100).toFixed(1) : '0';

    // MFPT improvement
    const nonExitNodes = DATA.nodes.filter(n => n.type !== 'exit');
    let totalMFPTBefore = 0, totalMFPTAfter = 0;
    for (const n of nonExitNodes) {
        totalMFPTBefore += DATA.mfpt_before[String(n.id)] || 0;
        totalMFPTAfter  += DATA.mfpt_after[String(n.id)]  || 0;
    }
    const mfptImprovement = totalMFPTBefore > 0 ?
        ((totalMFPTBefore - totalMFPTAfter) / totalMFPTBefore * 100).toFixed(1) : '0';

    const observations = [
        {
            icon: '⚠️',
            title: 'Bottleneck Identification',
            text: `The simulation identified <strong>${bottleneckNames.join(', ')}</strong> as the primary congestion points. These nodes see the highest cumulative crowd density across all time steps.`,
        },
        {
            icon: '📈',
            title: 'Congestion Peak Reduction',
            text: `After optimization, peak congestion at bottleneck nodes decreased by an average of <strong>${avgReduction}%</strong>. The combined strategy of exit acceleration, bottleneck relief, and path splitting distributes crowd more evenly.`,
        },
        {
            icon: '🚀',
            title: 'Faster Exit Times',
            text: `Mean steps to exit improved by <strong>${mfptImprovement}%</strong> on average across all non-exit nodes. The optimized transition matrix accelerates pedestrian flow toward exits.`,
        },
        {
            icon: '📊',
            title: 'Stationary Distribution',
            text: `In the long run (stationary state), crowd mass concentrates at <strong>exit nodes</strong> (absorbing states). The optimization shifts this convergence earlier, reducing transient congestion.`,
        },
        {
            icon: '🔁',
            title: 'Markov Property',
            text: `The memoryless property of Markov chains means each person's next location depends only on their current position. This simplification enables tractable analysis while capturing realistic flow patterns.`,
        },
        {
            icon: '🗺️',
            title: 'Graph Structure Impact',
            text: `The metro station's graph topology directly determines flow capacity. Nodes with high degree (many connections) and nodes on critical paths naturally become bottlenecks, confirming graph-theoretic predictions.`,
        },
    ];

    container.innerHTML = observations.map(o => `
        <div class="observation-item">
            <span class="obs-icon">${o.icon}</span>
            <div>
                <h4>${o.title}</h4>
                <p>${o.text}</p>
            </div>
        </div>
    `).join('');
}

// ═══════════════════════════════════════════════════════════════════════
// EVENT HANDLERS
// ═══════════════════════════════════════════════════════════════════════

// Time slider
document.getElementById('time-slider').addEventListener('input', (e) => {
    currentTimestep = parseInt(e.target.value);
    document.getElementById('time-value').textContent = `t = ${currentTimestep}`;
    drawGraph();
    drawHeatmap();
    updateDistributionList();
});

// Speed slider
document.getElementById('speed-slider').addEventListener('input', (e) => {
    animSpeed = parseInt(e.target.value);
    document.getElementById('speed-value').textContent = `${animSpeed}ms`;
    if (isPlaying) {
        clearInterval(playInterval);
        startPlayback();
    }
});

// Play / Pause / Reset
document.getElementById('btn-play').addEventListener('click', () => {
    if (!isPlaying) startPlayback();
});

document.getElementById('btn-pause').addEventListener('click', () => {
    stopPlayback();
});

document.getElementById('btn-reset').addEventListener('click', () => {
    stopPlayback();
    currentTimestep = 0;
    document.getElementById('time-slider').value = 0;
    document.getElementById('time-value').textContent = 't = 0';
    drawGraph();
    drawHeatmap();
    updateDistributionList();
});

function startPlayback() {
    isPlaying = true;
    document.getElementById('btn-play').textContent = '▶ Playing...';
    playInterval = setInterval(() => {
        if (currentTimestep >= DATA.n_steps) {
            stopPlayback();
            return;
        }
        currentTimestep++;
        document.getElementById('time-slider').value = currentTimestep;
        document.getElementById('time-value').textContent = `t = ${currentTimestep}`;
        drawGraph();
        drawHeatmap();
        updateDistributionList();
    }, animSpeed);
}

function stopPlayback() {
    isPlaying = false;
    clearInterval(playInterval);
    document.getElementById('btn-play').textContent = '▶ Play';
}

// View toggles (graph: before/after)
document.getElementById('btn-view-before').addEventListener('click', () => {
    currentView = 'before';
    document.getElementById('btn-view-before').classList.add('active');
    document.getElementById('btn-view-after').classList.remove('active');
    drawGraph();
    updateDistributionList();
});

document.getElementById('btn-view-after').addEventListener('click', () => {
    currentView = 'after';
    document.getElementById('btn-view-after').classList.add('active');
    document.getElementById('btn-view-before').classList.remove('active');
    drawGraph();
    updateDistributionList();
});

// Heatmap toggles
document.querySelectorAll('[data-heatmap]').forEach(btn => {
    btn.addEventListener('click', () => {
        currentHeatmap = btn.dataset.heatmap;
        document.querySelectorAll('[data-heatmap]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        drawHeatmap();
    });
});

// Matrix toggles
document.querySelectorAll('[data-matrix]').forEach(btn => {
    btn.addEventListener('click', () => {
        currentMatrix = btn.dataset.matrix;
        document.querySelectorAll('[data-matrix]').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        drawTransitionMatrix();
    });
});

// Resize handler
let resizeTimeout;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        drawGraph();
        drawHeatmap();
        drawStationary();
        drawMFPT();
        drawTransitionMatrix();
    }, 150);
});

// ═══════════════════════════════════════════════════════════════════════
// INITIALIZE
// ═══════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', loadData);
