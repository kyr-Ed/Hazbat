// Quick-view panel for the traceability graph.
//
// The graph page tells this panel what happened by sending browser events,
// so the panel and the graph/filter code stay in separate files:
//   document.dispatchEvent(new CustomEvent('hazbat:select', { detail: { id: nodeId } }));
//   document.dispatchEvent(new CustomEvent('hazbat:clear'));
//
// The panel only opens for cells (SLP, coin cell, MLP). It reads /api/card/{id}
// and, if the cell has cycling data, /api/cycling/{id}/summary for state of health.
(function () {
    const CELL_TYPES = {
        slp:      { label: 'SLP',       colour: 'var(--hz-slp)' },
        coincell: { label: 'Coin cell', colour: 'var(--hz-coincell)' },
        mlp:      { label: 'MLP',       colour: 'var(--hz-mlp)' },
    };
    const BLANK = '—';
    let currentId = null;  // ignore slow replies for a node that is no longer selected

    function panel() {
        return document.getElementById('nodePanel');
    }

    // Escape text before putting it into HTML (IDs, notes etc. come from the database)
    function esc(value) {
        return String(value)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function show(value, unit) {
        if (value === null || value === undefined || value === '' || value === 'N/A') return BLANK;
        return esc(value) + (unit || '');
    }

    function hide() {
        currentId = null;
        const el = panel();
        if (el) { el.hidden = true; el.innerHTML = ''; }
    }

    function render(data) {
        const p = data.panel;
        const type = CELL_TYPES[data.record_type];
        const id = esc(data.record_id);

        const rows = p.fields.map(([label, value]) =>
            `<div class="row"><span class="label">${esc(label)}</span><span class="value">${show(value)}</span></div>`
        ).join('');

        const chain = data.chain.length
            ? `<div class="panel-chain"><div class="chain-title">TRACEABILITY CHAIN</div>` +
              data.chain.map(c => `<div>${esc(c)}</div>`).join('') + `</div>`
            : '';

        // Until the lineage & passport page exists, the main button opens the existing card
        const mainLink = p.lineage_url
            ? `<a class="panel-button" href="${esc(p.lineage_url)}">Open lineage &amp; passport card →</a>`
            : `<a class="panel-button" href="${esc(p.card_url)}">Open full card →</a>`;

        panel().innerHTML = `
            <div class="node-panel-head">
                <div>
                    <h3>${id}</h3>
                    <span class="type-pill"><span class="dot" style="background:${type.colour}"></span>${type.label}</span>
                </div>
                <button type="button" class="node-panel-close" aria-label="Close panel">&times;</button>
            </div>
            <div>${rows}</div>
            <div class="metric-boxes">
                <div class="metric-box carbon" title="Filled in once process-step data is recorded">
                    <span class="metric-label">CO₂e</span><span class="metric-value">${show(p.kg_co2e, ' kg')}</span>
                </div>
                <div class="metric-box cost" title="Filled in once process-step data is recorded">
                    <span class="metric-label">COST</span><span class="metric-value">${p.cost_gbp == null ? BLANK : '£' + esc(p.cost_gbp)}</span>
                </div>
                <div class="metric-box soh" title="Latest discharge capacity as a % of the first discharge (needs cycling data)">
                    <span class="metric-label">SOH</span><span class="metric-value" id="nodePanelSoh">${BLANK}</span>
                </div>
            </div>
            <div class="panel-qr">
                <img src="${esc(p.qr_url)}" alt="QR code for ${id}">
                <span>Scan to open this card</span>
            </div>
            ${mainLink}
            <div class="panel-links">
                <a href="${esc(p.card_url)}">Basic card</a>
                <a href="${esc(p.qr_url)}" download="${id}-qr.png">Print QR label</a>
            </div>
            ${chain}`;

        panel().querySelector('.node-panel-close').addEventListener('click', () => {
            // clearSelection() lives in graph.html; it also un-highlights the graph
            if (typeof window.clearSelection === 'function') window.clearSelection();
            else hide();
        });
        panel().hidden = false;
    }

    async function loadStateOfHealth(recordId) {
        try {
            const res = await fetch(`/api/cycling/${encodeURIComponent(recordId)}/summary`);
            if (!res.ok || currentId !== recordId) return;
            const summary = await res.json();
            const el = document.getElementById('nodePanelSoh');
            if (el && summary.soh_pct != null) el.textContent = `${summary.soh_pct}%`;
        } catch (err) {
            // No cycling data or file could not be read: leave the box as "—"
        }
    }

    async function load(recordId) {
        currentId = recordId;
        let data;
        try {
            const res = await fetch(`/api/card/${encodeURIComponent(recordId)}`);
            if (!res.ok) { hide(); return; }
            data = await res.json();
        } catch (err) {
            hide();
            return;
        }
        if (currentId !== recordId) return;          // another node was clicked meanwhile
        if (!data.panel || !CELL_TYPES[data.record_type]) { hide(); return; }  // cells only
        render(data);
        loadStateOfHealth(recordId);
    }

    document.addEventListener('hazbat:select', e => load(e.detail.id));
    document.addEventListener('hazbat:clear', hide);
})();
