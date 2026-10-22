/* Certificate of Analysis (COA) chips and preview window.
 *
 * Each material card has a .coa-slot (top right) holding its newest COA as JSON in data-coa.
 *   "+ COA"  -> pick a file, or drop one anywhere on the card ([data-material-card])
 *   "COA"    -> opens the preview window (#coaModal): the PDF, or the server's PDF copy of a Word file
 * [data-coa-bulk] takes several files at once and matches them to cards by material ID in the file name.
 * [data-coa-input-drop] is the plain file field on the New Material form.
 * Server side: routers/coa.py.
 */
(function () {
    "use strict";

    const ALLOWED = /\.(pdf|docx|doc)$/i;
    const MAX_BYTES = 25 * 1024 * 1024;
    const ICON_ATTACHED = '<svg class="coa-icon" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 1.5h5.5L13 5v9.5H4z" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"/><path d="M6 9.2l1.6 1.6L11 7.4" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>';

    const modal = document.getElementById("coaModal");
    let modalSlot = null;

    function escapeHtml(text) {
        return String(text).replace(/[&<>"']/g, ch => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[ch]));
    }

    function checkFile(file) {
        if (!ALLOWED.test(file.name)) return "Only .pdf, .docx or .doc files.";
        if (file.size > MAX_BYTES) return "File is larger than 25 MB.";
        if (file.size === 0) return "That file is empty.";
        return null;
    }

    // --- Chip --------------------------------------------------------------

    function render(slot, state, message) {
        const chip = slot.querySelector(".coa-chip");
        const coa = slot._coa;
        chip.disabled = state === "busy";
        chip.className = "coa-chip";
        if (state === "busy") {
            chip.classList.add("busy");
            chip.innerHTML = '<span class="coa-spinner" aria-hidden="true"></span> Uploading…';
            chip.title = "Uploading COA";
        } else if (state === "error") {
            chip.classList.add("error");
            chip.innerHTML = "COA failed";
            chip.title = message || "Upload failed";
        } else if (coa) {
            chip.classList.add("has-coa");
            chip.innerHTML = ICON_ATTACHED + ' COA <span class="coa-kind">' + (coa.kind === "pdf" ? "PDF" : "DOC") + "</span>";
            chip.title = "View COA: " + coa.filename;
        } else {
            chip.classList.add("no-coa");
            chip.innerHTML = '<span aria-hidden="true">+</span> COA';
            chip.title = "Attach a COA (.pdf, .docx or .doc), or drop the file on this card";
        }
    }

    async function upload(slot, file) {
        const problem = checkFile(file);
        if (problem) {
            render(slot, "error", problem);
            setTimeout(() => render(slot), 4000);
            return false;
        }
        render(slot, "busy");
        const body = new FormData();
        body.append("file", file);
        try {
            const res = await fetch(`/materials/${encodeURIComponent(slot.dataset.materialId)}/coa`, {method: "POST", body});
            const data = await res.json().catch(() => ({}));
            if (!res.ok) throw new Error(data.error || `Upload failed (${res.status})`);
            slot._coa = data.coa;
            render(slot);
            const card = slot.closest("[data-material-card]");
            if (card) { card.classList.add("coa-flash"); setTimeout(() => card.classList.remove("coa-flash"), 1200); }
            if (modalSlot === slot) openModal(slot);   // "Replace" from the preview window
            return true;
        } catch (err) {
            render(slot, "error", err.message);
            setTimeout(() => render(slot), 5000);
            return false;
        }
    }

    function slotFor(materialId) {
        return document.querySelector(`.coa-slot[data-material-id="${CSS.escape(materialId)}"]`);
    }

    document.querySelectorAll(".coa-slot").forEach(slot => {
        try { slot._coa = JSON.parse(slot.dataset.coa || "null"); } catch (e) { slot._coa = null; }
        const input = slot.querySelector(".coa-file");
        slot.querySelector(".coa-chip").addEventListener("click", e => {
            e.preventDefault();
            e.stopPropagation();
            if (slot._coa) openModal(slot); else input.click();
        });
        input.addEventListener("change", () => {
            if (input.files[0]) upload(slot, input.files[0]);
            input.value = "";
        });
    });

    // Drop a file anywhere on a material card
    document.querySelectorAll("[data-material-card]").forEach(card => {
        const slot = slotFor(card.dataset.materialCard);
        if (!slot) return;
        card.addEventListener("dragover", e => { e.preventDefault(); card.classList.add("coa-dragover"); });
        card.addEventListener("dragleave", e => { if (!card.contains(e.relatedTarget)) card.classList.remove("coa-dragover"); });
        card.addEventListener("drop", e => {
            e.preventDefault();
            card.classList.remove("coa-dragover");
            if (e.dataTransfer.files[0]) upload(slot, e.dataTransfer.files[0]);
        });
    });

    // --- Preview window ------------------------------------------------------

    function openModal(slot) {
        if (!modal) return;
        const coa = slot._coa;
        modalSlot = slot;
        modal.querySelector("[data-coa-material]").textContent = coa.material_id;
        modal.querySelector("[data-coa-title]").textContent = coa.filename;
        modal.querySelector("[data-coa-meta]").textContent =
            [coa.kind_label, coa.size_label, coa.uploaded_at && "uploaded " + coa.uploaded_at, coa.uploaded_by && "by " + coa.uploaded_by]
                .filter(Boolean).join(" · ");
        modal.querySelector("[data-coa-download]").href = coa.download_url;
        const frame = modal.querySelector("[data-coa-frame]");
        const none = modal.querySelector("[data-coa-nopreview]");
        if (coa.has_preview) {
            frame.hidden = false; none.hidden = true;
            frame.src = coa.preview_url + "#view=FitH";
        } else {
            frame.hidden = true; none.hidden = false;
            frame.removeAttribute("src");
        }
        modal.hidden = false;
        document.body.classList.add("coa-modal-open");
        modal.querySelector("[data-coa-close]").focus();
    }

    function closeModal() {
        if (!modal || modal.hidden) return;
        modal.hidden = true;
        modal.querySelector("[data-coa-frame]").removeAttribute("src");
        document.body.classList.remove("coa-modal-open");
        if (modalSlot) modalSlot.querySelector(".coa-chip").focus();
        modalSlot = null;
    }

    if (modal) {
        modal.addEventListener("click", e => { if (e.target === modal) closeModal(); });
        modal.querySelector("[data-coa-close]").addEventListener("click", closeModal);
        document.addEventListener("keydown", e => { if (e.key === "Escape") closeModal(); });
        modal.querySelector("[data-coa-replace]").addEventListener("click", () => {
            if (modalSlot) modalSlot.querySelector(".coa-file").click();
        });
        modal.querySelector("[data-coa-remove]").addEventListener("click", async () => {
            const slot = modalSlot;
            if (!slot || !confirm(`Remove ${slot._coa.filename} from ${slot._coa.material_id}?`)) return;
            const res = await fetch(`/coa/${slot._coa.coa_id}`, {method: "DELETE"});
            const data = await res.json().catch(() => ({}));
            if (!res.ok) { alert(data.error || "Couldn't remove the COA."); return; }
            slot._coa = data.coa;    // the previous version, if there was one
            closeModal();
            render(slot);
        });
    }

    // --- Several files at once (bulk upload results) ------------------------------

    document.querySelectorAll("[data-coa-bulk]").forEach(zone => {
        const input = zone.querySelector('input[type="file"]');
        const status = zone.querySelector("[data-coa-bulk-status]");
        const ids = [...document.querySelectorAll(".coa-slot")].map(s => s.dataset.materialId)
            .sort((a, b) => b.length - a.length);          // longest ID first: CAT-NMC-0021 before CAT-NMC-002

        function match(file) {
            const name = file.name.toUpperCase();
            return ids.find(id => {
                const at = name.indexOf(id);
                // the ID must not run on into more of a longer ID (e.g. CAT-NMC-002 inside CAT-NMC-0021)
                return at >= 0 && !/[A-Z0-9]/.test(name.charAt(at + id.length));
            });
        }

        async function handle(files) {
            const unmatched = [];
            const jobs = [];
            for (const file of files) {
                const id = match(file);
                if (id) jobs.push(upload(slotFor(id), file)); else unmatched.push(file.name);
            }
            status.textContent = `Uploading ${jobs.length} file(s)…`;
            const ok = (await Promise.all(jobs)).filter(Boolean).length;
            status.innerHTML = `${ok} of ${jobs.length} attached.` +
                (unmatched.length ? ` <span class="coa-warn">No matching card for: ${unmatched.map(escapeHtml).join(", ")}</span>` : "");
        }

        zone.addEventListener("click", () => input.click());
        zone.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); } });
        input.addEventListener("change", () => { handle([...input.files]); input.value = ""; });
        zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("coa-dragover"); });
        zone.addEventListener("dragleave", () => zone.classList.remove("coa-dragover"));
        zone.addEventListener("drop", e => {
            e.preventDefault();
            zone.classList.remove("coa-dragover");
            handle([...e.dataTransfer.files]);
        });
    });

    // --- File field on the New Material form ---------------------------------

    document.querySelectorAll("[data-coa-input-drop]").forEach(zone => {
        const input = zone.querySelector('input[type="file"]');
        const text = zone.querySelector("[data-coa-drop-text]");
        const original = text.innerHTML;
        function show() {
            const file = input.files[0];
            zone.classList.remove("has-file", "bad-file");
            if (!file) { text.innerHTML = original; return; }
            const problem = checkFile(file);
            zone.classList.add(problem ? "bad-file" : "has-file");
            text.innerHTML = `<strong>${escapeHtml(file.name)}</strong> · ${(file.size / 1024).toFixed(0)} KB` +
                (problem ? ` — ${escapeHtml(problem)}` : " — attached when you create the material");
        }
        input.addEventListener("change", show);
        zone.addEventListener("dragover", e => { e.preventDefault(); zone.classList.add("coa-dragover"); });
        zone.addEventListener("dragleave", () => zone.classList.remove("coa-dragover"));
        zone.addEventListener("drop", e => {
            e.preventDefault();
            zone.classList.remove("coa-dragover");
            if (e.dataTransfer.files.length) { input.files = e.dataTransfer.files; show(); }
        });
    });
})();
