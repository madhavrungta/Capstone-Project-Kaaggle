/**
 * VyaparSathi v2.0  Frontend Application Logic
 * ============================================
 * Features:
 *    Typewriter animation on hero title
 *    Form submission  SSE stream from the agent backend
 *    Real-time console log rendering (inc. critic logs)
 *    Animated stats counter bar
 *    Dynamic dashboard: competitors, SWOT, gaps, recs
 *    Confidence badges & cluster tags on cards
 *    Chart.js growth chart + Price-vs-Quality quadrant
 *    Final Scorecard with Go/No-Go
 *    Research Trace transparency card
 *    Competitor comparison mode (head-to-head)
 *    PDF report export
 *    Research history (localStorage)
 *    Enhanced 90-day strategy simulator
 *    Demo mode with pre-loaded samples
 *    Parallax scroll for floating icons
 *    Honest error handling (no fake "Complete")
 */

//  State 
let currentTaskId = null;
let currentReport = null;
let currentNiche = "";
let currentLocation = "";
const PHASES_TOTAL = 9; // now 9 phases with critic
let phasesCompleted = 0;
let researchStartTime = null;
let compareMode = false;
let selectedForCompare = [];
let reportReceived = false; // Item 2: track success

//  DOM References 
const researchForm   = document.getElementById("researchForm");
const startBtn       = document.getElementById("startBtn");
const btnContent     = document.getElementById("btnContent");
const btnLoading     = document.getElementById("btnLoading");
const consoleSection = document.getElementById("consoleSection");
const consoleBody    = document.getElementById("consoleBody");
const consoleStatus  = document.getElementById("consoleStatus");
const progressBar    = document.getElementById("progressBar");
const resultsSection = document.getElementById("resultsSection");
const simulateBtn    = document.getElementById("simulateBtn");
const scenarioInput  = document.getElementById("scenarioInput");
const simResults     = document.getElementById("simResults");
const simBtnText     = document.getElementById("simBtnText");
const simBtnLoader   = document.getElementById("simBtnLoader");


// 
//  TYPEWRITER ANIMATION 
// 
(function initTypewriter() {
    const el = document.getElementById("heroHighlight");
    if (!el) return;
    const text = "Automated.";
    let i = 0;
    function type() {
        if (i <= text.length) {
            el.textContent = text.slice(0, i);
            i++;
            setTimeout(type, 90);
        }
    }
    setTimeout(type, 600);
})();


// 
//  PARALLAX SCROLL FOR FLOATING ICONS 
// 
(function initParallax() {
    const layer = document.querySelector(".floating-icons-layer");
    if (!layer) return;
    let ticking = false;
    window.addEventListener("scroll", () => {
        if (!ticking) {
            requestAnimationFrame(() => {
                const scrollY = window.scrollY;
                const icons = layer.querySelectorAll(".fi");
                icons.forEach(icon => {
                    let speed = 0.02;
                    if (icon.classList.contains("parallax-mid")) speed = 0.04;
                    if (icon.classList.contains("parallax-fast")) speed = 0.06;
                    icon.style.transform = `translateY(${-scrollY * speed}px)`;
                });
                ticking = false;
            });
            ticking = true;
        }
    });
})();


// 
//  FORM SUiMISSION 
// 
researchForm.addEventListener("submit", async (e) => {
    e.preventDefault();

    const niche    = document.getElementById("niche").value.trim();
    const location = document.getElementById("location").value.trim();
    const businessSize   = document.getElementById("business_size")?.value.trim();
    const budgetRange    = document.getElementById("budget_range")?.value.trim();
    const competitorType = document.getElementById("competitor_type")?.value.trim();
    const customKeywords = document.getElementById("custom_keywords")?.value.trim();
    if (!niche || !location) return;

    currentNiche = niche;
    currentLocation = location;

    // Reset state
    phasesCompleted = 0;
    currentReport   = null;
    reportReceived  = false;
    researchStartTime = Date.now();
    consoleBody.innerHTML = "";
    resultsSection.style.display = "none";
    progressBar.style.width = "0%";
    const statsSection = document.getElementById("statsbarSection");
    if (statsSection) statsSection.style.display = "none";

    // Reset compare mode
    compareMode = false;
    selectedForCompare = [];
    const ct = document.getElementById("compareToggle");
    if (ct) ct.classList.remove("active");

    // Toggle UI
    btnContent.style.display  = "none";
    btnLoading.style.display  = "flex";
    startBtn.disabled = true;
    consoleSection.style.display = "block";
    consoleStatus.textContent = " Running";
    consoleStatus.classList.remove("done", "failed");

    try {
        const response = await fetch("/api/research", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ niche, location, business_size: businessSize, budget_range: budgetRange, competitor_type: competitorType, custom_keywords: customKeywords }),
        });

        currentTaskId = response.headers.get("X-Task-Id");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() || "";
            for (const line of lines) {
                if (!line.startsWith("data: ")) continue;
                const jsonStr = line.slice(6).trim();
                if (!jsonStr) continue;
                try {
                    const event = JSON.parse(jsonStr);
                    handleEvent(event);
                } catch (_) {}
            }
        }
    } catch (err) {
        appendLog(` Connection error: ${err.message}`, "error");
    } finally {
        btnContent.style.display  = "flex";
        btnLoading.style.display  = "none";
        startBtn.disabled = false;

        // Item 2: Honest status  show Failed if no report received
        if (reportReceived) {
            consoleStatus.textContent = " Complete";
            consoleStatus.classList.add("done");
        } else {
            consoleStatus.textContent = " Failed";
            consoleStatus.classList.add("failed");
        }
        progressBar.style.width = "100%";
    }
});


//  Event Router 
function handleEvent(event) {
    if (event.type === "log") {
        appendLog(event.message, event.level);
        if (event.level === "phase") {
            phasesCompleted++;
            const pct = Math.min((phasesCompleted / PHASES_TOTAL) * 100, 95);
            progressBar.style.width = pct + "%";
        }
    } else if (event.type === "report") {
        reportReceived = true;
        currentReport = event.data;
        renderReport(event.data);
        showStatsbar(event.data);
        saveToHistory(event.data);
    } else if (event.type === "error") {
        appendLog(` Error: ${event.message}`, "error");
    }
}

//  Console Logger 
function appendLog(message, level = "info") {
    const el = document.createElement("div");
    el.className = `log-line log-${level}`;
    el.textContent = `> ${message}`;
    consoleBody.appendChild(el);
    consoleBody.scrollTop = consoleBody.scrollHeight;
}


// 
//  REPORT RENDERER 
// 
function renderReport(report) {
    // Executive Summary
    document.getElementById("executiveSummary").textContent =
        report.executive_summary || "No summary available.";

    const badge = document.getElementById("intensityBadge");
    const intensity = (report.competitive_intensity || "moderate").replace("_", " ");
    badge.textContent = intensity.toUpperCase() + " COMPETITION";
    badge.className = "intensity-badge intensity-" + (report.competitive_intensity || "moderate");

    // Competitors
    const grid = document.getElementById("competitorGrid");
    grid.innerHTML = "";
    (report.competitors || []).forEach((c, i) => {
        const card = document.createElement("div");
        card.className = "competitor-card";
        card.style.animationDelay = `${i * 0.1}s`;
        card.dataset.compIndex = i;

        const pricingClass = "pricing-" + (c.pricing_tier || "mid-range").replace(/\s+/g, "-");
        const starsHtml = renderStars(c.rating);

        // Confidence badge color
        const conf = c.confidence_score || 0.5;
        const confClass = conf >= 0.7 ? "conf-high" : conf >= 0.4 ? "conf-mid" : "conf-low";

        card.innerHTML = `
            <div class="comp-header">
                <span class="comp-name">${esc(c.name)}</span>
                <span class="comp-pricing ${pricingClass}">${esc(c.pricing_tier || "N/A")}</span>
            </div>
            <p class="comp-description">${esc(c.description || "")}</p>
            ${c.rating ? `<div class="comp-rating">${starsHtml} <span class="rating-num">${c.rating}/5</span></div>` : ""}
            <div class="comp-meta-row">
                ${c.cluster && c.cluster !== "general" ? `<span class="cluster-tag">${esc(c.cluster)}</span>` : ""}
                <span class="confidence-badge ${confClass}" title="Data confidence">${Math.round(conf * 100)}% conf.</span>
                ${c.source_count ? `<span class="source-count-badge">${c.source_count} sources</span>` : ""}
            </div>
            <div class="comp-section-label">Products / Services</div>
            <div class="tag-list">${(c.key_products || []).map(p => `<span class="tag tag-product">${esc(p)}</span>`).join("")}</div>
            <div class="comp-section-label">Strengths</div>
            <div class="tag-list">${(c.strengths || []).map(s => `<span class="tag tag-strength">${esc(s)}</span>`).join("")}</div>
            <div class="comp-section-label">Weaknesses</div>
            <div class="tag-list">${(c.weaknesses || []).map(w => `<span class="tag tag-weakness">${esc(w)}</span>`).join("")}</div>
            ${c.unique_selling_point ? `<div class="comp-usp">"${esc(c.unique_selling_point)}"</div>` : ""}
        `;

        card.addEventListener("click", () => {
            if (!compareMode) return;
            handleCompareClick(card, i);
        });

        grid.appendChild(card);
    });

    // SWOT
    populateList("swotStrengths",     report.swot?.strengths);
    populateList("swotWeaknesses",    report.swot?.weaknesses);
    populateList("swotOpportunities", report.swot?.opportunities);
    populateList("swotThreats",       report.swot?.threats);

    // Market Gaps (with root causes)
    const gapsGrid = document.getElementById("gapsGrid");
    gapsGrid.innerHTML = "";
    (report.market_gaps || []).forEach(g => {
        const impactClass = "impact-" + (g.potential_impact || "medium").toLowerCase();
        const diffClass   = "diff-" + (g.difficulty || "moderate").toLowerCase();
        const gapConf = g.confidence_score || 0.5;
        const gapConfClass = gapConf >= 0.7 ? "conf-high" : gapConf >= 0.4 ? "conf-mid" : "conf-low";

        const el = document.createElement("div");
        el.className = "gap-item";
        el.innerHTML = `
            <div class="gap-info">
                <h4>${esc(g.gap)}</h4>
                <p>${esc(g.description)}</p>
                ${g.root_cause ? `<p class="gap-root-cause"><strong>Why this exists:</strong> ${esc(g.root_cause)}</p>` : ""}
                <p class="gap-action"> ${esc(g.recommended_action)}</p>
                ${g.data_gaps ? `<p class="gap-data-gaps"><em> Data needed: ${esc(g.data_gaps)}</em></p>` : ""}
            </div>
            <div class="gap-badges">
                <span class="gap-badge ${impactClass}">${esc(g.potential_impact || "medium")} impact</span>
                <span class="gap-badge ${diffClass}">${esc(g.difficulty || "moderate")}</span>
                <span class="confidence-badge ${gapConfClass}">${Math.round(gapConf * 100)}%</span>
            </div>
        `;
        gapsGrid.appendChild(el);
    });

    // Recommendations
    const recsList = document.getElementById("recsList");
    recsList.innerHTML = "";
    (report.recommendations || []).forEach(r => {
        const li = document.createElement("li");
        li.textContent = r;
        recsList.appendChild(li);
    });

    // Growth Chart
    renderGrowthChart(report.competitors || []);

    // Quadrant Chart (Item 7)
    renderQuadrantChart(report.competitors || []);

    // Scorecard (Item 5)
    renderScorecard(report.scorecard);

    // Research Trace (Item 6)
    renderTrace(report.research_trace);

    // Critic Review (Item 3)
    renderCriticReview(report.critic_review);

    // Show results
    resultsSection.style.display = "block";

    if (typeof lucide !== "undefined") lucide.createIcons();

    setTimeout(() => {
        const statsbar = document.getElementById("statsbarSection");
        const scrollTarget = statsbar && statsbar.style.display !== "none" ? statsbar : resultsSection;
        scrollTarget.scrollIntoview({ behavior: "smooth", block: "start" });
    }, 300);
}


// 
//  SCORECARD RENDERER (Item 5) 
// 
function renderScorecard(scorecard) {
    const el = document.getElementById("scorecardSection");
    if (!el || !scorecard) return;

    const goClass = scorecard.go_no_go === "GO" ? "go-go" :
                    scorecard.go_no_go === "NO-GO" ? "go-nogo" : "go-caution";

    el.innerHTML = `
        <div class="card card-elevated scorecard-card">
            <div class="card-header-row">
                <div class="card-icon-wrap"><i data-lucide="gauge" class="card-icon"></i></div>
                <div>
                    <h2 class="card-heading">Market Scorecard</h2>
                    <p class="card-desc">Final assessment & recommendation</p>
                </div>
                <span class="go-badge ${goClass}">${esc(scorecard.go_no_go)}</span>
            </div>
            <div class="scorecard-grid">
                <div class="score-ring-item">
                    <div class="score-ring" data-value="${scorecard.opportunity_score}" data-color="var(--emerald)">
                        <svg viewBox="0 0 36 36"><path class="ring-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"/><path class="ring-fill" stroke-dasharray="${scorecard.opportunity_score}, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"/><text x="18" y="20.35" class="ring-text">${scorecard.opportunity_score}</text></svg>
                    </div>
                    <span class="score-label">Opportunity</span>
                </div>
                <div class="score-ring-item">
                    <div class="score-ring" data-value="${scorecard.differentiation_score}" data-color="var(--gold)">
                        <svg viewBox="0 0 36 36"><path class="ring-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"/><path class="ring-fill" stroke-dasharray="${scorecard.differentiation_score}, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"/><text x="18" y="20.35" class="ring-text">${scorecard.differentiation_score}</text></svg>
                    </div>
                    <span class="score-label">Differentiation</span>
                </div>
                <div class="score-ring-item">
                    <div class="score-ring" data-value="${scorecard.competition_intensity_score}" data-color="var(--rose)">
                        <svg viewBox="0 0 36 36"><path class="ring-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"/><path class="ring-fill" stroke-dasharray="${scorecard.competition_intensity_score}, 100" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"/><text x="18" y="20.35" class="ring-text">${scorecard.competition_intensity_score}</text></svg>
                    </div>
                    <span class="score-label">Competition</span>
                </div>
            </div>
            <div class="scorecard-meta">
                <span class="sc-pill"><strong>Launch:</strong> ${esc(scorecard.launch_difficulty)}</span>
                <span class="sc-pill"><strong>Confidence:</strong> ${esc(scorecard.confidence_level)}</span>
            </div>
            ${scorecard.rationale ? `<p class="scorecard-rationale">${esc(scorecard.rationale)}</p>` : ""}
        </div>
    `;
    el.style.display = "block";
}


// 
//  RESEARCH TRACE yIEW (Item 6) 
// 
function renderTrace(trace) {
    const el = document.getElementById("traceSection");
    if (!el || !trace) return;

    el.innerHTML = `
        <details class="card card-elevated trace-card">
            <summary class="trace-summary">
                <i data-lucide="route" class="icon-sm"></i>
                <span>Agent Research Trace</span>
                <span class="trace-time">${trace.total_time_seconds}s</span>
            </summary>
            <div class="trace-body">
                <div class="trace-grid">
                    <div class="trace-item"><span class="trace-num">${trace.queries_generated?.length || 0}</span><span class="trace-lbl">Queries</span></div>
                    <div class="trace-item"><span class="trace-num">${trace.search_hits_total || 0}</span><span class="trace-lbl">Search Hits</span></div>
                    <div class="trace-item"><span class="trace-num">${trace.unique_results || 0}</span><span class="trace-lbl">Unique Results</span></div>
                    <div class="trace-item"><span class="trace-num">${trace.pages_scraped || 0}</span><span class="trace-lbl">Pages Scraped</span></div>
                    <div class="trace-item"><span class="trace-num">${trace.pages_blocked || 0}</span><span class="trace-lbl">ilocked</span></div>
                    <div class="trace-item"><span class="trace-num">${trace.competitors_extracted || 0}</span><span class="trace-lbl">Extracted</span></div>
                    <div class="trace-item"><span class="trace-num">${trace.critic_issues_found || 0}</span><span class="trace-lbl">Critic Issues</span></div>
                    <div class="trace-item"><span class="trace-num">${trace.revision_made ? "Yes" : "No"}</span><span class="trace-lbl">Revised</span></div>
                </div>
                <div class="trace-detail">
                    <strong>AI Provider:</strong> ${esc(trace.ai_provider)} (${esc(trace.ai_model)})<br>
                    <strong>Queries Generated:</strong>
                    <ul>${(trace.queries_generated || []).map(q => `<li>"${esc(q)}"</li>`).join("")}</ul>
                    ${trace.critic_issues?.length ? `<strong>Critic Issues:</strong><ul>${trace.critic_issues.map(i => `<li>${esc(i)}</li>`).join("")}</ul>` : ""}
                </div>
            </div>
        </details>
    `;
    el.style.display = "block";
}


// 
//  CRITIC REVIEW DISPLAY (Item 3) 
// 
function renderCriticReview(critic) {
    const el = document.getElementById("criticSection");
    if (!el || !critic) return;

    const qualityClass = "crit-" + (critic.overall_quality || "good");
    const issues = critic.issues || [];

    el.innerHTML = `
        <div class="card card-elevated critic-card">
            <div class="card-header-row">
                <div class="card-icon-wrap"><i data-lucide="shield-alert" class="card-icon"></i></div>
                <div>
                    <h2 class="card-heading">Critic Agent Review</h2>
                    <p class="card-desc">Independent quality assessment</p>
                </div>
                <span class="critic-quality-badge ${qualityClass}">${esc((critic.overall_quality || "good").toUpperCase())}</span>
            </div>
            ${issues.length ? `
                <div class="critic-issues-list">
                    ${issues.map(iss => `
                        <div class="critic-issue severity-${iss.severity || "medium"}">
                            <span class="critic-issue-section">${esc(iss.section)}</span>
                            <span class="critic-issue-sev">${esc((iss.severity || "medium").toUpperCase())}</span>
                            <p class="critic-issue-text">${esc(iss.issue)}</p>
                            ${iss.suggestion ? `<p class="critic-issue-fix"> ${esc(iss.suggestion)}</p>` : ""}
                        </div>
                    `).join("")}
                </div>
            ` : `<p style="color:var(--emerald);padding:12px;">No issues found  report quality is excellent.</p>`}
        </div>
    `;
    el.style.display = "block";
}


// 
//  ANIMATED STATS COUNTER iAR 
// 
function showStatsbar(report) {
    const section = document.getElementById("statsbarSection");
    if (!section) return;

    const elapsedSec = researchStartTime ? Math.round((Date.now() - researchStartTime) / 1000) : 0;
    const compCount = (report.competitors || []).length;
    const gapCount = (report.market_gaps || []).length;
    const sourceCount = compCount * 3;

    document.getElementById("statCompetitors").dataset.target = compCount;
    document.getElementById("statSources").dataset.target = sourceCount;
    document.getElementById("statTime").dataset.target = elapsedSec;
    document.getElementById("statGaps").dataset.target = gapCount;

    section.style.display = "block";
    section.querySelectorAll(".stat-value").forEach(el => {
        animateCounter(el, parseInt(el.dataset.target) || 0);
    });
    if (typeof lucide !== "undefined") lucide.createIcons();
}

function animateCounter(el, target) {
    const duration = 1200;
    const start = performance.now();
    function tick(now) {
        const elapsed = now - start;
        const progress = Math.min(elapsed / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(target * eased);
        if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}


// 
//  GROWTH CHART 
// 
let growthChartInstance = null;

function renderGrowthChart(competitors) {
    const canvas = document.getElementById("growthChart");
    if (!canvas || typeof Chart === "undefined") return;
    if (growthChartInstance) { growthChartInstance.destroy(); growthChartInstance = null; }

    const palette = [
        { border: "#c9a44c", bg: "rgba(201,164,76,0.12)" },
        { border: "#2dd4bf", bg: "rgba(45,212,191,0.10)" },
        { border: "#60a5fa", bg: "rgba(96,165,250,0.10)" },
        { border: "#34d399", bg: "rgba(52,211,153,0.10)" },
        { border: "#fbbf24", bg: "rgba(251,191,36,0.10)" },
        { border: "#a78bfa", bg: "rgba(167,139,250,0.10)" },
        { border: "#fb7185", bg: "rgba(251,113,133,0.10)" },
        { border: "#38bdf8", bg: "rgba(56,189,248,0.10)" },
    ];

    let allYears = new Set();
    competitors.forEach(c => { (c.growth_years || []).forEach(y => allYears.add(y)); });
    const labels = Array.from(allYears).sort();
    if (labels.length === 0) labels.push("2023", "2024", "2025");

    const datasets = competitors.map((c, i) => {
        const color = palette[i % palette.length];
        const years = c.growth_years || ["2023", "2024", "2025"];
        const rates = c.growth_rates || [0, 0, 0];
        const data = labels.map(lbl => { const idx = years.indexOf(lbl); return idx >= 0 ? rates[idx] : null; });
        return {
            label: c.name || `Competitor ${i + 1}`, data,
            borderColor: color.border, backgroundColor: color.bg,
            borderWidth: 2, pointRadius: 4, pointHoverRadius: 6,
            pointBackgroundColor: color.border, tension: 0.35, fill: true,
        };
    });

    growthChartInstance = new Chart(canvas, {
        type: "line",
        data: { labels, datasets },
        options: {
            responsive: true, maintainAspectRatio: false,
            interaction: { mode: "index", intersect: false },
            plugins: {
                legend: { position: "bottom", labels: { color: "#94a3b8", font: { family: "'DM Sans', sans-serif", size: 11, weight: 500 }, padding: 16, usePointStyle: true, pointStyle: "circle" } },
                tooltip: { backgroundColor: "rgba(17,24,39,0.95)", titleColor: "#e2e8f0", bodyColor: "#e2e8f0", borderColor: "rgba(201,164,76,0.25)", borderWidth: 1, cornerRadius: 8, padding: 12, callbacks: { label: ctx => `${ctx.dataset.label}: ${ctx.parsed.y != null ? ctx.parsed.y.toFixed(1) + "%" : "N/A"}` } },
            },
            scales: {
                x: { ticks: { color: "#94a3b8", font: { family: "'DM Sans', sans-serif", size: 11 } }, grid: { color: "rgba(255,255,255,0.04)" } },
                y: { ticks: { color: "#94a3b8", font: { family: "'DM Sans', sans-serif", size: 11 }, callback: val => val + "%" }, grid: { color: "rgba(255,255,255,0.04)" }, title: { display: true, text: "Growth Rate (%)", color: "#64748b", font: { family: "'DM Sans', sans-serif", size: 12 } } },
            },
        },
    });
}


// 
//  PRICE yS QUALITY QUADRANT CHART (Item 7) 
// 
let quadrantChartInstance = null;

function renderQuadrantChart(competitors) {
    const canvas = document.getElementById("quadrantChart");
    if (!canvas || typeof Chart === "undefined") return;
    if (quadrantChartInstance) { quadrantChartInstance.destroy(); quadrantChartInstance = null; }

    const section = document.getElementById("quadrantSection");
    if (section) section.style.display = "block";

    const palette = ["#c9a44c", "#2dd4bf", "#60a5fa", "#34d399", "#fbbf24", "#a78bfa", "#fb7185", "#38bdf8"];

    const data = competitors.map((c, i) => ({
        x: c.price_score || 5,
        y: c.quality_score || 5,
        label: c.name,
    }));

    quadrantChartInstance = new Chart(canvas, {
        type: "scatter",
        data: {
            datasets: [{
                label: "Competitors",
                data: data,
                backgroundColor: competitors.map((_, i) => palette[i % palette.length] + "CC"),
                borderColor: competitors.map((_, i) => palette[i % palette.length]),
                borderWidth: 2,
                pointRadius: 10,
                pointHoverRadius: 14,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: "rgba(17,24,39,0.95)",
                    titleColor: "#e2e8f0", bodyColor: "#e2e8f0",
                    borderColor: "rgba(201,164,76,0.25)", borderWidth: 1,
                    cornerRadius: 8, padding: 12,
                    callbacks: {
                        title: (items) => items[0] ? data[items[0].dataIndex]?.label : "",
                        label: (ctx) => `Price: ${ctx.parsed.x}/10  |  Quality: ${ctx.parsed.y}/10`,
                    },
                },
                // Quadrant labels via annotation plugin or custom drawing
            },
            scales: {
                x: {
                    min: 0, max: 10,
                    title: { display: true, text: "Price ", color: "#64748b", font: { family: "'DM Sans', sans-serif", size: 12 } },
                    ticks: { color: "#94a3b8", font: { family: "'DM Sans', sans-serif", size: 11 } },
                    grid: { color: "rgba(255,255,255,0.04)" },
                },
                y: {
                    min: 0, max: 10,
                    title: { display: true, text: "Quality ", color: "#64748b", font: { family: "'DM Sans', sans-serif", size: 12 } },
                    ticks: { color: "#94a3b8", font: { family: "'DM Sans', sans-serif", size: 11 } },
                    grid: { color: "rgba(255,255,255,0.04)" },
                },
            },
        },
        plugins: [{
            // Draw quadrant labels
            afterDraw: (chart) => {
                const { ctx, chartArea: { left, right, top, bottom } } = chart;
                const midX = (left + right) / 2;
                const midY = (top + bottom) / 2;
                ctx.save();
                ctx.font = "600 11px 'DM Sans', sans-serif";
                ctx.globalAlpha = 0.2;

                ctx.fillStyle = "#34d399";
                ctx.fillText("High Quality / Low Price", left + 10, top + 20);

                ctx.fillStyle = "#c9a44c";
                ctx.fillText("High Quality / High Price", midX + 10, top + 20);

                ctx.fillStyle = "#94a3b8";
                ctx.fillText("Low Quality / Low Price", left + 10, bottom - 10);

                ctx.fillStyle = "#fb7185";
                ctx.fillText("Low Quality / High Price", midX + 10, bottom - 10);

                // Draw crosshair lines
                ctx.strokeStyle = "rgba(255,255,255,0.08)";
                ctx.lineWidth = 1;
                ctx.setLineDash([4, 4]);
                ctx.beginPath(); ctx.moveTo(midX, top); ctx.lineTo(midX, bottom); ctx.stroke();
                ctx.beginPath(); ctx.moveTo(left, midY); ctx.lineTo(right, midY); ctx.stroke();

                ctx.restore();
            },
        }],
    });
}


// 
//  COMPETITOR COMPARISON MODE 
// 
const compareToggle = document.getElementById("compareToggle");
if (compareToggle) {
    compareToggle.addEventListener("click", () => {
        compareMode = !compareMode;
        compareToggle.classList.toggle("active", compareMode);
        selectedForCompare = [];
        const cards = document.querySelectorAll(".competitor-card");
        cards.forEach(card => {
            card.classList.toggle("compare-mode", compareMode);
            card.classList.remove("compare-selected");
        });
        const compCard = document.getElementById("comparisonCard");
        if (!compareMode && compCard) compCard.style.display = "none";
        if (compareMode && compCard) {
            compCard.style.display = "block";
            document.getElementById("comparisonHint").style.display = "block";
            document.getElementById("comparisonTableWrap").style.display = "none";
        }
    });
}

const comparisonClose = document.getElementById("comparisonClose");
if (comparisonClose) {
    comparisonClose.addEventListener("click", () => {
        compareMode = false;
        if (compareToggle) compareToggle.classList.remove("active");
        selectedForCompare = [];
        document.querySelectorAll(".competitor-card").forEach(card => {
            card.classList.remove("compare-mode", "compare-selected");
        });
        document.getElementById("comparisonCard").style.display = "none";
    });
}

function handleCompareClick(card, index) {
    if (card.classList.contains("compare-selected")) {
        card.classList.remove("compare-selected");
        selectedForCompare = selectedForCompare.filter(i => i !== index);
    } else {
        if (selectedForCompare.length >= 2) {
            const firstIdx = selectedForCompare.shift();
            document.querySelector(`.competitor-card[data-comp-index="${firstIdx}"]`)?.classList.remove("compare-selected");
        }
        card.classList.add("compare-selected");
        selectedForCompare.push(index);
    }
    if (selectedForCompare.length === 2 && currentReport) {
        renderComparison(currentReport.competitors[selectedForCompare[0]], currentReport.competitors[selectedForCompare[1]]);
    }
}

function renderComparison(a, b) {
    const wrap = document.getElementById("comparisonTableWrap");
    const hint = document.getElementById("comparisonHint");
    if (!wrap) return;
    hint.style.display = "none";
    wrap.style.display = "block";
    const rows = [
        ["Name", a.name, b.name, true],
        ["Description", a.description, b.description],
        ["Rating", a.rating ? `${a.rating}/5` : "N/A", b.rating ? `${b.rating}/5` : "N/A"],
        ["Pricing", a.pricing_tier || "N/A", b.pricing_tier || "N/A"],
        ["Cluster", a.cluster || "N/A", b.cluster || "N/A"],
        ["Confidence", `${Math.round((a.confidence_score||0.5)*100)}%`, `${Math.round((b.confidence_score||0.5)*100)}%`],
        ["Products", (a.key_products || []).join(", "), (b.key_products || []).join(", ")],
        ["Strengths", (a.strengths || []).join(", "), (b.strengths || []).join(", ")],
        ["Weaknesses", (a.weaknesses || []).join(", "), (b.weaknesses || []).join(", ")],
        ["USP", a.unique_selling_point || "N/A", b.unique_selling_point || "N/A"],
    ];
    let html = `<table class="comparison-table"><thead><tr><th>Attribute</th><th>${esc(a.name)}</th><th>${esc(b.name)}</th></tr></thead><tbody>`;
    rows.forEach(([label, valA, vali, isName]) => {
        const cls = isName ? ' class="comp-col-name"' : '';
        html += `<tr><td><strong>${label}</strong></td><td${cls}>${esc(valA)}</td><td${cls}>${esc(vali)}</td></tr>`;
    });
    html += `</tbody></table>`;
    wrap.innerHTML = html;
}


// 
//  PDF EXPORT 
// 
const exportPdfBtn = document.getElementById("exportPdfBtn");
if (exportPdfBtn) {
    exportPdfBtn.addEventListener("click", () => {
        if (!currentReport) return;
        if (typeof html2pdf === "undefined") { alert("PDF library not loaded."); return; }
        const element = document.getElementById("resultsSection");
        const opt = {
            margin: [10, 10, 10, 10],
            filename: `VyaparSathi_Report_${currentNiche.replace(/\s+/g, "_")}_${new Date().toISOString().slice(0,10)}.pdf`,
            image: { type: "jpeg", quality: 0.95 },
            html2canvas: { scale: 2, useCORS: true, backgroundColor: "#0b1120" },
            jsPDF: { unit: "mm", format: "a4", orientation: "portrait" },
        };
        exportPdfBtn.disabled = true;
        exportPdfBtn.innerHTML = '<span class="spinner spinner-sm"></span> Generating';
        html2pdf().set(opt).from(element).save().then(() => {
            exportPdfBtn.disabled = false;
            exportPdfBtn.innerHTML = '<i data-lucide="download" class="icon-sm"></i> Export PDF Report';
            if (typeof lucide !== "undefined") lucide.createIcons();
        });
    });
}


// 
//  RESEARCH HISTORY 
// 
const HISTORY_KEY = "vyaparsathi_history";

function saveToHistory(report) {
    try {
        const history = JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]");
        history.unshift({
            niche: currentNiche, location: currentLocation,
            timestamp: new Date().toISOString(),
            competitorCount: (report.competitors || []).length,
            intensity: report.competitive_intensity || "moderate",
            goNoGo: report.scorecard?.go_no_go || "N/A",
            report, taskId: currentTaskId,
        });
        if (history.length > 20) history.length = 20;
        localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
        renderHistoryList();
    } catch (e) { console.warn("Failed to save history:", e); }
}

function loadHistory() {
    try { return JSON.parse(localStorage.getItem(HISTORY_KEY) || "[]"); }
    catch { return []; }
}

function renderHistoryList() {
    const list = document.getElementById("historyList");
    if (!list) return;
    const history = loadHistory();
    if (history.length === 0) {
        list.innerHTML = '<p class="history-empty">No past research found. Run your first scan!</p>';
        return;
    }
    list.innerHTML = history.map((entry, i) => {
        const date = new Date(entry.timestamp);
        const dateStr = date.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
        const timeStr = date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
        return `
            <div class="history-entry" data-index="${i}">
                <div class="history-entry-niche">${esc(entry.niche)}</div>
                <div class="history-entry-meta">
                    <span> ${esc(entry.location)}</span>
                    <span> ${entry.competitorCount} competitors</span>
                    <span> ${dateStr} ${timeStr}</span>
                    ${entry.goNoGo ? `<span class="history-go">${esc(entry.goNoGo)}</span>` : ""}
                </div>
            </div>`;
    }).join("");
    list.querySelectorAll(".history-entry").forEach(el => {
        el.addEventListener("click", () => {
            const idx = parseInt(el.dataset.index);
            const entry = history[idx];
            if (entry?.report) {
                currentReport = entry.report; currentTaskId = entry.taskId;
                currentNiche = entry.niche; currentLocation = entry.location;
                reportReceived = true;
                renderReport(entry.report); showStatsbar(entry.report); closeHistory();
            }
        });
    });
}

const historyToggle = document.getElementById("historyToggle");
const historyPanel = document.getElementById("historyPanel");
const historyClose = document.getElementById("historyClose");
const historyOverlay = document.getElementById("historyOverlay");

function openHistory() { renderHistoryList(); historyPanel?.classList.add("open"); historyOverlay?.classList.add("active"); }
function closeHistory() { historyPanel?.classList.remove("open"); historyOverlay?.classList.remove("active"); }

if (historyToggle) historyToggle.addEventListener("click", openHistory);
if (historyClose) historyClose.addEventListener("click", closeHistory);
if (historyOverlay) historyOverlay.addEventListener("click", closeHistory);
renderHistoryList();


// 
//  DEMO MODE (Item 9) 
// 
const demoBtn = document.getElementById("demoBtn");
if (demoBtn) {
    demoBtn.addEventListener("click", () => {
        document.getElementById("niche").value = "Specialty Coffee Shop";
        document.getElementById("location").value = "Austin, TX";
        // Auto-submit
        researchForm.dispatchEvent(new Event("submit", { cancelable: true }));
    });
}


// 
//  STRATEGY SIMULATOR (Enhanced  Item 8) 
// 
simulateBtn.addEventListener("click", async () => {
    const scenario = scenarioInput.value.trim();
    if (!scenario || !currentTaskId || !currentReport) return;

    simBtnText.style.display   = "none";
    simBtnLoader.style.display = "inline-block";
    simulateBtn.disabled = true;
    simResults.style.display = "none";

    try {
        const res = await fetch("/api/simulate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ task_id: currentTaskId, scenario }),
        });
        if (!res.ok) throw new Error("Simulation failed");
        const data = await res.json();
        renderSimulation(data);
    } catch (err) {
        simResults.innerHTML = `<p style="color:var(--rose);">Error: ${esc(err.message)}</p>`;
        simResults.style.display = "block";
    } finally {
        simBtnText.style.display   = "inline";
        simBtnLoader.style.display = "none";
        simulateBtn.disabled = false;
    }
});

function renderSimulation(data) {
    let html = `<div class="sim-scenario">Scenario: "${esc(data.scenario || "")}"</div>`;

    // Success probability
    if (data.success_probability != null) {
        const prob = data.success_probability;
        const probClass = prob >= 60 ? "prob-high" : prob >= 35 ? "prob-mid" : "prob-low";
        html += `<div class="sim-probability ${probClass}">Success Probability: <strong>${prob}%</strong></div>`;
    }

    // Phased timeline (Item 8)
    if (data.phases?.length) {
        html += `<div class="sim-timeline">`;
        data.phases.forEach((p, i) => {
            html += `
                <div class="sim-phase" style="animation-delay:${i * 0.15}s">
                    <div class="sim-phase-marker">${i + 1}</div>
                    <div class="sim-phase-content">
                        <div class="sim-phase-period">${esc(p.phase || "")}</div>
                        <div class="sim-phase-title">${esc(p.title || "")}</div>
                        <div class="sim-phase-desc">${esc(p.description || "")}</div>
                    </div>
                </div>`;
        });
        html += `</div>`;
    }

    // Competitor reactions
    (data.competitor_reactions || []).forEach(r => {
        html += `
            <div class="sim-reaction">
                <div class="sim-reaction-name">${esc(r.name || "Competitor")}</div>
                <div class="sim-reaction-text">${esc(r.reaction || "")}</div>
                ${r.impact ? `<div class="sim-reaction-text" style="color:var(--amber);margin-top:4px;">Impact: ${esc(r.impact)}</div>` : ""}
            </div>`;
    });

    // Counter strategies
    if (data.counter_strategies?.length) {
        html += `<div class="sim-counters"><strong> Counter Strategies:</strong><ul>`;
        data.counter_strategies.forEach(s => { html += `<li>${esc(s)}</li>`; });
        html += `</ul></div>`;
    }

    const risk = (data.risk_assessment || "medium").toLowerCase();
    html += `<div class="sim-risk risk-${risk}">Risk Assessment: ${esc(data.risk_assessment || "N/A")}</div>`;
    if (data.recommendation) {
        html += `<div class="sim-recommendation"><strong>Recommendation:</strong> ${esc(data.recommendation)}</div>`;
    }

    simResults.innerHTML = html;
    simResults.style.display = "block";
}


// 
//  HELPERS 
// 
function esc(str) {
    const div = document.createElement("div");
    div.textContent = String(str || "");
    return div.innerHTML;
}

function renderStars(rating) {
    if (!rating) return "";
    const filled = Math.max(0, Math.min(5, Math.round(rating)));
    const empty = 5 - filled;
    return `<span class="stars">${"★".repeat(filled)}${"☆".repeat(empty)}</span>`;
}

function populateList(elementId, items) {
    const ul = document.getElementById(elementId);
    if (!ul) return;
    ul.innerHTML = "";
    (items || []).forEach(item => {
        const li = document.createElement("li");
        li.textContent = item;
        ul.appendChild(li);
    });
}


