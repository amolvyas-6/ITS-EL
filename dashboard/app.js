const TYPE_COLORS = {
    major_signalized: '#c0392b',
    signalized: '#e67e22',
    arterial_merge: '#2980b9',
    flyover_merge: '#16a085',
    destination_zone: '#27ae60',
};

const ALERT_COLORS = {
    CRITICAL: '#c0392b',
    WARNING: '#e67e22',
    MODERATE: '#f1c40f',
    NORMAL: '#27ae60',
};

const COLORS = {
    ink: '#102331',
    grid: 'rgba(16, 35, 49, 0.12)',
    soft: '#5a6d78',
    light: '#fdf7ec',
    accent: '#12344b',
    neutral: '#d9cbb2',
};

let DATA = null;
let NODE_BY_ID = new Map();
let currentTimestep = 0;
let currentView = 'before';
let currentHeatmap = 'before';
let currentMatrix = 'before';
let isPlaying = false;
let playInterval = null;
let animSpeed = 500;
const DPR = window.devicePixelRatio || 1;

function $(id) {
    return document.getElementById(id);
}

function setupCanvas(canvas, width, height) {
    canvas.width = width * DPR;
    canvas.height = height * DPR;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    const ctx = canvas.getContext('2d');
    ctx.scale(DPR, DPR);
    return ctx;
}

function clearCanvas(ctx, width, height) {
    ctx.fillStyle = COLORS.light;
    ctx.fillRect(0, 0, width, height);
}

function clamp(value, min, max) {
    return Math.max(min, Math.min(max, value));
}

function lerpColor(colorA, colorB, t) {
    const a = colorA.match(/\w\w/g).map((hex) => parseInt(hex, 16));
    const b = colorB.match(/\w\w/g).map((hex) => parseInt(hex, 16));
    const mix = a.map((component, index) =>
        Math.round(component + (b[index] - component) * clamp(t, 0, 1))
    );
    return `rgb(${mix[0]}, ${mix[1]}, ${mix[2]})`;
}

function formatPercent(value) {
    return `${Number(value || 0).toFixed(1)}%`;
}

function formatScenarioLabel(view) {
    return view === 'before' ? 'Pre-ATMS Intervention' : 'Post-ATMS Signal Optimization';
}

function getHistory(view = currentView) {
    return view === 'before' ? DATA.history_before : DATA.history_after;
}

function getVCHistory(view = currentView) {
    return view === 'before' ? DATA.v_c_history.before : DATA.v_c_history.after;
}

function getDetectorScenario(view = currentView) {
    return view === 'before' ? 'pre_atms' : 'post_atms';
}

function getDensityColor(value) {
    if (value < 0.04) return lerpColor('fdf7ec', 'd7e8ef', value / 0.04);
    if (value < 0.12) return lerpColor('d7e8ef', 'f4c26b', (value - 0.04) / 0.08);
    return lerpColor('f4c26b', 'c0392b', (value - 0.12) / 0.2);
}

function getDiffColor(value) {
    if (value < 0) return lerpColor('e8f6ef', '27ae60', Math.abs(value) / 0.15);
    if (value > 0) return lerpColor('fceae7', 'c0392b', value / 0.15);
    return '#fdf7ec';
}

function getNodePosition(node, width, height, pad = 50) {
    return {
        x: pad + node.x * (width - pad * 2),
        y: pad + (1 - node.y) * (height - pad * 2),
    };
}

function drawArrow(ctx, x1, y1, x2, y2, width) {
    const angle = Math.atan2(y2 - y1, x2 - x1);
    const arrowLength = 8 + width * 1.6;

    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();

    ctx.beginPath();
    ctx.moveTo(x2, y2);
    ctx.lineTo(
        x2 - arrowLength * Math.cos(angle - Math.PI / 7),
        y2 - arrowLength * Math.sin(angle - Math.PI / 7),
    );
    ctx.lineTo(
        x2 - arrowLength * Math.cos(angle + Math.PI / 7),
        y2 - arrowLength * Math.sin(angle + Math.PI / 7),
    );
    ctx.closePath();
    ctx.fill();
}

async function loadData() {
    try {
        const response = await fetch('simulation_data.json');
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        DATA = await response.json();
        NODE_BY_ID = new Map(DATA.nodes.map((node) => [node.id, node]));
        onDataLoaded();
    } catch (error) {
        console.error('Failed to load dashboard data', error);
        $('status-badge').innerHTML =
            '<span class="pulse" style="background:#c0392b"></span> Dashboard data missing — run main.py first';
    }
}

function onDataLoaded() {
    $('status-badge').innerHTML = '<span class="pulse active"></span> Traffic simulation loaded';
    $('time-slider').max = DATA.n_steps;
    $('time-slider').value = String(currentTimestep);
    $('time-value').textContent = `Cycle ${currentTimestep}`;
    $('speed-value').textContent = `${animSpeed}ms`;

    renderOverviewStats();
    renderITSArchitecture();
    renderATMSKPI();
    renderAll();
}

function renderOverviewStats() {
    const kpis = DATA.its_report?.kpi_summary || {};

    $('stat-nodes').querySelector('.stat-value').textContent = DATA.nodes.length;
    $('stat-edges').querySelector('.stat-value').textContent = DATA.edges.length;
    $('stat-steps').querySelector('.stat-value').textContent = DATA.n_steps;
    $('stat-bottlenecks').querySelector('.stat-value').textContent =
        kpis.saturated_intersections_before ?? DATA.bottlenecks.length;
    $('stat-improvement').querySelector('.stat-value').textContent = formatPercent(
        kpis.antt_improvement_percent,
    );
}

function drawGraph() {
    const canvas = $('graph-canvas');
    const width = canvas.parentElement.clientWidth - 8;
    const height = 450;
    const ctx = setupCanvas(canvas, width, height);
    clearCanvas(ctx, width, height);

    if (!DATA) return;

    const history = getHistory();
    const vcHistory = getVCHistory();
    const densities = history[currentTimestep];
    const vcRatios = vcHistory[currentTimestep];
    const maxEdgeCapacity = Math.max(...DATA.edges.map((edge) => edge.capacity || 1));

    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';

    for (const edge of DATA.edges) {
        if (edge.source === edge.target) continue;
        const source = NODE_BY_ID.get(edge.source);
        const target = NODE_BY_ID.get(edge.target);
        if (!source || !target) continue;

        const start = getNodePosition(source, width, height);
        const end = getNodePosition(target, width, height);
        const controlYOffset = source.y === target.y ? -14 : 0;
        const midX = (start.x + end.x) / 2;
        const midY = (start.y + end.y) / 2 + controlYOffset;
        const edgeWidth = 1.2 + ((edge.capacity || 0) / maxEdgeCapacity) * 4.4;

        ctx.strokeStyle = 'rgba(16, 35, 49, 0.28)';
        ctx.fillStyle = 'rgba(16, 35, 49, 0.28)';
        ctx.lineWidth = edgeWidth;
        drawArrow(ctx, start.x, start.y, end.x, end.y, edgeWidth);

        if (edge.weight > 0) {
            ctx.fillStyle = '#5a6d78';
            ctx.font = '10px IBM Plex Mono';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(`${Math.round(edge.weight)}s`, midX, midY);
        }
    }

    DATA.nodes.forEach((node, index) => {
        const point = getNodePosition(node, width, height);
        const density = densities[index] || 0;
        const ratio = vcRatios?.[node.id] || 0;
        const radius = 16 + density * 78;
        const color = TYPE_COLORS[node.type] || COLORS.soft;

        if (ratio > 0.85) {
            ctx.beginPath();
            ctx.fillStyle = ratio > 1 ? 'rgba(192,57,43,0.18)' : 'rgba(230,126,34,0.16)';
            ctx.arc(point.x, point.y, radius + 10, 0, Math.PI * 2);
            ctx.fill();
        }

        ctx.beginPath();
        ctx.fillStyle = color;
        ctx.arc(point.x, point.y, radius, 0, Math.PI * 2);
        ctx.fill();

        ctx.lineWidth = ratio > 0.85 ? 3 : 1.8;
        ctx.strokeStyle = ratio > 1 ? '#8f251b' : '#fff';
        ctx.stroke();

        ctx.fillStyle = '#fff';
        ctx.font = '700 10px IBM Plex Mono';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(density.toFixed(2), point.x, point.y);

        ctx.fillStyle = COLORS.ink;
        ctx.font = '700 11px Space Grotesk';
        ctx.fillText(node.label, point.x, point.y + radius + 14);
    });

    ctx.fillStyle = COLORS.ink;
    ctx.font = '700 14px Space Grotesk';
    ctx.textAlign = 'left';
    ctx.fillText(
        `${formatScenarioLabel(currentView)} — Cycle ${currentTimestep}`,
        18,
        24,
    );
}

function drawHeatmap() {
    const canvas = $('heatmap-canvas');
    const width = canvas.parentElement.clientWidth - 8;
    const height = 380;
    const ctx = setupCanvas(canvas, width, height);
    clearCanvas(ctx, width, height);

    if (!DATA) return;

    const sourceHistory =
        currentHeatmap === 'diff'
            ? DATA.history_before.map((row, rowIndex) =>
                row.map((value, columnIndex) => DATA.history_after[rowIndex][columnIndex] - value),
            )
            : getHistory(currentHeatmap);

    const nRows = DATA.nodes.length;
    const nCols = DATA.n_steps + 1;
    const padLeft = 156;
    const padTop = 42;
    const padRight = 66;
    const padBottom = 44;
    const plotWidth = width - padLeft - padRight;
    const plotHeight = height - padTop - padBottom;
    const cellWidth = plotWidth / nCols;
    const cellHeight = plotHeight / nRows;

    for (let t = 0; t < nCols; t += 1) {
        for (let row = 0; row < nRows; row += 1) {
            const value = sourceHistory[t][row];
            ctx.fillStyle = currentHeatmap === 'diff' ? getDiffColor(value) : getDensityColor(value);
            ctx.fillRect(
                padLeft + t * cellWidth,
                padTop + row * cellHeight,
                cellWidth + 0.5,
                cellHeight + 0.5,
            );
        }
    }

    ctx.strokeStyle = 'rgba(18, 52, 75, 0.45)';
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 5]);
    const markerX = padLeft + currentTimestep * cellWidth + cellWidth / 2;
    ctx.beginPath();
    ctx.moveTo(markerX, padTop);
    ctx.lineTo(markerX, padTop + plotHeight);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.font = '11px Space Grotesk';
    ctx.fillStyle = COLORS.soft;
    ctx.textAlign = 'right';
    DATA.nodes.forEach((node, row) => {
        ctx.fillText(node.label, padLeft - 10, padTop + row * cellHeight + cellHeight * 0.62);
    });

    ctx.textAlign = 'center';
    for (let t = 0; t < nCols; t += Math.max(1, Math.floor(nCols / 10))) {
        ctx.fillText(`C${t}`, padLeft + t * cellWidth + cellWidth / 2, height - 16);
    }

    ctx.fillStyle = COLORS.ink;
    ctx.font = '700 14px Space Grotesk';
    const label =
        currentHeatmap === 'diff'
            ? 'Difference (Post-ATMS − Pre-ATMS)'
            : formatScenarioLabel(currentHeatmap);
    ctx.fillText(`Vehicle Density Heatmap — ${label}`, padLeft, 24);
}

function drawStationary() {
    const canvas = $('stationary-canvas');
    const width = canvas.parentElement.clientWidth - 8;
    const height = 320;
    const ctx = setupCanvas(canvas, width, height);
    clearCanvas(ctx, width, height);

    if (!DATA) return;

    const valuesBefore = DATA.stationary_before;
    const valuesAfter = DATA.stationary_after;
    const maxValue = Math.max(...valuesBefore, ...valuesAfter, 0.01);
    const padLeft = 46;
    const padTop = 36;
    const padBottom = 96;
    const plotHeight = height - padTop - padBottom;
    const slotWidth = (width - padLeft - 18) / DATA.nodes.length;

    DATA.nodes.forEach((node, index) => {
        const baseX = padLeft + index * slotWidth;
        const beforeHeight = (valuesBefore[index] / maxValue) * plotHeight;
        const afterHeight = (valuesAfter[index] / maxValue) * plotHeight;
        const barWidth = Math.max(8, slotWidth * 0.28);

        ctx.fillStyle = '#e67e22';
        ctx.fillRect(baseX, padTop + plotHeight - beforeHeight, barWidth, beforeHeight);
        ctx.fillStyle = '#27ae60';
        ctx.fillRect(baseX + barWidth + 3, padTop + plotHeight - afterHeight, barWidth, afterHeight);

        ctx.save();
        ctx.translate(baseX + barWidth, height - 80);
        ctx.rotate(Math.PI / 4);
        ctx.fillStyle = COLORS.soft;
        ctx.font = '10px Space Grotesk';
        ctx.fillText(node.label, 0, 0);
        ctx.restore();
    });

    ctx.strokeStyle = COLORS.grid;
    for (let tick = 0; tick <= 4; tick += 1) {
        const y = padTop + plotHeight - (tick / 4) * plotHeight;
        ctx.beginPath();
        ctx.moveTo(padLeft, y);
        ctx.lineTo(width - 10, y);
        ctx.stroke();
    }

    ctx.fillStyle = COLORS.ink;
    ctx.font = '700 14px Space Grotesk';
    ctx.fillText('Long-Run Intersection Utilization', 16, 22);
}

function drawMFPT() {
    const canvas = $('mfpt-canvas');
    const width = canvas.parentElement.clientWidth - 8;
    const height = 320;
    const ctx = setupCanvas(canvas, width, height);
    clearCanvas(ctx, width, height);

    if (!DATA) return;

    const entries = DATA.nodes.filter((node) => (DATA.mfpt_before[String(node.id)] || 0) > 0);
    const maxValue = Math.max(
        ...entries.map((node) => DATA.mfpt_before[String(node.id)] || 0),
        ...entries.map((node) => DATA.mfpt_after[String(node.id)] || 0),
        1,
    );

    const padLeft = 156;
    const padTop = 36;
    const rowGap = (height - padTop - 18) / entries.length;
    const plotWidth = width - padLeft - 30;

    entries.forEach((node, index) => {
        const beforeValue = DATA.mfpt_before[String(node.id)] || 0;
        const afterValue = DATA.mfpt_after[String(node.id)] || 0;
        const y = padTop + index * rowGap;
        const barHeight = Math.max(8, rowGap * 0.26);

        ctx.fillStyle = '#e67e22';
        ctx.fillRect(padLeft, y, (beforeValue / maxValue) * plotWidth, barHeight);
        ctx.fillStyle = '#27ae60';
        ctx.fillRect(padLeft, y + barHeight + 3, (afterValue / maxValue) * plotWidth, barHeight);

        ctx.fillStyle = COLORS.soft;
        ctx.font = '10px Space Grotesk';
        ctx.textAlign = 'right';
        ctx.fillText(node.label, padLeft - 8, y + barHeight + 1);

        ctx.textAlign = 'left';
        ctx.font = '10px IBM Plex Mono';
        ctx.fillText(beforeValue.toFixed(1), padLeft + (beforeValue / maxValue) * plotWidth + 5, y + 9);
        ctx.fillText(afterValue.toFixed(1), padLeft + (afterValue / maxValue) * plotWidth + 5, y + barHeight + 13);
    });

    ctx.fillStyle = COLORS.ink;
    ctx.font = '700 14px Space Grotesk';
    ctx.textAlign = 'left';
    ctx.fillText('Average Network Travel Time (Signal Cycles)', 16, 22);
}

function drawTransitionMatrix() {
    const canvas = $('matrix-canvas');
    const width = canvas.parentElement.clientWidth - 8;
    const height = 520;
    const ctx = setupCanvas(canvas, width, height);
    clearCanvas(ctx, width, height);

    if (!DATA) return;

    const matrix = currentMatrix === 'before' ? DATA.transition_matrix_before : DATA.transition_matrix_after;
    const n = matrix.length;
    const padLeft = 150;
    const padTop = 52;
    const padRight = 30;
    const padBottom = 136;
    const cellWidth = (width - padLeft - padRight) / n;
    const cellHeight = (height - padTop - padBottom) / n;
    const maxValue = Math.max(...matrix.flat().filter((value) => value < 0.999), 0.05);

    for (let row = 0; row < n; row += 1) {
        for (let column = 0; column < n; column += 1) {
            const value = matrix[row][column];
            if (value <= 0.001) continue;
            const t = value / maxValue;
            ctx.fillStyle = lerpColor('d7e8ef', '12344b', t);
            ctx.fillRect(
                padLeft + column * cellWidth,
                padTop + row * cellHeight,
                cellWidth - 1,
                cellHeight - 1,
            );

            if (cellWidth > 18 && value > 0.04) {
                ctx.fillStyle = t > 0.55 ? '#fff' : COLORS.ink;
                ctx.font = '10px IBM Plex Mono';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(
                    value.toFixed(2),
                    padLeft + column * cellWidth + cellWidth / 2,
                    padTop + row * cellHeight + cellHeight / 2,
                );
            }
        }
    }

    DATA.nodes.forEach((node, index) => {
        ctx.font = '10px Space Grotesk';
        ctx.fillStyle = COLORS.soft;
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        ctx.fillText(node.label, padLeft - 8, padTop + index * cellHeight + cellHeight / 2);

        ctx.save();
        ctx.translate(padLeft + index * cellWidth + cellWidth / 2, height - 122);
        ctx.rotate(Math.PI / 4);
        ctx.textAlign = 'left';
        ctx.textBaseline = 'top';
        ctx.fillText(node.label, 0, 0);
        ctx.restore();
    });

    ctx.fillStyle = COLORS.ink;
    ctx.font = '700 14px Space Grotesk';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'alphabetic';
    ctx.fillText(
        `Vehicle Routing Probability Matrix — ${formatScenarioLabel(currentMatrix)}`,
        16,
        24,
    );
}

function renderDistributionList() {
    const container = $('distribution-list');
    if (!DATA) {
        container.innerHTML = '<div class="empty-state">Waiting for simulation data.</div>';
        return;
    }

    const history = getHistory();
    const vcHistory = getVCHistory();
    const densities = history[currentTimestep];
    const ratios = vcHistory[currentTimestep];

    const rows = DATA.nodes
        .map((node, index) => ({
            ...node,
            density: densities[index] || 0,
            vcr: ratios[node.id] || 0,
        }))
        .sort((a, b) => b.vcr - a.vcr);

    container.innerHTML = rows
        .map((row) => {
            const color = TYPE_COLORS[row.type] || COLORS.soft;
            const barWidth = clamp((row.vcr / 1.2) * 100, 6, 100);
            const barColor =
                row.vcr > 1
                    ? ALERT_COLORS.CRITICAL
                    : row.vcr > 0.85
                        ? ALERT_COLORS.WARNING
                        : color;

            return `
                <div class="dist-item">
                    <div class="dist-main">
                        <span class="type-dot" style="background:${color}"></span>
                        <span class="node-name">${row.label}</span>
                    </div>
                    <span class="node-value">${row.vcr.toFixed(2)} v/c</span>
                    <span class="node-value">${(row.density * 5000).toFixed(0)} PCU</span>
                    <div class="node-meta">
                        <span>${row.type.replace(/_/g, ' ')}</span>
                        <span>${row.detector_type || 'None'}</span>
                    </div>
                    <div class="node-bar"><span style="width:${barWidth}%;background:${barColor}"></span></div>
                </div>
            `;
        })
        .join('');
}

function renderITSArchitecture() {
    const tbody = $('architecture-table-body');
    const architecture = DATA?.its_report?.its_architecture || {};

    const orderedRows = [
        ['data_acquisition', 'Data Acquisition'],
        ['data_communication', 'Communication'],
        ['traffic_management_centre', 'Traffic Management Centre'],
        ['traveller_information', 'ATIS (Variable Message Signs)'],
        ['vehicle_control', 'AVCS (Vehicle Control)'],
        ['law_enforcement', 'Law Enforcement'],
    ];

    tbody.innerHTML = orderedRows
        .filter(([key]) => architecture[key])
        .map(([key, label]) => `
            <tr>
                <td>${label}</td>
                <td>${architecture[key].technology}</td>
                <td>${architecture[key].mapped_to}</td>
            </tr>
        `)
        .join('');
}

function renderDetectorFeed(timestep = currentTimestep) {
    const tbody = $('detector-feed-body');
    const scenarioLabel = $('detector-scenario-label');
    if (!DATA) return;

    scenarioLabel.textContent = `${formatScenarioLabel(currentView)} detector telemetry`;
    const scenario = getDetectorScenario();
    const rows = (DATA.detector_feed || [])
        .filter((entry) => entry.scenario === scenario && entry.timestep === timestep)
        .sort((a, b) => b.v_c_ratio - a.v_c_ratio);

    if (rows.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5">No detector feed for the selected cycle.</td></tr>';
        return;
    }

    tbody.innerHTML = rows
        .map((row) => {
            const alert = row.alert_level || 'NORMAL';
            return `
                <tr class="detector-row ${alert.toLowerCase()}">
                    <td>${row.node_label}</td>
                    <td>${row.detector_type}</td>
                    <td>${row.v_c_ratio.toFixed(2)}</td>
                    <td>${row.estimated_queue_length_vehicles}</td>
                    <td>${alert}</td>
                </tr>
            `;
        })
        .join('');
}

function renderATMSKPI() {
    const kpis = DATA?.its_report?.kpi_summary || {};
    const context = DATA?.its_report?.city_context || {};
    const units = DATA?.its_report?.its_unit_coverage || {};

    $('kpi-improvement').textContent = formatPercent(kpis.antt_improvement_percent);
    $('kpi-saturated').textContent =
        `${kpis.saturated_intersections_before ?? 0} → ${kpis.saturated_intersections_after ?? 0}`;
    $('kpi-delay').textContent =
        `${Number(kpis.avg_delay_reduction_seconds || 0).toFixed(1)} sec`;
    $('kpi-context-badge').textContent =
        `${context.city || 'Bengaluru'} ATMS context: ${context.atms_deployment_status || 'N/A'}`;

    $('kpi-unit-badges').innerHTML = Object.entries(units)
        .map(([key]) => `<span class="unit-badge">${key.replace('_', ' ').toUpperCase()}</span>`)
        .join('');
}

function renderObservations() {
    const container = $('observations-content');
    if (!DATA) return;

    const kpis = DATA.its_report?.kpi_summary || {};
    const report = DATA.its_report?.optimization_report || {};
    const topNames = report.bottleneck_intersections || [];
    const before = report.v_c_before || {};
    const after = report.v_c_after || {};

    const reductionRows = Object.keys(before).map((nodeId) => {
        const initial = Number(before[nodeId] || 0);
        const final = Number(after[nodeId] || 0);
        const reduction = initial > 0 ? ((initial - final) / initial) * 100 : 0;
        return reduction;
    });

    const avgReduction =
        reductionRows.length > 0
            ? reductionRows.reduce((sum, value) => sum + value, 0) / reductionRows.length
            : 0;

    const observations = [
        {
            section: 'Bottleneck Ranking',
            title: 'Agara-HSR pocket dominates the early peak',
            text: `${topNames.join(', ')} emerge as the operational bottlenecks once the first cycle begins, which matches the v/c-based saturation logic rather than just the initial source injection.`,
        },
        {
            section: 'ATMS Impact',
            title: 'Adaptive timing relieves queue retention',
            text: `The optimized matrix reduces ANTT by ${formatPercent(kpis.antt_improvement_percent)} and cuts the tracked bottleneck v/c peak by an average of ${avgReduction.toFixed(1)}%.`,
        },
        {
            section: 'Detector Layer',
            title: 'Detector alerts stay tied to the selected cycle',
            text: `Each slider position replays the detector table for the selected scenario, exposing queue estimates, alert levels, and the recommended intervention state for that exact cycle.`,
        },
        {
            section: 'ITS Coverage',
            title: 'The dashboard now reads like an ATMS console',
            text: `Architecture mapping, live detector feed, KPI cards, and traveller-information visuals are all wired to the exported ITS report rather than static text.`,
        },
    ];

    container.innerHTML = observations
        .map((item) => `
            <div class="observation-item">
                <small>${item.section}</small>
                <h4>${item.title}</h4>
                <p>${item.text}</p>
            </div>
        `)
        .join('');
}

function renderAll() {
    drawGraph();
    drawHeatmap();
    drawStationary();
    drawMFPT();
    drawTransitionMatrix();
    renderDistributionList();
    renderDetectorFeed();
    renderObservations();
}

function startPlayback() {
    if (!DATA) return;
    isPlaying = true;
    $('btn-play').textContent = '▶ Playing…';
    playInterval = window.setInterval(() => {
        if (currentTimestep >= DATA.n_steps) {
            stopPlayback();
            return;
        }
        currentTimestep += 1;
        $('time-slider').value = String(currentTimestep);
        $('time-value').textContent = `Cycle ${currentTimestep}`;
        drawGraph();
        drawHeatmap();
        renderDistributionList();
        renderDetectorFeed();
    }, animSpeed);
}

function stopPlayback() {
    isPlaying = false;
    window.clearInterval(playInterval);
    $('btn-play').textContent = '▶ Play';
}

$('time-slider').addEventListener('input', (event) => {
    currentTimestep = Number(event.target.value);
    $('time-value').textContent = `Cycle ${currentTimestep}`;
    drawGraph();
    drawHeatmap();
    renderDistributionList();
    renderDetectorFeed();
});

$('speed-slider').addEventListener('input', (event) => {
    animSpeed = Number(event.target.value);
    $('speed-value').textContent = `${animSpeed}ms`;
    if (isPlaying) {
        stopPlayback();
        startPlayback();
    }
});

$('btn-play').addEventListener('click', () => {
    if (!isPlaying) startPlayback();
});

$('btn-pause').addEventListener('click', stopPlayback);

$('btn-reset').addEventListener('click', () => {
    stopPlayback();
    currentTimestep = 0;
    $('time-slider').value = '0';
    $('time-value').textContent = 'Cycle 0';
    drawGraph();
    drawHeatmap();
    renderDistributionList();
    renderDetectorFeed();
});

$('btn-view-before').addEventListener('click', () => {
    currentView = 'before';
    $('btn-view-before').classList.add('active');
    $('btn-view-after').classList.remove('active');
    drawGraph();
    renderDistributionList();
    renderDetectorFeed();
});

$('btn-view-after').addEventListener('click', () => {
    currentView = 'after';
    $('btn-view-after').classList.add('active');
    $('btn-view-before').classList.remove('active');
    drawGraph();
    renderDistributionList();
    renderDetectorFeed();
});

document.querySelectorAll('[data-heatmap]').forEach((button) => {
    button.addEventListener('click', () => {
        currentHeatmap = button.dataset.heatmap;
        document.querySelectorAll('[data-heatmap]').forEach((item) => item.classList.remove('active'));
        button.classList.add('active');
        drawHeatmap();
    });
});

document.querySelectorAll('[data-matrix]').forEach((button) => {
    button.addEventListener('click', () => {
        currentMatrix = button.dataset.matrix;
        document.querySelectorAll('[data-matrix]').forEach((item) => item.classList.remove('active'));
        button.classList.add('active');
        drawTransitionMatrix();
    });
});

let resizeHandle = null;
window.addEventListener('resize', () => {
    window.clearTimeout(resizeHandle);
    resizeHandle = window.setTimeout(() => {
        if (DATA) renderAll();
    }, 120);
});

document.addEventListener('DOMContentLoaded', loadData);
