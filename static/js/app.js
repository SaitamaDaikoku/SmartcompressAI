/**
 * SmartCompress AI - Frontend Interactions & Dynamic Benchmarks
 * Information Storage Management (ISM) Suite
 */

document.addEventListener("DOMContentLoaded", function () {
    // ====================================================
    // Visual Batch Studio Controller (Matches User Reference Image)
    // ====================================================
    const studioCanvas = document.getElementById("studioCanvas");
    const emptyStateContainer = document.getElementById("emptyStateContainer");
    const cardsDeck = document.getElementById("cardsDeck");
    const addMoreCircleBtn = document.getElementById("addMoreCircleBtn");
    const compressionLevelSlider = document.getElementById("compressionLevelSlider");
    const levelValueDisplay = document.getElementById("levelValueDisplay");
    const compressAllBtn = document.getElementById("compressAllBtn");
    const compressAllSpinner = document.getElementById("compressAllSpinner");
    const compressAllIcon = document.getElementById("compressAllIcon");
    const deleteAllTopBtn = document.getElementById("deleteAllTopBtn");
    const bottomSelectFilesBtn = document.getElementById("bottomSelectFilesBtn");
    const bottomSelectFolderBtn = document.getElementById("bottomSelectFolderBtn");
    const emptySelectFilesBtn = document.getElementById("emptySelectFilesBtn");
    const emptySelectFolderBtn = document.getElementById("emptySelectFolderBtn");
    const bottomTrashBtn = document.getElementById("bottomTrashBtn");
    const downloadZipBtn = document.getElementById("downloadZipBtn");
    const batchFileInput = document.getElementById("batchFileInput");
    const batchFolderInput = document.getElementById("batchFolderInput");

    let studioFiles = []; // Array of {operation_id, filename, size_display, thumbnail_url, is_pdf, status, ...}

    function formatBytes(bytes) {
        if (bytes < 1024) return bytes + " Bytes";
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + " KB";
        return (bytes / (1024 * 1024)).toFixed(2) + " MB";
    }

    // Compression Level Slider Event
    if (compressionLevelSlider && levelValueDisplay) {
        compressionLevelSlider.addEventListener("input", function () {
            levelValueDisplay.textContent = this.value;
        });
    }

    function updateStudioUI() {
        if (!emptyStateContainer || !cardsDeck) return;

        if (studioFiles.length === 0) {
            emptyStateContainer.classList.remove("d-none");
            cardsDeck.classList.add("d-none");
            if (compressAllBtn) compressAllBtn.disabled = true;
            if (downloadZipBtn) downloadZipBtn.disabled = true;
        } else {
            emptyStateContainer.classList.add("d-none");
            cardsDeck.classList.remove("d-none");

            // Remove existing card DOM elements (preserving the Add More circle button)
            const oldCards = cardsDeck.querySelectorAll(".studio-card");
            oldCards.forEach(c => c.remove());

            let anyUncompressed = false;
            let anyCompressed = false;

            studioFiles.forEach(item => {
                if (item.status !== "compressed") anyUncompressed = true;
                if (item.status === "compressed") anyCompressed = true;

                const cardEl = createCardElement(item);
                cardsDeck.insertBefore(cardEl, addMoreCircleBtn);
            });

            if (compressAllBtn) compressAllBtn.disabled = !anyUncompressed;
            if (downloadZipBtn) downloadZipBtn.disabled = !anyCompressed;
        }
    }

    function truncateFilename(name, maxLen = 7) {
        if (!name) return "File";
        if (name.length <= maxLen) return name;
        const extIdx = name.lastIndexOf(".");
        if (extIdx > 0 && extIdx <= maxLen) {
            return name.substring(0, maxLen) + "...";
        }
        return name.substring(0, 3) + "...";
    }

    function createCardElement(item) {
        const card = document.createElement("div");
        card.className = "studio-card animate-fade-in";
        card.id = `card-${item.operation_id}`;

        const shortName = truncateFilename(item.filename, 6);

        // Thumbnail preview rendering
        let thumbContent = "";
        if (item.thumbnail_url) {
            thumbContent = `<img src="${item.thumbnail_url}" alt="${item.filename}">`;
        } else if (item.is_pdf) {
            thumbContent = `
                <div class="doc-generic-preview d-flex flex-column align-items-center justify-content-center text-center">
                    <i class="bi bi-file-earmark-pdf-fill text-danger fs-1 mb-2"></i>
                    <div class="fw-bold text-dark text-break small px-1">${item.filename}</div>
                    <small class="text-muted mt-1">PDF Document</small>
                </div>
            `;
        } else {
            thumbContent = `
                <div class="doc-generic-preview d-flex flex-column align-items-center justify-content-center text-center">
                    <i class="bi bi-file-earmark-code-fill text-primary fs-1 mb-2"></i>
                    <div class="fw-bold text-dark text-break small px-1">${item.filename}</div>
                    <small class="text-muted mt-1">${item.category || "File"}</small>
                </div>
            `;
        }

        // Footer status & action rendering
        let footerContent = "";
        if (item.status === "compressing") {
            footerContent = `
                <div class="mb-2">
                    <span class="text-warning small fw-semibold">
                        <span class="spinner-border spinner-border-sm me-1"></span> Compressing...
                    </span>
                </div>
                <button class="btn btn-secondary btn-sm w-100 fw-semibold" disabled>Processing...</button>
            `;
        } else if (item.status === "compressed") {
            footerContent = `
                <div class="mb-2">
                    <div class="fw-bold text-white small">New size: ${item.compressed_size_display}</div>
                    <span class="badge bg-dark border border-secondary text-white mt-1">-${item.space_saving_pct}%</span>
                </div>
                <div class="d-grid gap-1">
                    <a href="${item.download_url}" class="btn btn-royal-blue btn-sm fw-bold">
                        <i class="bi bi-download me-1"></i> Download
                    </a>
                    <a href="/result/${item.operation_id}" class="btn btn-outline-secondary btn-sm fw-semibold mt-1 d-flex align-items-center justify-content-center gap-1 text-white" style="font-size: 11px;">
                        <i class="bi bi-graph-up"></i> Analytics &amp; Algorithms
                    </a>
                </div>
            `;
        } else {
            footerContent = `
                <div class="mb-2">
                    <span class="badge bg-dark border border-secondary text-secondary-light small">
                        <i class="bi bi-cpu me-1"></i> Rec: ${item.recommended_algorithm || "7Z"}
                    </span>
                </div>
                <div class="d-grid gap-1">
                    <button class="btn btn-royal-blue btn-sm fw-semibold card-compress-btn" data-id="${item.operation_id}">
                        Compress
                    </button>
                    <a href="/result/${item.operation_id}" class="btn btn-outline-secondary btn-sm fw-semibold mt-1 d-flex align-items-center justify-content-center gap-1 text-white" style="font-size: 11px;">
                        <i class="bi bi-graph-up"></i> Analytics &amp; Chooser
                    </a>
                </div>
            `;
        }

        card.innerHTML = `
            <div class="studio-card-header">
                <span class="fw-bold text-white text-truncate" style="max-width: 95px;" title="${item.filename}">
                    ${shortName}
                </span>
                <div class="d-flex align-items-center gap-2">
                    <span class="text-secondary-light small font-monospace">${item.size_display}</span>
                    <button type="button" class="btn btn-link text-secondary-light p-0 text-decoration-none remove-card-btn" data-id="${item.operation_id}" title="Remove file">
                        <i class="bi bi-x-lg fs-6"></i>
                    </button>
                </div>
            </div>
            <div class="studio-card-body">
                <div class="doc-paper-frame">
                    ${thumbContent}
                </div>
            </div>
            <div class="studio-card-footer">
                ${footerContent}
            </div>
        `;

        return card;
    }

    async function uploadFilesToStudio(fileList) {
        if (!fileList || fileList.length === 0) return;

        const formData = new FormData();
        for (let i = 0; i < fileList.length; i++) {
            formData.append("files", fileList[i]);
        }

        // Show loading state
        if (compressAllBtn) compressAllBtn.disabled = true;

        try {
            const resp = await fetch("/api/upload_file", {
                method: "POST",
                body: formData
            });
            const data = await resp.json();

            if (data.success && data.files) {
                data.files.forEach(f => {
                    if (f.success) {
                        studioFiles.push(f);
                    }
                });
                updateStudioUI();
            } else {
                alert("Upload failed: " + (data.error || "Unknown server error"));
            }
        } catch (err) {
            alert("Network error uploading files: " + err);
        } finally {
            if (batchFileInput) batchFileInput.value = "";
            if (batchFolderInput) batchFolderInput.value = "";
            updateStudioUI();
        }
    }

    async function compressItem(item) {
        if (!item || item.status === "compressed") return;

        item.status = "compressing";
        updateStudioUI();

        const level = parseInt(compressionLevelSlider ? compressionLevelSlider.value : 100, 10);
        const globalAlgo = document.getElementById("studioGlobalAlgorithm") ? document.getElementById("studioGlobalAlgorithm").value : "AUTO";

        try {
            const resp = await fetch("/api/compress_file", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    operation_id: item.operation_id,
                    compression_level: level,
                    algorithm: globalAlgo
                })
            });
            const data = await resp.json();

            if (data.success) {
                item.status = "compressed";
                item.compressed_size_display = data.compressed_size_display;
                item.space_saving_pct = data.space_saving_pct;
                item.download_url = data.download_url;
            } else {
                item.status = "ready";
                alert("Compression error for " + item.filename + ": " + (data.error || "Unknown error"));
            }
        } catch (err) {
            item.status = "ready";
            alert("Network error compressing " + item.filename + ": " + err);
        }

        updateStudioUI();
    }

    // Event Delegation on Cards Deck
    if (cardsDeck) {
        cardsDeck.addEventListener("click", function (e) {
            // Remove file button
            const removeBtn = e.target.closest(".remove-card-btn");
            if (removeBtn) {
                const opId = removeBtn.getAttribute("data-id");
                studioFiles = studioFiles.filter(f => f.operation_id !== opId);
                fetch(`/api/delete_file/${opId}`, { method: "POST" }).catch(() => {});
                updateStudioUI();
                return;
            }

            // Single Compress button
            const compBtn = e.target.closest(".card-compress-btn");
            if (compBtn) {
                const opId = compBtn.getAttribute("data-id");
                const targetItem = studioFiles.find(f => f.operation_id === opId);
                if (targetItem) {
                    compressItem(targetItem);
                }
                return;
            }
        });
    }

    // Compress All Button
    if (compressAllBtn) {
        compressAllBtn.addEventListener("click", async function () {
            const uncompressed = studioFiles.filter(f => f.status !== "compressed");
            if (uncompressed.length === 0) return;

            compressAllBtn.disabled = true;
            if (compressAllSpinner) compressAllSpinner.classList.remove("d-none");
            if (compressAllIcon) compressAllIcon.classList.add("d-none");

            for (const item of uncompressed) {
                await compressItem(item);
            }

            compressAllBtn.disabled = false;
            if (compressAllSpinner) compressAllSpinner.classList.add("d-none");
            if (compressAllIcon) compressAllIcon.classList.remove("d-none");
            updateStudioUI();
        });
    }

    // Delete All Buttons (Top & Bottom)
    function deleteAllFiles() {
        if (studioFiles.length === 0) return;
        studioFiles.forEach(f => {
            fetch(`/api/delete_file/${f.operation_id}`, { method: "POST" }).catch(() => {});
        });
        studioFiles = [];
        updateStudioUI();
    }

    if (deleteAllTopBtn) deleteAllTopBtn.addEventListener("click", deleteAllFiles);
    if (bottomTrashBtn) bottomTrashBtn.addEventListener("click", deleteAllFiles);

    // Download Batch ZIP
    if (downloadZipBtn) {
        downloadZipBtn.addEventListener("click", async function () {
            const compressedItems = studioFiles.filter(f => f.status === "compressed");
            if (compressedItems.length === 0) {
                alert("Please compress files first before downloading ZIP.");
                return;
            }

            const opIds = compressedItems.map(f => f.operation_id);
            downloadZipBtn.disabled = true;
            downloadZipBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span> Creating ZIP...';

            try {
                const resp = await fetch("/api/download_batch_zip", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ operation_ids: opIds })
                });

                if (!resp.ok) {
                    alert("Failed to build ZIP archive on server.");
                    return;
                }

                const blob = await resp.blob();
                const blobUrl = window.URL.createObjectURL(blob);
                const tempLink = document.createElement("a");
                tempLink.href = blobUrl;
                tempLink.download = "SmartCompress_Batch.zip";
                document.body.appendChild(tempLink);
                tempLink.click();
                tempLink.remove();
                window.URL.revokeObjectURL(blobUrl);
            } catch (err) {
                alert("Error downloading batch ZIP: " + err);
            } finally {
                downloadZipBtn.disabled = false;
                downloadZipBtn.innerHTML = '<i class="bi bi-file-earmark-zip-fill me-1"></i> Download ZIP';
            }
        });
    }

    // File Selector Buttons Integration
    const selectFilesTriggers = [emptySelectFilesBtn, bottomSelectFilesBtn, addMoreCircleBtn];
    selectFilesTriggers.forEach(btn => {
        if (btn) {
            btn.addEventListener("click", function (e) {
                e.preventDefault();
                if (batchFileInput) batchFileInput.click();
            });
        }
    });

    const selectFolderTriggers = [emptySelectFolderBtn, bottomSelectFolderBtn];
    selectFolderTriggers.forEach(btn => {
        if (btn) {
            btn.addEventListener("click", function (e) {
                e.preventDefault();
                if (batchFolderInput) batchFolderInput.click();
            });
        }
    });

    if (batchFileInput) {
        batchFileInput.addEventListener("change", function () {
            if (this.files && this.files.length > 0) {
                uploadFilesToStudio(this.files);
            }
        });
    }

    if (batchFolderInput) {
        batchFolderInput.addEventListener("change", function () {
            if (this.files && this.files.length > 0) {
                uploadFilesToStudio(this.files);
            }
        });
    }

    // Drag and Drop on Studio Canvas
    if (studioCanvas) {
        ["dragenter", "dragover"].forEach(evt => {
            studioCanvas.addEventListener(evt, (e) => {
                e.preventDefault();
                e.stopPropagation();
                studioCanvas.classList.add("border", "border-primary", "border-2");
            });
        });

        ["dragleave", "drop"].forEach(evt => {
            studioCanvas.addEventListener(evt, (e) => {
                e.preventDefault();
                e.stopPropagation();
                studioCanvas.classList.remove("border", "border-primary", "border-2");
            });
        });

        studioCanvas.addEventListener("drop", function (e) {
            if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                uploadFilesToStudio(e.dataTransfer.files);
            }
        });
    }

    // ====================================================
    // Tab 1: Intelligent Analytics & Algorithm Chooser Controls
    // ====================================================
    const analyticsDropzone = document.getElementById("analyticsDropzone");
    const analyticsFileInput = document.getElementById("analyticsFileInput");
    const analyticsFolderInput = document.getElementById("analyticsFolderInput");
    const analyticsPickFileBtn = document.getElementById("analyticsPickFileBtn");
    const analyticsPickFolderBtn = document.getElementById("analyticsPickFolderBtn");
    const analyticsSubmitBtn = document.getElementById("analyticsSubmitBtn");
    const analyticsSelectedDisplay = document.getElementById("analyticsSelectedDisplay");
    const analyticsSelectedName = document.getElementById("analyticsSelectedName");
    const analyticsSelectedSize = document.getElementById("analyticsSelectedSize");
    const analyticsUploadMode = document.getElementById("analyticsUploadMode");
    const analyticsRelativePaths = document.getElementById("analyticsRelativePaths");
    const analyticsFolderName = document.getElementById("analyticsFolderName");
    const lookupOpIdInput = document.getElementById("lookupOpIdInput");
    const lookupOpIdBtn = document.getElementById("lookupOpIdBtn");

    if (lookupOpIdBtn && lookupOpIdInput) {
        function doLookup() {
            const val = lookupOpIdInput.value.trim();
            if (val) {
                window.location.href = `/result/${encodeURIComponent(val)}`;
            } else {
                alert("Please enter an Operation ID to look up.");
            }
        }
        lookupOpIdBtn.addEventListener("click", doLookup);
        lookupOpIdInput.addEventListener("keydown", function (e) {
            if (e.key === "Enter") {
                e.preventDefault();
                doLookup();
            }
        });
    }

    if (analyticsPickFileBtn && analyticsFileInput) {
        analyticsPickFileBtn.addEventListener("click", function (e) {
            e.preventDefault();
            analyticsFileInput.click();
        });
    }

    if (analyticsPickFolderBtn && analyticsFolderInput) {
        analyticsPickFolderBtn.addEventListener("click", function (e) {
            e.preventDefault();
            analyticsFolderInput.click();
        });
    }

    if (analyticsFileInput) {
        analyticsFileInput.addEventListener("change", function () {
            if (this.files && this.files.length > 0) {
                const file = this.files[0];
                if (analyticsUploadMode) analyticsUploadMode.value = "file";
                if (analyticsSelectedDisplay) analyticsSelectedDisplay.classList.remove("d-none");
                if (analyticsSelectedName) analyticsSelectedName.textContent = file.name;
                if (analyticsSelectedSize) analyticsSelectedSize.textContent = `(${formatBytes(file.size)})`;
                if (analyticsSubmitBtn) analyticsSubmitBtn.disabled = false;
            }
        });
    }

    if (analyticsFolderInput) {
        analyticsFolderInput.addEventListener("change", function () {
            if (this.files && this.files.length > 0) {
                const files = Array.from(this.files);
                const relPaths = files.map(f => f.webkitRelativePath || f.name);
                let folderName = "Archive_Folder";
                if (relPaths.length > 0 && relPaths[0].includes("/")) {
                    folderName = relPaths[0].split("/")[0];
                }
                let totalBytes = files.reduce((acc, f) => acc + f.size, 0);

                if (analyticsUploadMode) analyticsUploadMode.value = "folder";
                if (analyticsRelativePaths) analyticsRelativePaths.value = JSON.stringify(relPaths);
                if (analyticsFolderName) analyticsFolderName.value = folderName;
                if (analyticsSelectedDisplay) analyticsSelectedDisplay.classList.remove("d-none");
                if (analyticsSelectedName) analyticsSelectedName.textContent = `Folder: ${folderName} (${files.length} files)`;
                if (analyticsSelectedSize) analyticsSelectedSize.textContent = `(${formatBytes(totalBytes)})`;
                if (analyticsSubmitBtn) analyticsSubmitBtn.disabled = false;
            }
        });
    }

    // Drag-and-drop on Analytics Dropzone
    if (analyticsDropzone) {
        ["dragenter", "dragover"].forEach(evt => {
            analyticsDropzone.addEventListener(evt, (e) => {
                e.preventDefault();
                e.stopPropagation();
                analyticsDropzone.classList.add("border-primary", "bg-primary-subtle", "bg-opacity-10");
            });
        });

        ["dragleave", "drop"].forEach(evt => {
            analyticsDropzone.addEventListener(evt, (e) => {
                e.preventDefault();
                e.stopPropagation();
                analyticsDropzone.classList.remove("border-primary", "bg-primary-subtle", "bg-opacity-10");
            });
        });

        analyticsDropzone.addEventListener("drop", function (e) {
            if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                analyticsFileInput.files = e.dataTransfer.files;
                const file = e.dataTransfer.files[0];
                if (analyticsUploadMode) analyticsUploadMode.value = "file";
                if (analyticsSelectedDisplay) analyticsSelectedDisplay.classList.remove("d-none");
                if (analyticsSelectedName) analyticsSelectedName.textContent = file.name;
                if (analyticsSelectedSize) analyticsSelectedSize.textContent = `(${formatBytes(file.size)})`;
                if (analyticsSubmitBtn) analyticsSubmitBtn.disabled = false;
            }
        });
    }

    // Initialize UI on load
    updateStudioUI();

    // Compression submit loading feedback
    const compressForm = document.getElementById("compressForm");
    const compressBtn = document.getElementById("compressBtn");
    const compressSpinner = document.getElementById("compressSpinner");
    const compressIcon = document.getElementById("compressIcon");

    if (compressForm && compressBtn) {
        compressForm.addEventListener("submit", function () {
            compressBtn.disabled = true;
            if (compressSpinner) compressSpinner.classList.remove("d-none");
            if (compressIcon) compressIcon.classList.add("d-none");
            compressBtn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span> Compressing...`;
        });
    }

    // ----------------------------------------------------
    // Progressive Web App (PWA) Service Worker Registration
    // ----------------------------------------------------
    if ("serviceWorker" in navigator) {
        window.addEventListener("load", function () {
            navigator.serviceWorker.register("/service-worker.js").then(
                function (registration) {
                    console.log("[PWA] ServiceWorker registered with scope: ", registration.scope);
                },
                function (err) {
                    console.log("[PWA] ServiceWorker registration failed: ", err);
                }
            );
        });
    }
});

/**
 * Run Live Benchmark on all 5 Lossless Algorithms for the current operation.
 */
function runBenchmark(operationId) {
    const btn = document.getElementById("benchmarkBtn");
    const spinner = document.getElementById("benchSpinner");
    const icon = document.getElementById("benchIcon");
    const container = document.getElementById("benchmarkContainer");
    const tbody = document.getElementById("benchmarkTableBody");

    if (!btn || !spinner || !icon) return;

    btn.disabled = true;
    spinner.classList.remove("d-none");
    icon.classList.add("d-none");
    btn.innerHTML = `<span class="spinner-border spinner-border-sm me-1"></span> Benchmarking Algorithms (PDF-Deflate, 7Z, ZIP, GZIP, BZIP2, LZMA)...`;

    fetch(`/api/benchmark/${operationId}`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        }
    })
    .then(response => response.json())
    .then(data => {
        btn.disabled = false;
        spinner.classList.add("d-none");
        icon.classList.remove("d-none");
        btn.innerHTML = `<i class="bi bi-speedometer me-1"></i> Re-Run Benchmark`;

        if (!data.success) {
            alert("Benchmark notice: " + (data.error || "Unknown server error"));
            return;
        }

        // Render Benchmark Table
        tbody.innerHTML = "";
        data.benchmarks.forEach(item => {
            const tr = document.createElement("tr");
            const savingsClass = item.space_saving_pct >= 0 ? "text-white fw-bold" : "text-secondary";
            
            tr.innerHTML = `
                <td class="fw-bold text-white">${item.algorithm}</td>
                <td class="text-white">${item.compressed_size_display}</td>
                <td class="${savingsClass}">${item.bytes_saved.toLocaleString()} B</td>
                <td class="${savingsClass} fs-6">${item.space_saving_pct}%</td>
                <td class="text-secondary-light">${item.duration}s</td>
                <td class="text-secondary-light">${item.speed_mb_s} MB/s</td>
                <td>
                    <button class="btn btn-sm btn-outline-secondary text-white py-0 px-2" onclick="selectAndCompress('${item.algorithm}')">
                        Use ${item.algorithm}
                    </button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        container.classList.remove("d-none");
        container.scrollIntoView({ behavior: "smooth" });
    })
    .catch(err => {
        btn.disabled = false;
        spinner.classList.add("d-none");
        icon.classList.remove("d-none");
        btn.innerHTML = `<i class="bi bi-speedometer me-1"></i> Benchmark Algorithms`;
        alert("Network error executing benchmark: " + err);
    });
}

/**
 * Helper to select an algorithm from benchmark table and trigger form submission
 */
function selectAndCompress(algo) {
    const select = document.getElementById("algorithmSelect");
    const form = document.getElementById("compressForm");
    if (select && form) {
        select.value = algo;
        form.submit();
    }
}
