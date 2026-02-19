document.addEventListener('DOMContentLoaded', () => {
    // Theme Management
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const themeIcon = themeToggleBtn.querySelector('i');

    // Check saved theme
    const savedTheme = localStorage.getItem('visionx-theme');
    if (savedTheme === 'light') {
        document.body.classList.add('light-mode');
        themeIcon.classList.replace('fa-sun', 'fa-moon');
    }

    themeToggleBtn.addEventListener('click', () => {
        document.body.classList.toggle('light-mode');
        const isLight = document.body.classList.contains('light-mode');

        // Update Icon
        if (isLight) {
            themeIcon.classList.replace('fa-sun', 'fa-moon');
            localStorage.setItem('visionx-theme', 'light');
        } else {
            themeIcon.classList.replace('fa-moon', 'fa-sun');
            localStorage.setItem('visionx-theme', 'dark');
        }
    });

    // ===== ELEMENTS =====
    const searchForm = document.getElementById('searchForm');
    const searchInput = document.getElementById('searchQuery');
    const searchBtn = document.getElementById('searchBtn');
    const searchLoader = document.getElementById('searchLoader');
    const resultsArea = document.getElementById('resultsArea');
    const messageArea = document.getElementById('messageArea');

    // Tabs
    const tabSearch = document.getElementById('tabSearch');
    const tabHistory = document.getElementById('tabHistory');
    const sectionSearch = document.getElementById('sectionSearch');
    const sectionHistory = document.getElementById('sectionHistory');

    // FAB
    const fabContainer = document.getElementById('fabContainer');
    const batchDownloadBtn = document.getElementById('batchDownloadBtn');
    const selectedCount = document.getElementById('selectedCount');

    // Modal
    const downloadModal = document.getElementById('downloadModal');
    const modalCloseBtn = document.getElementById('modalCloseBtn');
    const modalCancelBtn = document.getElementById('modalCancelBtn');
    const modalConfirmBtn = document.getElementById('modalConfirmBtn');
    const modalVideoCount = document.getElementById('modalVideoCount');
    const modalVideoList = document.getElementById('modalVideoList');
    const modalFormatSelect = document.getElementById('modalFormatSelect');

    // Download Panel (REMOVED - now part of History)
    const activeDownloads = document.getElementById('activeDownloads');
    const downloadQueue = document.getElementById('downloadQueue');
    // const closePanelBtn = document.getElementById('closePanelBtn'); // Removed

    // History
    const historyList = document.getElementById('historyList');
    const clearHistoryBtn = document.getElementById('clearHistoryBtn');

    // ===== STATE =====
    let selectedVideos = new Map(); // url -> {id, title, thumbnail, url, ...}
    let isDownloading = false;
    let allVideoData = []; // Store all rendered video data for reference

    // ===== INIT =====
    fetchTrending();
    renderHistory();

    // ===== TABS =====
    document.querySelector('.nav-brand').addEventListener('click', () => {
        switchTab('search');
    });

    tabSearch.addEventListener('click', () => switchTab('search'));
    tabHistory.addEventListener('click', () => switchTab('history'));

    function switchTab(tab) {
        tabSearch.classList.toggle('active', tab === 'search');
        tabHistory.classList.toggle('active', tab === 'history');
        sectionSearch.classList.toggle('active', tab === 'search');
        sectionHistory.classList.toggle('active', tab === 'history');
        if (tab === 'history') renderHistory();
    }

    // ===== TRENDING =====
    async function fetchTrending() {
        // Simple skeleton or loader
        resultsArea.innerHTML = '<div style="grid-column: 1/-1; text-align:center; padding: 40px; color: var(--text-muted);">Carregando vídeos...</div>';

        setSearchLoading(true);
        try {
            const response = await fetch('/trending');
            const data = await response.json();
            if (data.results) {
                renderResults(data.results);
            }
        } catch (e) {
            console.error(e);
        } finally {
            setSearchLoading(false);
        }
    }

    // ===== SEARCH =====
    searchForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = searchInput.value.trim();
        if (!query) return;

        // Reset state
        switchTab('search');
        setSearchLoading(true);
        resultsArea.classList.add('opacity-50');

        // Check if query is a YouTube URL
        // Allow anything that looks like a URL containing youtube or youtu.be
        const isUrl = /(youtube\.com|youtu\.be)\/.+/i.test(query);

        try {
            const response = await fetch(`/search?q=${encodeURIComponent(query)}`);
            if (!response.ok) throw new Error('Erro na busca.');
            const data = await response.json();
            resultsArea.classList.remove('opacity-50');

            if (data.results && data.results.length > 0) {
                renderResults(data.results);

                // Auto-open modal if it was a URL search
                if (isUrl && data.results.length === 1) {
                    const video = data.results[0];
                    console.log("Auto-opening modal for:", video.title);

                    // Clear previous selection if any
                    selectedVideos.clear();

                    // Auto select
                    selectedVideos.set(video.url, video);

                    // Update UI card selection
                    const card = document.querySelector(`.video-card`); // Since it's single result, it's the first one
                    if (card) card.classList.add('selected');

                    updateFab();
                    openModal();
                }
            } else {
                showMessage('Nenhum vídeo encontrado.', 'error');
            }
        } catch (error) {
            console.error('Search error:', error);
            showMessage('Erro ao buscar vídeos.', 'error');
            resultsArea.classList.remove('opacity-50');
        } finally {
            setSearchLoading(false);
        }
    });

    // ===== RENDER RESULTS =====
    function renderResults(videos) {
        resultsArea.innerHTML = '';
        allVideoData = videos;

        videos.forEach(video => {
            const card = document.createElement('div');
            card.className = 'video-card';
            if (selectedVideos.has(video.url)) {
                card.classList.add('selected');
            }

            card.dataset.url = video.url;
            const thumbUrl = video.thumbnail || `https://i.ytimg.com/vi/${video.id}/hqdefault.jpg`;

            card.innerHTML = `
                <div class="thumb-container">
                    <img src="${thumbUrl}" alt="${video.title || ''}" class="video-thumb" loading="lazy">
                    ${video.duration ? `<span class="video-duration">${formatDuration(video.duration)}</span>` : ''}
                </div>
                <div class="video-info">
                    <h3 class="video-title" title="${video.title || ''}">${video.title || 'Sem título'}</h3>
                    <p class="video-meta">${video.uploader || ''}</p>
                </div>
            `;

            card.addEventListener('click', () => toggleSelection(card, video));
            resultsArea.appendChild(card);
        });
    }

    // ===== SELECTION =====
    let socialModalShown = sessionStorage.getItem('socialModalShown') === 'true';

    function toggleSelection(card, video) {
        if (selectedVideos.has(video.url)) {
            selectedVideos.delete(video.url);
            card.classList.remove('selected');
        } else {
            // Check if selecting more than 5 and social modal not yet shown
            if (selectedVideos.size >= 5 && !socialModalShown) {
                socialModalShown = true;
                sessionStorage.setItem('socialModalShown', 'true');
                // Still select the video
                selectedVideos.set(video.url, video);
                card.classList.add('selected');
                updateFab();
                showSocialModal();
                return;
            }
            selectedVideos.set(video.url, video);
            card.classList.add('selected');
        }
        updateFab();
    }

    // ===== SOCIAL MODAL =====
    const socialModal = document.getElementById('socialModal');
    const socialModalCloseBtn = document.getElementById('socialModalCloseBtn');
    const socialModalContinueBtn = document.getElementById('socialModalContinueBtn');

    function showSocialModal() {
        socialModal.classList.remove('hidden');
    }

    function closeSocialModal() {
        socialModal.classList.add('hidden');
    }

    socialModalCloseBtn.addEventListener('click', closeSocialModal);
    socialModalContinueBtn.addEventListener('click', closeSocialModal);
    socialModal.addEventListener('click', (e) => {
        if (e.target === socialModal) closeSocialModal();
    });

    function updateFab() {
        const count = selectedVideos.size;
        selectedCount.textContent = count;
        if (count > 0) {
            fabContainer.classList.remove('hidden');
        } else {
            fabContainer.classList.add('hidden');
        }
    }

    // ===== MODAL =====
    batchDownloadBtn.addEventListener('click', () => {
        if (selectedVideos.size === 0 || isDownloading) return;
        openModal();
    });

    function openModal() {
        const videos = Array.from(selectedVideos.values());
        modalVideoCount.textContent = videos.length;

        // Render thumbnails in modal
        modalVideoList.innerHTML = '';
        videos.forEach(v => {
            const thumb = v.thumbnail || `https://i.ytimg.com/vi/${v.id}/hqdefault.jpg`;
            const item = document.createElement('div');
            item.className = 'modal-video-item';
            item.innerHTML = `
                <img src="${thumb}" alt="${v.title || ''}">
                <div class="modal-item-title">${v.title || 'Sem título'}</div>
            `;
            modalVideoList.appendChild(item);
        });

        downloadModal.classList.remove('hidden');
    }

    function closeModal() {
        downloadModal.classList.add('hidden');
    }

    modalCloseBtn.addEventListener('click', closeModal);
    modalCancelBtn.addEventListener('click', closeModal);
    downloadModal.addEventListener('click', (e) => {
        if (e.target === downloadModal) closeModal();
    });

    // ===== CONFIRM & START DOWNLOADS =====
    modalConfirmBtn.addEventListener('click', async () => {
        closeModal();
        const format = modalFormatSelect.value;
        const videos = Array.from(selectedVideos.values());
        startBatchDownload(videos, format);
    });

    // ===== BATCH DOWNLOAD WITH PANEL =====
    async function startBatchDownload(videos, format) {
        isDownloading = true;
        fabContainer.classList.add('hidden');

        // Show active downloads section in History tab
        switchTab('history');
        if (activeDownloads) activeDownloads.classList.remove('hidden');

        downloadQueue.innerHTML = '';

        // Create queue items
        const items = videos.map((video, idx) => {
            const thumb = video.thumbnail || `https://i.ytimg.com/vi/${video.id}/hqdefault.jpg`;
            const el = document.createElement('div');
            el.className = 'download-item';
            el.id = `dl-item-${idx}`;
            el.innerHTML = `
                <img src="${thumb}" class="download-item-thumb" alt="">
                <div class="download-item-info">
                    <div class="download-item-title">${video.title || 'Sem título'}</div>
                    <div class="download-item-status" id="dl-status-${idx}">Na fila...</div>
                    <div class="download-item-progress">
                        <div class="download-item-progress-bar" id="dl-bar-${idx}"></div>
                    </div>
                </div>
                <div class="download-actions" style="display: flex; gap: 8px; align-items: center;">
                     <button class="cancel-btn hidden" id="dl-cancel-${idx}" title="Cancelar">
                        <i class="fa-solid fa-xmark"></i>
                     </button>
                    <div class="download-item-icon waiting" id="dl-icon-${idx}">
                        <i class="fa-solid fa-clock"></i>
                    </div>
                </div>
            `;
            downloadQueue.appendChild(el);
            return { video, el, idx };
        });

        let successCount = 0;

        // Process one by one
        for (const item of items) {
            const statusEl = document.getElementById(`dl-status-${item.idx}`);
            const barEl = document.getElementById(`dl-bar-${item.idx}`);
            const iconEl = document.getElementById(`dl-icon-${item.idx}`);
            const cancelBtn = document.getElementById(`dl-cancel-${item.idx}`);

            // Set downloading state
            iconEl.className = 'download-item-icon downloading';
            iconEl.innerHTML = '<i class="fa-solid fa-spinner"></i>';
            statusEl.textContent = 'Conectando ao YouTube...';
            cancelBtn.classList.remove('hidden');

            // Unique Client ID for this download (passed to downloadSingleVideo)
            // We need to generate it here to pass to cancel function
            const clientId = Math.random().toString(36).substring(7);

            // Cancel Handler
            const abortController = new AbortController();
            const cancelHandler = async () => {
                cancelBtn.disabled = true;
                statusEl.textContent = 'Cancelando...';
                try {
                    await fetch('/cancel', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ client_id: clientId })
                    });
                    // We also abort the fetch on frontend side if possible, 
                    // but backend cancellation is key.
                    abortController.abort();
                } catch (e) { console.error(e); }
            };
            cancelBtn.onclick = cancelHandler;

            try {
                await downloadSingleVideo(item.video.url, format, statusEl, barEl, clientId, abortController.signal);
                iconEl.className = 'download-item-icon done';
                iconEl.innerHTML = '<i class="fa-solid fa-check-circle"></i>';
                statusEl.textContent = 'Concluído ✓';
                barEl.style.width = '100%';
                successCount++;

                // Save to history
                addToHistory(item.video, format);
            } catch (err) {
                if (err.message && err.message.includes('cancelado')) {
                    statusEl.textContent = 'Cancelado pelo usuário.';
                    iconEl.className = 'download-item-icon';
                    iconEl.innerHTML = '<i class="fa-solid fa-ban" style="color: var(--text-muted);"></i>';
                    barEl.style.background = 'var(--text-muted)';
                } else {
                    iconEl.className = 'download-item-icon error';
                    iconEl.innerHTML = '<i class="fa-solid fa-exclamation-circle"></i>';
                    statusEl.textContent = `Erro: ${err}`;
                    barEl.style.width = '0%';
                    barEl.style.background = 'var(--error)';
                }
            } finally {
                cancelBtn.classList.add('hidden');
            }


            // Small delay between downloads
            await sleep(800);
        }

        // Final
        const summaryEl = document.createElement('div');
        summaryEl.className = 'download-item';
        summaryEl.style.background = successCount === items.length
            ? 'rgba(0, 255, 128, 0.08)'
            : 'rgba(255, 170, 0, 0.08)';
        summaryEl.innerHTML = `
            <div class="download-item-info" style="text-align:center;">
                <div class="download-item-title" style="font-size:1rem;">
                    ${successCount === items.length ? '🎉 Todos os downloads concluídos!' : `⚠️ ${successCount}/${items.length} concluídos`}
                </div>
            </div>
        `;
        downloadQueue.appendChild(summaryEl);

        isDownloading = false;
        // Clear selection
        selectedVideos.clear();
        document.querySelectorAll('.video-card.selected').forEach(c => c.classList.remove('selected'));
        updateFab();
    }

    async function downloadSingleVideo(url, format, statusEl, barEl, clientId, signal) {
        return new Promise(async (resolve, reject) => {
            if (!clientId) clientId = Math.random().toString(36).substring(7);

            // Abort listener
            if (signal) {
                signal.addEventListener('abort', () => {
                    reject(new Error('Download cancelado pelo usuário.'));
                });
            }

            // SSE for progress
            const eventSource = new EventSource(`/progress/${clientId}`);
            eventSource.onmessage = (e) => {
                const d = JSON.parse(e.data);
                if (d.message) {
                    if (d.message.includes('100%')) {
                        statusEl.textContent = 'Processando e transferindo...';
                        barEl.style.width = '100%';
                    } else if (d.message.includes('[download]')) {
                        const match = d.message.match(/(\d+\.?\d*)%/);
                        if (match) {
                            const pct = match[1];
                            statusEl.textContent = `Baixando: ${pct}%`;
                            barEl.style.width = `${pct}%`;
                        }
                    } else {
                        statusEl.textContent = d.message.substring(0, 60);
                    }
                }
            };
            eventSource.onerror = () => eventSource.close();

            try {
                const response = await fetch('/download', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url, client_id: clientId, format })
                });

                if (!response.ok) {
                    const err = await response.json().catch(() => ({}));
                    throw new Error(err.error || `HTTP ${response.status}`);
                }

                const blob = await response.blob();
                const contentDisposition = response.headers.get('Content-Disposition');
                let filename = 'video.mp4';
                if (contentDisposition) {
                    const match = contentDisposition.match(/filename="?([^"]+)"?/);
                    if (match && match[1]) filename = match[1];
                }

                // Trigger browser download
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = downloadUrl;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(downloadUrl);

                eventSource.close();
                resolve();
            } catch (error) {
                eventSource.close();
                reject(error.message || error);
            }
        });
    }

    // ===== CLOSE PANEL (REMOVED) =====


    // ===== HISTORY (localStorage) =====
    function getHistory() {
        try {
            return JSON.parse(localStorage.getItem('visionx_history') || '[]');
        } catch { return []; }
    }

    function saveHistory(history) {
        localStorage.setItem('visionx_history', JSON.stringify(history));
    }

    function addToHistory(video, format) {
        const history = getHistory();
        let formatLabel = 'Vídeo Original';

        if (format === 'mp3') formatLabel = 'Áudio MP3';
        if (format === 'thumbnail') formatLabel = 'Capa';

        history.unshift({
            id: video.id,
            title: video.title,
            thumbnail: video.thumbnail || `https://i.ytimg.com/vi/${video.id}/hqdefault.jpg`,
            url: video.url,
            format: formatLabel,
            date: new Date().toISOString()
        });

        // Keep only last 100
        if (history.length > 100) history.length = 100;
        saveHistory(history);
    }

    function renderHistory() {
        const history = getHistory();
        historyList.innerHTML = '';

        if (history.length === 0) {
            historyList.innerHTML = '<p class="empty-history">Nenhum download realizado ainda.</p>';
            return;
        }

        history.forEach(item => {
            const el = document.createElement('div');
            el.className = 'history-item';

            let badgeClass = 'mp4';
            if (item.format === 'Áudio MP3' || item.format === 'MP3') badgeClass = 'mp3';
            if (item.format === 'Capa' || item.format === 'Thumbnail') badgeClass = 'thumbnail';
            const dateStr = formatDate(item.date);

            el.innerHTML = `
                <img src="${item.thumbnail}" class="history-item-thumb" alt="" loading="lazy">
                <div class="history-item-info">
                    <div class="history-item-title" title="${item.title || ''}">${item.title || 'Sem título'}</div>
                    <div class="history-item-meta">
                        <span>${dateStr}</span>
                    </div>
                </div>
                <span class="history-item-badge ${badgeClass}">${item.format}</span>
            `;
            historyList.appendChild(el);
        });
    }

    clearHistoryBtn.addEventListener('click', () => {
        if (confirm('Limpar todo o histórico de downloads?')) {
            localStorage.removeItem('visionx_history');
            renderHistory();
        }
    });

    // ===== HELPERS =====
    function setSearchLoading(isLoading) {
        searchBtn.disabled = isLoading;
        const text = searchBtn.querySelector('.btn-text');
        if (isLoading) {
            text.style.display = 'none';
            searchLoader.style.display = 'block';
        } else {
            text.style.display = '';
            searchLoader.style.display = 'none';
        }
    }

    function showMessage(msg, type) {
        messageArea.className = 'message-area hidden';
        if (msg) {
            messageArea.textContent = msg;
            messageArea.classList.add(type);
            messageArea.classList.remove('hidden');
        }
    }

    function formatDuration(seconds) {
        if (!seconds) return '';
        if (typeof seconds === 'string' && seconds.includes(':')) return seconds;
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        return `${m}:${s.toString().padStart(2, '0')}`;
    }

    function formatDate(isoStr) {
        try {
            const d = new Date(isoStr);
            return d.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit', hour: '2-digit', minute: '2-digit' });
        } catch { return ''; }
    }

    function sleep(ms) {
        return new Promise(r => setTimeout(r, ms));
    }
});
