document.addEventListener("DOMContentLoaded", () => {
    // DOM Elements
    const urlForm = document.getElementById("urlForm");
    const videoUrlInput = document.getElementById("videoUrlInput");
    const pasteBtn = document.getElementById("pasteBtn");
    const fetchBtn = document.getElementById("fetchBtn");
    const errorAlert = document.getElementById("errorAlert");
    const errorTitle = document.getElementById("errorTitle");
    const errorMessage = document.getElementById("errorMessage");

    // Preview Section
    const videoPreviewSection = document.getElementById("videoPreviewSection");
    const videoThumb = document.getElementById("videoThumb");
    const videoDuration = document.getElementById("videoDuration");
    const videoTitle = document.getElementById("videoTitle");
    const videoChannel = document.getElementById("videoChannel");
    const videoViews = document.getElementById("videoViews");
    const qualitiesGrid = document.getElementById("qualitiesGrid");
    const startDownloadBtn = document.getElementById("startDownloadBtn");
    const downloadBtnText = document.getElementById("downloadBtnText");

    // Progress Section
    const progressSection = document.getElementById("progressSection");
    const progressSpinner = document.getElementById("progressSpinner");
    const progressStatusText = document.getElementById("progressStatusText");
    const progressSpeed = document.getElementById("progressSpeed");
    const progressEta = document.getElementById("progressEta");
    const progressBar = document.getElementById("progressBar");
    const progressMessage = document.getElementById("progressMessage");
    const progressPercentage = document.getElementById("progressPercentage");
    const completedBox = document.getElementById("completedBox");
    const completedDetails = document.getElementById("completedDetails");
    const saveFileLink = document.getElementById("saveFileLink");
    const revealInFinderBtn = document.getElementById("revealInFinderBtn");

    // Header & History
    const openFolderBtn = document.getElementById("openFolderBtn");
    const historyToggleBtn = document.getElementById("historyToggleBtn");
    const historyBadge = document.getElementById("historyBadge");
    const historySection = document.getElementById("historySection");
    const historyContainer = document.getElementById("historyContainer");
    const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");
    const sampleChips = document.querySelectorAll(".sample-chip");

    // State
    let currentVideoData = null;
    let selectedQuality = "1080p";
    let activePollInterval = null;

    // Toast notifications
    function showToast(message, type = "success") {
        const container = document.getElementById("toastContainer");
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <span>${type === "success" ? "✓" : "⚠️"}</span>
            <span>${message}</span>
        `;
        container.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transform = "translateX(100%)";
            toast.style.transition = "all 0.3s ease";
            setTimeout(() => toast.remove(), 300);
        }, 3500);
    }

    function showError(title, msg) {
        errorTitle.textContent = title;
        errorMessage.textContent = msg;
        errorAlert.style.display = "flex";
        errorAlert.scrollIntoView({ behavior: "smooth", block: "center" });
    }

    function hideError() {
        errorAlert.style.display = "none";
    }

    // Paste button
    pasteBtn.addEventListener("click", async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                videoUrlInput.value = text.trim();
                hideError();
                fetchVideoInfo();
            }
        } catch (err) {
            showToast("Clipboard access allow karein ya link direct paste karein", "error");
        }
    });

    // Sample links
    sampleChips.forEach(chip => {
        chip.addEventListener("click", () => {
            videoUrlInput.value = chip.getAttribute("data-url");
            hideError();
            fetchVideoInfo();
        });
    });

    // Form submit / Fetch
    urlForm.addEventListener("submit", (e) => {
        e.preventDefault();
        fetchVideoInfo();
    });

    fetchBtn.addEventListener("click", () => {
        fetchVideoInfo();
    });

    async function fetchVideoInfo() {
        const url = videoUrlInput.value.trim();
        if (!url) {
            showError("Input Khali Hai", "Kripya valid YouTube video link enter karein.");
            return;
        }

        hideError();
        setFetchLoading(true);

        try {
            const res = await fetch("/api/info", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ url })
            });

            const data = await res.json();

            if (!res.ok || !data.success) {
                showError("Video Fetch Nahi Hua", data.error || "YouTube server se data prapt nahi ho saka.");
                return;
            }

            currentVideoData = data;
            renderVideoPreview(data);
            showToast("Video metadata prapt ho gaya!", "success");

        } catch (err) {
            showError("Connection Error", "Local server se connect nahi ho saka: " + err.message);
        } finally {
            setFetchLoading(false);
        }
    }

    function setFetchLoading(isLoading) {
        const btnText = fetchBtn.querySelector(".btn-text");
        const btnLoader = fetchBtn.querySelector(".btn-loader");
        if (isLoading) {
            btnText.style.display = "none";
            btnLoader.style.display = "inline-flex";
            fetchBtn.disabled = true;
        } else {
            btnText.style.display = "inline";
            btnLoader.style.display = "none";
            fetchBtn.disabled = false;
        }
    }

    function renderVideoPreview(data) {
        videoThumb.src = data.thumbnail || "https://images.unsplash.com/photo-1611162617213-7d7a39e9b1d7?w=800&auto=format&fit=crop";
        videoDuration.textContent = data.duration;
        videoTitle.textContent = data.title;
        videoChannel.textContent = data.channel || "YouTube Channel";
        videoViews.textContent = `${data.views} views`;

        // Render qualities
        qualitiesGrid.innerHTML = "";
        
        // If video has 4K, default to 4K Ultra HD! Otherwise 1080p
        selectedQuality = data.has_4k ? "2160p" : "1080p";

        let initialLabel = data.has_4k ? "4K Ultra HD" : "1080p Full HD";

        data.qualities.forEach(q => {
            const card = document.createElement("div");
            const isSelected = q.id === selectedQuality;
            const is4KCard = q.is_4k || q.id === "2160p";
            
            card.className = `quality-card ${isSelected ? "selected" : ""} ${is4KCard ? "card-4k" : ""}`;
            card.dataset.id = q.id;
            card.dataset.label = q.label;
            card.innerHTML = `
                <div class="quality-top">
                    <span class="quality-label">${q.label}</span>
                    <span class="quality-badge ${is4KCard ? "badge-4k" : ""}">${q.badge}</span>
                </div>
                <div class="quality-desc">${q.format_desc}</div>
            `;

            card.addEventListener("click", () => {
                document.querySelectorAll(".quality-card").forEach(c => c.classList.remove("selected"));
                card.classList.add("selected");
                selectedQuality = q.id;
                updateDownloadButtonLabel(q.label);
            });

            qualitiesGrid.appendChild(card);
        });

        updateDownloadButtonLabel(initialLabel);
        videoPreviewSection.style.display = "block";
        videoPreviewSection.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    function updateDownloadButtonLabel(qualityLabel) {
        if (selectedQuality === "mp3" || selectedQuality === "m4a") {
            downloadBtnText.textContent = `Download Audio (${qualityLabel})`;
        } else if (selectedQuality === "2160p") {
            downloadBtnText.textContent = `Download in 4K Ultra HD (MP4 + Studio Audio)`;
        } else {
            downloadBtnText.textContent = `Download in ${qualityLabel} (MP4 + Audio)`;
        }
    }

    // Start Download
    startDownloadBtn.addEventListener("click", async () => {
        if (!currentVideoData) return;

        startDownloadBtn.disabled = true;
        progressSection.style.display = "block";
        completedBox.style.display = "none";
        progressBar.style.width = "0%";
        progressPercentage.textContent = "0%";
        progressSpeed.textContent = "Speed: --";
        progressEta.textContent = "ETA: --";
        progressStatusText.textContent = `Downloading ${currentVideoData.title.slice(0, 40)}...`;
        progressMessage.textContent = "Connecting to YouTube high-speed streams...";
        progressSpinner.style.display = "inline-block";

        progressSection.scrollIntoView({ behavior: "smooth", block: "center" });

        try {
            const res = await fetch("/api/download", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    url: currentVideoData.webpage_url,
                    quality: selectedQuality,
                    title: currentVideoData.title
                })
            });

            const data = await res.json();
            if (!res.ok || !data.success) {
                showError("Download Error", data.error || "Download initiate nahi ho saka.");
                startDownloadBtn.disabled = false;
                return;
            }

            pollProgress(data.task_id);

        } catch (err) {
            showError("Network Error", "Server error: " + err.message);
            startDownloadBtn.disabled = false;
        }
    });

    function pollProgress(taskId) {
        if (activePollInterval) clearInterval(activePollInterval);

        activePollInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/progress/${taskId}`);
                if (!res.ok) {
                    clearInterval(activePollInterval);
                    return;
                }
                const data = await res.json();
                const task = data.task;

                if (task) {
                    progressBar.style.width = `${task.percent}%`;
                    progressPercentage.textContent = `${task.percent.toFixed(1)}%`;
                    progressSpeed.textContent = `Speed: ${task.speed || "--"}`;
                    progressEta.textContent = `ETA: ${task.eta || "--"}`;
                    progressMessage.textContent = task.message;

                    if (task.status === "completed") {
                        clearInterval(activePollInterval);
                        onDownloadCompleted(task);
                    } else if (task.status === "error") {
                        clearInterval(activePollInterval);
                        progressStatusText.textContent = "Download Failed";
                        progressSpinner.style.display = "none";
                        showError("Download Fail Hua", task.message);
                        startDownloadBtn.disabled = false;
                    }
                }
            } catch (err) {
                console.error("Progress poll error:", err);
            }
        }, 600);
    }

    function onDownloadCompleted(task) {
        progressSpinner.style.display = "none";
        progressStatusText.textContent = "Download Complete!";
        progressBar.style.width = "100%";
        progressPercentage.textContent = "100%";
        progressMessage.textContent = "High quality file ready!";
        startDownloadBtn.disabled = false;

        completedDetails.textContent = `${task.filename} (${task.filesize})`;
        saveFileLink.href = task.download_url;
        saveFileLink.setAttribute("download", task.filename);
        completedBox.style.display = "flex";

        showToast("Download aur FFmpeg muxing poora ho gaya!", "success");
        loadHistory();

        // Auto trigger save to browser downloads
        const autoSave = document.createElement("a");
        autoSave.href = task.download_url;
        autoSave.setAttribute("download", task.filename);
        document.body.appendChild(autoSave);
        autoSave.click();
        autoSave.remove();
    }

    // Open Downloads Folder in Mac Finder
    openFolderBtn.addEventListener("click", async () => {
        try {
            const res = await fetch("/api/open-downloads", { method: "POST" });
            const data = await res.json();
            if (data.success) {
                showToast("Mac Finder me Downloads folder open ho gaya! 📂", "success");
            } else {
                showToast("Folder open nahi ho saka", "error");
            }
        } catch (err) {
            showToast("Server error", "error");
        }
    });

    revealInFinderBtn.addEventListener("click", () => {
        openFolderBtn.click();
    });

    // Toggle & Load History
    historyToggleBtn.addEventListener("click", () => {
        historySection.scrollIntoView({ behavior: "smooth" });
    });

    refreshHistoryBtn.addEventListener("click", () => {
        loadHistory();
    });

    async function loadHistory() {
        try {
            const res = await fetch("/api/history");
            const data = await res.json();
            if (data.success) {
                renderHistory(data.files);
            }
        } catch (err) {
            console.error("History fetch error:", err);
        }
    }

    function renderHistory(files) {
        historyBadge.textContent = files.length;

        if (files.length === 0) {
            historyContainer.innerHTML = `
                <div class="empty-history">
                    <span>Abhi tak koi downloaded file nahi hai. Upar link paste karke download karein!</span>
                </div>
            `;
            return;
        }

        historyContainer.innerHTML = "";
        files.forEach(f => {
            const item = document.createElement("div");
            item.className = "history-item";
            item.innerHTML = `
                <div class="history-file-info">
                    <span class="ext-badge">${f.ext}</span>
                    <div class="history-text">
                        <div class="history-name" title="${f.display_name}">${f.display_name}</div>
                        <div class="history-meta">
                            <span>${f.size}</span>
                            <span>•</span>
                            <span>${f.created_at}</span>
                        </div>
                    </div>
                </div>
                <div class="history-actions">
                    <a href="/api/history/download/${encodeURIComponent(f.filename)}" class="btn btn-secondary btn-sm" download title="Download to Mac">
                        ⬇ Save
                    </a>
                    <button class="btn btn-ghost btn-sm delete-file-btn" data-filename="${encodeURIComponent(f.filename)}" title="Delete File">
                        🗑
                    </button>
                </div>
            `;

            const delBtn = item.querySelector(".delete-file-btn");
            delBtn.addEventListener("click", async () => {
                if (confirm(`Kya aap "${f.display_name}" ko delete karna chahte hain?`)) {
                    await deleteFile(f.filename);
                }
            });

            historyContainer.appendChild(item);
        });
    }

    async function deleteFile(filename) {
        try {
            const res = await fetch(`/api/history/${filename}`, { method: "DELETE" });
            const data = await res.json();
            if (data.success) {
                showToast("File delete ho gayi", "success");
                loadHistory();
            }
        } catch (err) {
            showToast("Delete karne me error", "error");
        }
    }

    // Initial load
    loadHistory();
});
