// ============================================================
//  DocExtractor — Client Application (app.js)
//  Clean Technical Developer Tool Architecture
// ============================================================

const API_BASE = '/api/v1';

const state = {
  token: localStorage.getItem('dqe_token') || '',
  user: null,
  activeDocumentId: null,
  activeDocument: null,
  documents: [],
  questions: [],
  reviewItems: [],
  pages: [],
  selectedFile: null,
  pollTimer: null,
};

// ── DOM references ────────────────────────────────────────────
const el = {
  globalLoader:    document.getElementById('global-loader'),
  loaderMsg:       document.getElementById('loader-msg'),

  systemStatus:    document.getElementById('system-status'),
  statusDot:       document.getElementById('status-dot'),
  statusLabel:     document.getElementById('status-label'),

  quickDemoBtn:    document.getElementById('quick-demo-btn'),
  userDisplay:     document.getElementById('user-display'),
  logoutBtn:       document.getElementById('logout-btn'),

  // Sidebar Nav
  navItems:        document.querySelectorAll('.nav-item'),
  navReviewCount:  document.getElementById('nav-review-count'),

  // Upload
  dropZone:        document.getElementById('drop-zone'),
  fileInput:       document.getElementById('file-input'),
  browseBtn:       document.getElementById('browse-btn'),
  selectedFileInfo:document.getElementById('selected-file-info'),
  previewFilename: document.getElementById('preview-filename'),
  previewFilesize: document.getElementById('preview-filesize'),
  clearFileBtn:    document.getElementById('clear-file-btn'),
  uploadBtn:       document.getElementById('upload-btn'),
  progressWrap:    document.getElementById('upload-progress-wrap'),
  progressFill:    document.getElementById('progress-fill'),
  progressStageLabel: document.getElementById('progress-stage-label'),
  progressPct:     document.getElementById('progress-pct'),

  // Document Queue
  docList:         document.getElementById('doc-list'),
  refreshDocsBtn:  document.getElementById('refresh-docs-btn'),

  // Metrics
  metricDocs:      document.getElementById('metric-docs'),
  metricQuestions: document.getElementById('metric-questions'),
  metricProcessing:document.getElementById('metric-processing'),
  metricReviews:   document.getElementById('metric-reviews'),

  // Overview
  activeDocTitle:  document.getElementById('active-doc-title'),
  activeDocStatusBadge: document.getElementById('active-doc-status-badge'),
  reprocessDocBtn: document.getElementById('reprocess-doc-btn'),
  activeDocId:     document.getElementById('active-doc-id'),
  activeDocType:   document.getElementById('active-doc-type'),
  activeDocPages:  document.getElementById('active-doc-pages'),
  activeDocConf:   document.getElementById('active-doc-conf'),


  // Tabs
  tabItems:        document.querySelectorAll('.tab-item'),
  tabPanes:        document.querySelectorAll('.tab-pane'),
  tabDocsCount:    document.getElementById('tab-docs-count'),
  tabQuestionsCount: document.getElementById('tab-questions-count'),
  tabReviewsCount: document.getElementById('tab-reviews-count'),
  tabPagesCount:   document.getElementById('tab-pages-count'),

  // Documents Table
  documentsTbody:  document.getElementById('documents-tbody'),

  // Content areas
  questionsContainer:   document.getElementById('questions-container'),
  reviewItemsContainer: document.getElementById('review-items-container'),
  pagesContainer:       document.getElementById('pages-container'),
  jsonCodeView:         document.getElementById('json-code-view'),
  copyJsonBtn:          document.getElementById('copy-json-btn'),

  // Filters
  typeFilter:      document.getElementById('type-filter'),
  statusFilter:    document.getElementById('status-filter'),
  questionSearch:  document.getElementById('question-search-input'),

  // Modal
  editModal:       document.getElementById('edit-modal'),
  editQuestionId:  document.getElementById('edit-question-id'),
  editQuestionText:document.getElementById('edit-question-text'),
  editQuestionType:document.getElementById('edit-question-type'),
  editQuestionAnswer: document.getElementById('edit-question-answer'),
  closeModalBtn:   document.getElementById('close-modal-btn'),
  cancelEditBtn:   document.getElementById('cancel-edit-btn'),
  saveEditBtn:     document.getElementById('save-edit-btn'),

  toast:           document.getElementById('toast'),
};

// ── Bootstrap ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', async () => {
  setupEventListeners();
  await checkBackendHealth();

  if (state.token) {
    await fetchUserProfile();
  } else {
    await handleDemoLogin();
  }
});

// ── Health Check ──────────────────────────────────────────────
async function checkBackendHealth() {
  setStatus('connecting');
  try {
    const res = await fetch('/health', { signal: AbortSignal.timeout(4000) });
    if (res.ok) {
      setStatus('ok');
    } else {
      setStatus('error');
    }
  } catch {
    setStatus('error');
  }
}

function setStatus(statusState) {
  el.systemStatus.classList.remove('error', 'connecting');
  if (statusState === 'ok') {
    el.statusLabel.textContent = 'Backend Connected';
  } else if (statusState === 'connecting') {
    el.statusLabel.textContent = 'Connecting...';
    el.systemStatus.classList.add('connecting');
  } else {
    el.statusLabel.textContent = 'Backend Offline';
    el.systemStatus.classList.add('error');
  }
}

// ── Event Listeners ───────────────────────────────────────────
function setupEventListeners() {
  el.quickDemoBtn.addEventListener('click', handleDemoLogin);
  el.logoutBtn.addEventListener('click', handleLogout);

  // File drag & drop
  el.dropZone.addEventListener('dragover', (e) => { e.preventDefault(); el.dropZone.classList.add('drag-over'); });
  el.dropZone.addEventListener('dragleave', () => el.dropZone.classList.remove('drag-over'));
  el.dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    el.dropZone.classList.remove('drag-over');
    if (e.dataTransfer.files?.[0]) handleFileSelected(e.dataTransfer.files[0]);
  });
  el.dropZone.addEventListener('click', () => el.fileInput.click());
  el.dropZone.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') el.fileInput.click(); });
  el.browseBtn.addEventListener('click', (e) => { e.stopPropagation(); el.fileInput.click(); });
  el.fileInput.addEventListener('change', (e) => { if (e.target.files?.[0]) handleFileSelected(e.target.files[0]); });
  el.clearFileBtn.addEventListener('click', clearSelectedFile);
  el.uploadBtn.addEventListener('click', uploadSelectedFile);
  el.refreshDocsBtn.addEventListener('click', () => loadUserDocuments());

  // Sidebar Nav items
  el.navItems.forEach(item => {
    item.addEventListener('click', () => {
      el.navItems.forEach(i => i.classList.remove('active'));
      item.classList.add('active');
      const targetNav = item.dataset.nav;
      if (targetNav === 'documents') switchTab('tab-documents');
      else if (targetNav === 'questions') switchTab('tab-questions');
      else if (targetNav === 'review') switchTab('tab-reviews');
      else if (targetNav === 'settings') switchTab('tab-settings');
    });
  });

  // Sample document buttons
  document.querySelectorAll('.sample-item').forEach(btn => {
    btn.addEventListener('click', () => uploadSampleDocument(btn.dataset.sample));
  });

  // Main Tabs
  el.tabItems.forEach(btn => {
    btn.addEventListener('click', () => {
      switchTab(btn.dataset.tab);
    });
  });

  if (el.reprocessDocBtn) {
    el.reprocessDocBtn.addEventListener('click', handleReprocessDocument);
  }

  // Filters & Search
  el.typeFilter.addEventListener('change', renderQuestions);
  el.statusFilter.addEventListener('change', renderQuestions);
  el.questionSearch.addEventListener('input', debounce(renderQuestions, 200));

  // JSON copy
  el.copyJsonBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(el.jsonCodeView.textContent).then(() => showToast('JSON copied to clipboard', 'success'));
  });

  // Modal
  el.closeModalBtn.addEventListener('click', closeModal);
  el.cancelEditBtn.addEventListener('click', closeModal);
  el.saveEditBtn.addEventListener('click', handleSaveQuestionEdit);
  el.editModal.addEventListener('click', (e) => { if (e.target === el.editModal) closeModal(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });
}

async function handleReprocessDocument() {
  if (!state.activeDocumentId) return;
  showToast('Re-triggering universal extraction pipeline...', 'info');
  try {
    if (el.reprocessDocBtn) el.reprocessDocBtn.disabled = true;
    await apiFetch(`/documents/${state.activeDocumentId}/reprocess`, 'POST');
    showToast('✓ Reprocessing started! Cleaning instruction noise...', 'success');
    await selectDocument(state.activeDocumentId);
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    if (el.reprocessDocBtn) el.reprocessDocBtn.disabled = false;
  }
}


function switchTab(tabId) {
  el.tabItems.forEach(b => b.classList.toggle('active', b.dataset.tab === tabId));
  el.tabPanes.forEach(p => p.classList.toggle('active', p.id === tabId));
}

// ── Authentication ────────────────────────────────────────────
async function handleDemoLogin() {
  showLoader('Authenticating demo account...');
  try {
    const demoEmail = 'evaluator@docextractor.ai';
    const demoPassword = 'DemoPass@2024!';

    await apiFetch('/auth/register', 'POST', {
      email: demoEmail, password: demoPassword, full_name: 'Evaluator Lead'
    }).catch(() => {});

    const data = await apiFetch('/auth/login', 'POST', { email: demoEmail, password: demoPassword });
    state.token = data.access_token;
    localStorage.setItem('dqe_token', state.token);
    await fetchUserProfile();
    showToast('Authenticated as Evaluator', 'success');
  } catch (err) {
    showToast(`Auth failed: ${err.message}`, 'error');
  } finally {
    hideLoader();
  }
}

async function fetchUserProfile() {
  try {
    const data = await apiFetch('/auth/me');
    state.user = data;
    el.userDisplay.textContent = data.email;
    el.userDisplay.classList.remove('hidden');
    el.logoutBtn.classList.remove('hidden');
    el.quickDemoBtn.classList.add('hidden');
    await loadUserDocuments();
  } catch {
    handleLogout();
  }
}

function handleLogout() {
  state.token = '';
  state.user = null;
  localStorage.removeItem('dqe_token');
  el.userDisplay.classList.add('hidden');
  el.logoutBtn.classList.add('hidden');
  el.quickDemoBtn.classList.remove('hidden');
}

// ── File Handling ─────────────────────────────────────────────
function handleFileSelected(file) {
  const maxSize = 20 * 1024 * 1024;
  if (file.size > maxSize) { showToast('File exceeds 20 MB limit', 'error'); return; }
  const allowed = ['application/pdf', 'image/jpeg', 'image/png'];
  if (!allowed.includes(file.type) && !file.name.match(/\.(pdf|jpg|jpeg|png)$/i)) {
    showToast('Only PDF, JPG and PNG files are supported', 'error');
    return;
  }
  state.selectedFile = file;
  el.previewFilename.textContent = file.name;
  el.previewFilesize.textContent = formatFileSize(file.size);
  el.selectedFileInfo.classList.remove('hidden');
}

function clearSelectedFile() {
  state.selectedFile = null;
  el.fileInput.value = '';
  el.selectedFileInfo.classList.add('hidden');
  el.progressWrap.classList.add('hidden');
}

async function uploadSelectedFile() {
  if (!state.selectedFile) return;
  if (!state.token) { showToast('Please login first', 'error'); return; }

  const formData = new FormData();
  formData.append('file', state.selectedFile);

  el.uploadBtn.disabled = true;
  el.uploadBtn.textContent = 'Uploading...';
  showProgress('Uploading file...', 20);

  try {
    const resp = await fetch(`${API_BASE}/documents`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${state.token}` },
      body: formData,
    });
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.error?.message || `Upload failed (${resp.status})`);
    }
    showProgress('Queued for processing...', 80);
    const data = await resp.json();
    showProgress('Queued!', 100);

    await sleep(400);
    hideProgress();
    clearSelectedFile();
    showToast(`✓ "${data.filename}" queued`, 'success');
    await loadUserDocuments();
    selectDocument(data.document_id || data.id);
  } catch (err) {
    hideProgress();
    showToast(err.message, 'error');
  } finally {
    el.uploadBtn.disabled = false;
    el.uploadBtn.textContent = 'Process Document';
  }
}

async function uploadSampleDocument(sampleName) {
  if (!state.token) { showToast('Please login first', 'error'); return; }
  showToast(`Loading sample: ${sampleName}...`);

  try {
    const mimeType = sampleName.endsWith('.pdf') ? 'application/pdf' : 'image/png';
    let blob;
    const sampleResp = await fetch(`/samples/${sampleName}`).catch(() => null);
    if (sampleResp?.ok) {
      blob = await sampleResp.blob();
    } else {
      blob = new Blob([generateSampleContent(sampleName)], { type: mimeType });
    }

    const formData = new FormData();
    formData.append('file', blob, sampleName);

    const resp = await fetch(`${API_BASE}/documents`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${state.token}` },
      body: formData,
    });
    if (!resp.ok) throw new Error('Failed to upload sample document');
    const data = await resp.json();
    showToast(`✓ Sample "${sampleName}" queued`, 'success');
    await loadUserDocuments();
    selectDocument(data.document_id || data.id);
  } catch (err) {
    showToast(`Sample: ${err.message}`, 'error');
  }
}

function generateSampleContent(name) {
  return `%PDF-1.4 SAMPLE — ${name}\n\nQ1. What is the capital of France?\n(A) Berlin  (B) Paris  (C) Rome  (D) Madrid\n\nAnswer Key: Q1 → B\n`;
}

// ── Documents Queue & Table ───────────────────────────────────
async function loadUserDocuments() {
  if (!state.token) return;
  try {
    const data = await apiFetch('/documents');
    const items = data.items || [];
    state.documents = items;

    el.tabDocsCount.textContent = items.length;
    el.metricDocs.textContent = items.length;

    const processingCount = items.filter(d => ['QUEUED', 'PROCESSING', 'OCR_PROCESSING', 'QUESTION_EXTRACTION', 'ANSWER_MATCHING', 'VALIDATION'].includes(d.processing_status)).length;
    el.metricProcessing.textContent = processingCount;

    // Render sidebar queue
    if (items.length === 0) {
      el.docList.innerHTML = `<div class="empty-state-mini">No documents uploaded yet</div>`;
      el.documentsTbody.innerHTML = `<tr><td colspan="8" class="text-center muted-text">No documents available</td></tr>`;
      return;
    }

    el.docList.innerHTML = items.map(doc => `
      <div class="doc-item ${doc.id === state.activeDocumentId ? 'active' : ''}"
           onclick="selectDocument('${doc.id}')" role="button" tabindex="0">
        <div class="doc-item-left">
          <div class="doc-item-title" title="${escHtml(doc.filename)}">${escHtml(doc.filename)}</div>
          <div class="doc-item-meta">${timeAgo(doc.created_at)} • ${formatFileSize(doc.file_size_bytes)}</div>
        </div>
        <span class="status-badge ${doc.processing_status}">${doc.processing_status}</span>
      </div>
    `).join('');

    // Render Documents Table
    el.documentsTbody.innerHTML = items.map(doc => `
      <tr class="${doc.id === state.activeDocumentId ? 'active-row' : ''}">
        <td><strong>${escHtml(doc.filename)}</strong></td>
        <td><span class="code-text">${doc.mime_type?.includes('pdf') ? 'PDF' : 'IMAGE'}</span></td>
        <td>${doc.page_count ?? '—'}</td>
        <td><span class="status-badge ${doc.processing_status}">${doc.processing_status}</span></td>
        <td>${doc.questions_count ?? 0}</td>
        <td>${doc.review_items_count > 0 ? `<span class="status-badge PARTIAL">${doc.review_items_count} flags</span>` : '0'}</td>
        <td>${timeAgo(doc.created_at)}</td>
        <td class="text-right">
          <button class="btn btn-secondary btn-xs" onclick="selectDocument('${doc.id}')">Select</button>
        </td>
      </tr>
    `).join('');

    if (!state.activeDocumentId && items.length > 0) selectDocument(items[0].id);
  } catch (err) {
    console.error('loadUserDocuments:', err);
  }
}

window.selectDocument = async function(documentId) {
  if (!documentId) return;
  state.activeDocumentId = documentId;
  document.querySelectorAll('.doc-item').forEach(item => {
    item.classList.toggle('active', item.getAttribute('onclick')?.includes(documentId));
  });

  clearInterval(state.pollTimer);
  await fetchDocumentDetails(documentId);

  const s = state.activeDocument?.processing_status;
  if (s && ['QUEUED', 'PROCESSING', 'UPLOADED', 'OCR_PROCESSING', 'QUESTION_EXTRACTION', 'ANSWER_MATCHING', 'VALIDATION'].includes(s)) {
    state.pollTimer = setInterval(async () => {
      await fetchDocumentDetails(documentId);
      const newStatus = state.activeDocument?.processing_status;
      if (['COMPLETED', 'PARTIAL', 'FAILED'].includes(newStatus)) {
        clearInterval(state.pollTimer);
        await loadUserDocuments();
        if (newStatus === 'COMPLETED') showToast('✓ Extraction completed', 'success');
        else if (newStatus === 'FAILED') showToast('⚠ Processing failed', 'error');
      }
    }, 1800);
  }
};

async function fetchDocumentDetails(documentId) {
  try {
    const doc = await apiFetch(`/documents/${documentId}`);
    state.activeDocument = doc;

    el.activeDocType.textContent = doc.mime_type?.includes('pdf') ? 'PDF' : 'IMAGE';
    el.activeDocTitle.textContent = doc.filename;
    el.activeDocStatusBadge.textContent = doc.processing_status;
    el.activeDocStatusBadge.className = `status-badge ${doc.processing_status}`;
    el.activeDocId.textContent = `UUID: ${doc.id}`;
    el.activeDocPages.textContent = `${doc.page_count ?? 0} Pages`;
    el.metricQuestions.textContent = doc.questions_count ?? 0;
    el.metricReviews.textContent = doc.review_items_count ?? 0;
    if (el.navReviewCount) el.navReviewCount.textContent = doc.review_items_count ?? 0;
    if (el.reprocessDocBtn) el.reprocessDocBtn.classList.remove('hidden');

    const overallConf = doc.overall_confidence != null ? `${Math.round(doc.overall_confidence * 100)}%` : '--';
    el.activeDocConf.textContent = `Avg Conf: ${overallConf}`;

    updateStepper(doc.processing_stage, doc.processing_status);

    if (['COMPLETED', 'PARTIAL', 'VALIDATION', 'ANSWER_MATCHING', 'QUESTION_EXTRACTION'].includes(doc.processing_status)) {
      await Promise.all([fetchQuestions(documentId), fetchReviewItems(documentId), fetchPages(documentId)]);
    }
  } catch (err) {
    console.error('fetchDocumentDetails:', err);
  }
}


function updateStepper(stage, status) {
  const stages = ['UPLOADED', 'OCR_PROCESSING', 'QUESTION_EXTRACTION', 'ANSWER_MATCHING', 'VALIDATION', 'COMPLETED'];
  const currentIdx = stages.indexOf(stage ?? '');
  const isComplete = status === 'COMPLETED';

  document.querySelectorAll('.step-item').forEach(step => {
    const idx = stages.indexOf(step.dataset.stage);
    step.classList.remove('active', 'done');
    if (isComplete || idx < currentIdx) step.classList.add('done');
    else if (idx === currentIdx) step.classList.add('active');
  });
}

// ── Questions List ────────────────────────────────────────────
async function fetchQuestions(documentId) {
  try {
    const data = await apiFetch(`/documents/${documentId}/questions`);
    state.questions = data.items || [];
    el.tabQuestionsCount.textContent = data.total || state.questions.length;
    renderQuestions();
    updateJsonView();
  } catch (err) { console.error('fetchQuestions:', err); }
}

function renderQuestions() {
  const typeVal   = el.typeFilter.value;
  const statusVal = el.statusFilter.value;
  const searchVal = el.questionSearch.value.toLowerCase().trim();

  const filtered = state.questions.filter(q => {
    if (typeVal   && q.question_type    !== typeVal)   return false;
    if (statusVal && q.extraction_status !== statusVal) return false;
    if (searchVal) {
      const haystack = (q.question_text + ' ' + (q.options?.map(o => o.option_text).join(' ') ?? '')).toLowerCase();
      if (!haystack.includes(searchVal)) return false;
    }
    return true;
  });

  if (filtered.length === 0) {
    el.questionsContainer.innerHTML = `<div class="empty-state">${state.questions.length > 0 ? 'No matching questions found.' : 'No questions extracted yet.'}</div>`;
    return;
  }

  el.questionsContainer.innerHTML = filtered.map(q => {
    const conf = q.confidence_score ?? 0;
    const confPct = Math.round(conf * 100);
    const confBadgeClass = conf >= 0.85 ? 'COMPLETED' : conf >= 0.60 ? 'PARTIAL' : 'FAILED';
    const pages = Array.isArray(q.source_pages) ? q.source_pages : [];
    const opts  = Array.isArray(q.options) ? q.options : [];

    return `
    <div class="q-item-card" id="qc-${q.id}">
      <div class="q-card-header">
        <div class="q-meta-left">
          <span class="q-num-pill">${q.question_number ? `Q${q.question_number}` : 'Q?'}</span>
          <span class="q-type-pill">${q.question_type ?? 'UNKNOWN'}</span>
          ${pages.length ? pages.map(p => `<span class="page-chip">Page ${p}</span>`).join(' ') : ''}
        </div>
        <div class="q-actions">
          <span class="status-badge ${confBadgeClass}">${confPct}% Conf</span>
          <button class="btn btn-secondary btn-xs" onclick="openEditModal('${q.id}')">Edit</button>
        </div>
      </div>
      <div class="q-body">${escHtml(q.question_text || '(no text extracted)')}</div>
      ${q.image_url ? `<div class="q-image-container"><img src="${escHtml(q.image_url)}" class="q-image-preview" alt="Question Diagram / Page Preview" onclick="window.open('${escHtml(q.image_url)}', '_blank')"></div>` : ''}
      ${opts.length ? `
        <div class="options-grid">

          ${opts.map(o => `
            <div class="opt-box ${o.is_correct ? 'correct' : ''}">
              <span class="opt-key-tag">${escHtml(o.option_key)}</span>
              <span>${escHtml(o.option_text)}</span>
            </div>`).join('')}
        </div>` : ''}
      <div class="q-card-footer">
        <span>Answer: <strong>${escHtml(q.matched_answer || '—')}</strong> ${q.answer_source ? `(${escHtml(q.answer_source)})` : ''}</span>
        <span>Status: <strong class="code-text">${escHtml(q.extraction_status || '—')}</strong></span>
      </div>
    </div>`;
  }).join('');
}

// ── Review Items ──────────────────────────────────────────────
async function fetchReviewItems(documentId) {
  try {
    const data = await apiFetch(`/documents/${documentId}/review-items`);
    state.reviewItems = data.items || [];
    el.tabReviewsCount.textContent = data.total || state.reviewItems.length;

    if (state.reviewItems.length === 0) {
      el.reviewItemsContainer.innerHTML = `<div class="empty-state">✓ No quality warnings or flags for this document.</div>`;
      return;
    }

    el.reviewItemsContainer.innerHTML = state.reviewItems.map(item => `
      <div class="review-item-row ${item.severity}">
        <div class="review-info">
          <span class="review-title">${escHtml(item.review_type)} (${item.severity})</span>
          <span class="review-msg">${escHtml(item.message)}</span>
        </div>
        <div>
          ${item.is_resolved
            ? '<span class="status-badge COMPLETED">Resolved</span>'
            : `<button class="btn btn-secondary btn-xs" onclick="resolveReviewItem('${item.id}')">Resolve</button>`}
        </div>
      </div>`).join('');
  } catch (err) { console.error('fetchReviewItems:', err); }
}

window.resolveReviewItem = async function(itemId) {
  try {
    await apiFetch(`/review-items/${itemId}/resolve`, 'PATCH');
    showToast('Review item resolved', 'success');
    await fetchReviewItems(state.activeDocumentId);
  } catch (err) { showToast(err.message, 'error'); }
};

// ── Normalized Pages ──────────────────────────────────────────
async function fetchPages(documentId) {
  try {
    const pages = await apiFetch(`/documents/${documentId}/pages`);
    state.pages = Array.isArray(pages) ? pages : (pages.items || []);
    el.tabPagesCount.textContent = state.pages.length;

    if (state.pages.length === 0) {
      el.pagesContainer.innerHTML = `<div class="empty-state">No page text extracted yet.</div>`;
      return;
    }

    el.pagesContainer.innerHTML = state.pages.map(p => `
      <div class="page-block">
        <div class="q-card-header">
          <span class="q-num-pill">Page ${p.page_number}</span>
          <span class="code-text">${p.ocr_used ? 'OCR Engine' : 'Digital PDF'} ${p.ocr_confidence != null ? `(Conf: ${p.ocr_confidence}%)` : ''}</span>
        </div>
        <pre><code>${escHtml(p.extracted_text || '(no text extracted)')}</code></pre>
      </div>`).join('');
  } catch (err) { console.error('fetchPages:', err); }
}

// ── JSON View ─────────────────────────────────────────────────
function updateJsonView() {
  const payload = {
    document_id: state.activeDocument?.id,
    filename: state.activeDocument?.filename,
    status: state.activeDocument?.processing_status,
    questions_count: state.questions.length,
    overall_confidence: state.activeDocument?.overall_confidence,
    questions: state.questions,
  };
  el.jsonCodeView.textContent = JSON.stringify(payload, null, 2);
}

// ── Edit Modal ────────────────────────────────────────────────
window.openEditModal = function(questionId) {
  const q = state.questions.find(item => item.id === questionId);
  if (!q) return;
  el.editQuestionId.value = q.id;
  el.editQuestionText.value = q.question_text || '';
  el.editQuestionType.value = q.question_type || 'MCQ';
  el.editQuestionAnswer.value = q.matched_answer || '';
  el.editModal.classList.remove('hidden');
  setTimeout(() => el.editQuestionText.focus(), 50);
};

function closeModal() { el.editModal.classList.add('hidden'); }

async function handleSaveQuestionEdit() {
  const qId    = el.editQuestionId.value;
  const body   = {
    question_text:  el.editQuestionText.value.trim(),
    question_type:  el.editQuestionType.value,
    matched_answer: el.editQuestionAnswer.value.trim() || null,
  };
  if (!body.question_text) { showToast('Question text cannot be empty', 'error'); return; }

  try {
    el.saveEditBtn.disabled = true;
    el.saveEditBtn.textContent = 'Saving...';
    await apiFetch(`/questions/${qId}`, 'PATCH', body);
    showToast('Question updated', 'success');
    closeModal();
    await fetchQuestions(state.activeDocumentId);
  } catch (err) {
    showToast(err.message, 'error');
  } finally {
    el.saveEditBtn.disabled = false;
    el.saveEditBtn.textContent = 'Save Changes';
  }
}

// ── API Helper ────────────────────────────────────────────────
async function apiFetch(path, method = 'GET', body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (state.token) opts.headers['Authorization'] = `Bearer ${state.token}`;
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.error?.message || err.detail || `Request failed (${res.status})`);
  }
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('application/json')) return res.json();
  return {};
}

// ── UI Utilities ──────────────────────────────────────────────
let _toastTimer;
function showToast(message, type = 'info') {
  clearTimeout(_toastTimer);
  el.toast.textContent = message;
  el.toast.className = `toast ${type}`;
  el.toast.classList.remove('hidden');
  _toastTimer = setTimeout(() => el.toast.classList.add('hidden'), 3500);
}

function showLoader(msg = 'Loading...') {
  el.loaderMsg.textContent = msg;
  el.globalLoader.classList.remove('hidden');
}
function hideLoader() { el.globalLoader.classList.add('hidden'); }

function showProgress(label, pct) {
  el.progressWrap.classList.remove('hidden');
  el.progressStageLabel.textContent = label;
  el.progressPct.textContent = `${pct}%`;
  el.progressFill.style.width = `${pct}%`;
}
function hideProgress() {
  setTimeout(() => {
    el.progressWrap.classList.add('hidden');
    el.progressFill.style.width = '0%';
  }, 400);
}

function escHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;')
    .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function formatFileSize(bytes) {
  if (!bytes) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
}

function timeAgo(isoStr) {
  if (!isoStr) return '';
  const diff = (Date.now() - new Date(isoStr).getTime()) / 1000;
  if (diff < 60) return 'just now';
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return new Date(isoStr).toLocaleDateString();
}

function debounce(fn, ms) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
