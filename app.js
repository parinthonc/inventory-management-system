// ─── Theme Management (Light/Dark) ────────────────────────────────────────
// Applied immediately to avoid flash of wrong theme on page load.
(function initTheme() {
    const saved = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', saved);
    // After DOM is ready, sync the toggle icon
    document.addEventListener('DOMContentLoaded', () => {
        const sunIcon = document.getElementById('theme-icon-sun');
        const moonIcon = document.getElementById('theme-icon-moon');
        const toggleBtn = document.getElementById('theme-toggle-btn');
        if (!sunIcon || !moonIcon || !toggleBtn) return;

        function syncIcons(theme) {
            if (theme === 'light') {
                sunIcon.classList.add('hidden');
                moonIcon.classList.remove('hidden');
            } else {
                sunIcon.classList.remove('hidden');
                moonIcon.classList.add('hidden');
            }
        }
        syncIcons(saved);

        toggleBtn.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme') || 'light';
            const next = current === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', next);
            localStorage.setItem('theme', next);
            syncIcons(next);
        });
    });
})();

// ─── Theme-aware Color Helper ─────────────────────────────────────────────
// Returns colours appropriate for the current theme.  Used by Chart.js and
// any JS-generated inline styles that can't rely on CSS variables alone.
function getThemeColors() {
    const isLight = document.documentElement.getAttribute('data-theme') === 'light';
    return {
        tickColor:  isLight ? 'rgba(0, 0, 0, 0.55)'   : 'rgba(255, 255, 255, 0.5)',
        gridColor:  isLight ? 'rgba(0, 0, 0, 0.06)'   : 'rgba(255, 255, 255, 0.05)',
        locBadgeBg: isLight ? 'rgba(109, 40, 217, 0.1)' : 'rgba(139, 92, 246, 0.2)',
        locBadgeColor: isLight ? '#6d28d9' : '#c4b5fd',
    };
}

// Category name mapping: English -> Thai
const CATEGORY_NAME_TH = {
    'Domestic Purchase': 'ซื้อในประเทศ',
    'Overseas Purchase': 'ซื้อต่างประเทศ',
    'Customer Return': 'รับคืนจากลูกค้า',
    'Other In': 'รับอื่นๆ',
    'Adjustment In': 'ปรับปรุงเข้า',
    'Transfer In': 'ย้ายเข้า',
    'AF': 'AF',
    'SF': 'SF',
    'Sale': 'ขาย',
    'Return to Manufacturer': 'คืนผู้ผลิต',
    'Other Out': 'จ่ายอื่นๆ',
    'Adjustment Out': 'ปรับปรุงออก',
    'Transfer Out': 'ย้ายออก',
    'Other': 'อื่นๆ',
    'Opening Balance': 'ยอดยกมา',
};

function getCategoryThai(englishName) {
    return CATEGORY_NAME_TH[englishName] || englishName || '-';
}

// State management
let state = {
    products: [],
    totalItems: 0,
    page: 1,
    perPage: 50,
    totalPages: 0,
    search: '',
    brand: '',
    suffix: '',
    activeDays: '', // new filter
    sort: 'part_code',
    sortDir: 'asc',
    brands: [],
    suffixes: [],

    // Moves State
    moves: [],
    movesTotalItems: 0,
    movesPage: 1,
    movesPerPage: 50,
    movesTotalPages: 0,
    movesSearch: '',
    movesType: 'all', // 'all', 'in', 'out'
    movesSort: '',
    movesSortDir: '',

    // Flags State
    flags: [],
    flagsSearch: '',
    flagsPage: 1,
    flagsPerPage: 50,
    flagsTotalItems: 0,
    flagsTotalPages: 0,
    flagsSort: '',
    flagsSortDir: '',

    // Photo Flags State
    photoFlags: [],
    photoFlagsSearch: '',
    photoFlagsPage: 1,
    photoFlagsPerPage: 50,
    photoFlagsTotalItems: 0,
    photoFlagsTotalPages: 0,
    photoFlagsSort: '',
    photoFlagsSortDir: '',

    // Pickup Mode State
    pickupMode: false,
    pickupData: null,

    // Customer Activity State
    customerActivity: [],
    customerSearch: '',
    customers: [],
    customersPage: 1,
    customersPerPage: 50,
    customersTotalItems: 0,
    customersTotalPages: 0,
    customerDetailCode: null,  // when set, we're in detail mode

    // Invoice State
    invoices: [],
    invoicesSearch: '',
    invoicesDocType: '',
    invoicesPage: 1,
    invoicesPerPage: 50,
    invoicesTotalItems: 0,
    invoicesTotalPages: 0,
    invoicesSort: 'invoice_date',
    invoicesSortDir: 'desc',
    invoiceDetailNumber: null,  // when set, we're in detail mode

    // Modal navigation
    modalList: [],
    modalIndex: -1,

    currentTab: 'products', // 'products', 'moves', 'flags', 'photo-flags', 'customer', 'invoice'

    // Sync change highlighting — sets of keys for newly detected items
    syncNewProductSkus: new Set(),
    syncNewMoveKeys: new Set(),
    syncDetectionTimes: new Map(),   // sku -> time string (for today's sales)
};

// DOM Elements
const els = {
    // Tabs Navigation
    tabBtnProducts: document.getElementById('tab-btn-products'),
    tabBtnMoves: document.getElementById('tab-btn-moves'),
    tabBtnFlags: document.getElementById('tab-btn-flags'),
    tabBtnCustomer: document.getElementById('tab-btn-customer'),
    tabBtnPhotoFlags: document.getElementById('tab-btn-photo-flags'),

    // Views
    viewProducts: document.getElementById('view-products'),
    viewMoves: document.getElementById('view-moves'),
    viewFlags: document.getElementById('view-flags'),
    viewPhotoFlags: document.getElementById('view-photo-flags'),
    viewCustomer: document.getElementById('view-customer'),

    // Stats
    totalSkus: document.getElementById('total-skus'),

    // Controls - Products
    searchInput: document.getElementById('search-input'),
    brandFilter: document.getElementById('brand-filter'),
    suffixFilter: document.getElementById('suffix-filter'),
    activeFilter: document.getElementById('active-filter'), // New
    sortFilter: document.getElementById('sort-filter'),
    sortDirBtn: document.getElementById('sort-dir-btn'),
    sortIconAsc: document.getElementById('sort-icon-asc'),
    sortIconDesc: document.getElementById('sort-icon-desc'),
    thumbSizeSlider: document.getElementById('thumb-size-slider'),

    // Table - Products
    productList: document.getElementById('product-list'),
    resultsCount: document.getElementById('results-count'),
    colAmountSold: document.getElementById('col-amount-sold'), // New

    // Pagination - Products
    pageStart: document.getElementById('page-start'),
    pageEnd: document.getElementById('page-end'),
    totalResults: document.getElementById('total-results'),
    btnPrev: document.getElementById('btn-prev'),
    btnNext: document.getElementById('btn-next'),
    pageNumbers: document.getElementById('page-numbers'),

    // Controls - Moves
    movesSearchInput: document.getElementById('moves-search-input'),
    movesTypeFilter: document.getElementById('moves-type-filter'),

    // Table - Moves
    movesList: document.getElementById('moves-list'),
    movesResultsCount: document.getElementById('moves-results-count'),

    // Pagination - Moves
    movesPageStart: document.getElementById('moves-page-start'),
    movesPageEnd: document.getElementById('moves-page-end'),
    movesTotalResults: document.getElementById('moves-total-results'),
    movesBtnPrev: document.getElementById('moves-btn-prev'),
    movesBtnNext: document.getElementById('moves-btn-next'),
    movesPageNumbers: document.getElementById('moves-page-numbers'),

    // Controls - Flags
    flagsSearchInput: document.getElementById('flags-search-input'),

    // Table - Flags
    flagsList: document.getElementById('flags-list'),
    flagsResultsCount: document.getElementById('flags-results-count'),

    // Pagination - Flags
    flagsPageStart: document.getElementById('flags-page-start'),
    flagsPageEnd: document.getElementById('flags-page-end'),
    flagsTotalResults: document.getElementById('flags-total-results'),
    flagsBtnPrev: document.getElementById('flags-btn-prev'),
    flagsBtnNext: document.getElementById('flags-btn-next'),
    flagsPageNumbers: document.getElementById('flags-page-numbers'),

    // Photo Flags Tab
    photoFlagsSearchInput: document.getElementById('photo-flags-search-input'),
    photoFlagsList: document.getElementById('photo-flags-list'),
    photoFlagsResultsCount: document.getElementById('photo-flags-results-count'),
    photoFlagsPageStart: document.getElementById('photo-flags-page-start'),
    photoFlagsPageEnd: document.getElementById('photo-flags-page-end'),
    photoFlagsTotalResults: document.getElementById('photo-flags-total-results'),
    photoFlagsBtnPrev: document.getElementById('photo-flags-btn-prev'),
    photoFlagsBtnNext: document.getElementById('photo-flags-btn-next'),
    photoFlagsPageNumbers: document.getElementById('photo-flags-page-numbers'),

    // Customer Activity
    customerSearchInput: document.getElementById('customer-search-input'),
    customerResultsCount: document.getElementById('customer-results-count'),
    customerList: document.getElementById('customer-list'),
    customerListPanel: document.getElementById('customer-list-panel'),
    customerDetailPanel: document.getElementById('customer-detail-panel'),
    customerInfoCard: document.getElementById('customer-info-card'),
    custDetailTxnCount: document.getElementById('cust-detail-txn-count'),
    custDetailTxnList: document.getElementById('cust-detail-txn-list'),
    custBackBtn: document.getElementById('cust-back-btn'),
    // Customer list pagination
    custPageStart: document.getElementById('cust-page-start'),
    custPageEnd: document.getElementById('cust-page-end'),
    custTotalResults: document.getElementById('cust-total-results'),
    custBtnPrev: document.getElementById('cust-btn-prev'),
    custBtnNext: document.getElementById('cust-btn-next'),
    custPageNumbers: document.getElementById('cust-page-numbers'),
    // Refresh Customer
    refreshCustomerBtn: document.getElementById('refresh-customer-btn'),
    customerModDate: document.getElementById('customer-mod-date'),

    // Modal
    modal: document.getElementById('product-modal'),
    closeModal: document.getElementById('close-modal'),
    modalMainImg: document.getElementById('modal-main-image'),
    mainImageTrashBtn: document.getElementById('main-image-trash-btn'),
    modalThumbnails: document.getElementById('modal-thumbnails'),
    modalSuffixLabel: document.getElementById('modal-suffix-label'),
    modalPartCode: document.getElementById('modal-part-code'),
    modalNameEng: document.getElementById('modal-name-eng'),
    modalNameThai: document.getElementById('modal-name-thai'),
    modalBrand: document.getElementById('modal-brand'),
    modalSize: document.getElementById('modal-size'),
    modalQty: document.getElementById('modal-qty'),
    modalPrice: document.getElementById('modal-price'),
    modalLocation: document.getElementById('modal-location'),
    modalHistory: document.getElementById('modal-history'),
    modalArchivedHistory: document.getElementById('modal-archived-history'),
    modalPossibleTitles: document.getElementById('modal-possible-titles'),

    // Modal Flagging Elements
    btnReportIssue: document.getElementById('btn-report-issue'),
    reportDialog: document.getElementById('report-dialog'),
    btnCancelReport: document.getElementById('btn-cancel-report'),
    btnSubmitReport: document.getElementById('btn-submit-report'),
    reportNote: document.getElementById('report-note'),
    flagTypeRadios: document.getElementsByName('flag_type'),

    // Modal Photo Flag Elements
    btnPhotoFlag: document.getElementById('btn-photo-flag'),
    photoFlagDialog: document.getElementById('photo-flag-dialog'),
    photoFlagNote: document.getElementById('photo-flag-note'),
    btnCancelPhotoFlag: document.getElementById('btn-cancel-photo-flag'),
    btnSubmitPhotoFlag: document.getElementById('btn-submit-photo-flag'),

    // Refresh Master
    refreshMasterBtn: document.getElementById('refresh-master-btn'),
    masterModDate: document.getElementById('master-mod-date'),
    refreshLedgerBtn: document.getElementById('refresh-ledger-btn'),
    ledgerModDate: document.getElementById('ledger-mod-date'),

    // Modal Navigation
    modalPrevBtn: document.getElementById('modal-prev-btn'),
    modalNextBtn: document.getElementById('modal-next-btn'),
    modalNavIndicator: document.getElementById('modal-nav-indicator'),
    modalNavControls: document.getElementById('modal-nav-controls'),

    // Charts
    archivedHistoryChart: document.getElementById('archived-history-chart'),

    // Sales by Year
    modalSalesByYear: document.getElementById('modal-sales-by-year'),
    salesByYearGrid: document.getElementById('sales-by-year-grid'),

    // Invoice Tab
    tabBtnInvoice: document.getElementById('tab-btn-invoice'),
    viewInvoice: document.getElementById('view-invoice'),
    invoiceSearchInput: document.getElementById('invoice-search-input'),
    invoiceDocTypeFilter: document.getElementById('invoice-doctype-filter'),
    invoiceList: document.getElementById('invoice-list'),
    invoiceResultsCount: document.getElementById('invoice-results-count'),
    invPageStart: document.getElementById('inv-page-start'),
    invPageEnd: document.getElementById('inv-page-end'),
    invTotalResults: document.getElementById('inv-total-results'),
    invBtnPrev: document.getElementById('inv-btn-prev'),
    invBtnNext: document.getElementById('inv-btn-next'),
    invPageNumbers: document.getElementById('inv-page-numbers'),
    invoiceListPanel: document.getElementById('invoice-list-panel'),
    invoiceDetailPanel: document.getElementById('invoice-detail-panel'),
    invBackBtn: document.getElementById('inv-back-btn'),
    invoiceInfoCard: document.getElementById('invoice-info-card'),
    invDetailItemCount: document.getElementById('inv-detail-item-count'),
    invDetailItemsList: document.getElementById('inv-detail-items-list'),
    refreshInvoiceBtn: document.getElementById('refresh-invoice-btn'),
    invoiceModDate: document.getElementById('invoice-mod-date'),

};

// Global chart instances
let archivedChartInstance = null;

// Format utilities
const formatNumber = (num) => new Intl.NumberFormat('en-US').format(num);
const formatPrice = (num) => new Intl.NumberFormat('th-TH', { style: 'currency', currency: 'THB' }).format(num);

// Date formatting to Buddhist Era (BE)
function formatBuddhistDate(dateStr, includeTime = false) {
    if (!dateStr || dateStr === '-') return '-';

    // Handle YYYY-MM-DD
    if (typeof dateStr === 'string' && dateStr.includes('-') && dateStr.length <= 10) {
        let parts = dateStr.split('-');
        if (parts.length === 3) {
            const year = parseInt(parts[0], 10);
            // Handle if it's already BE (e.g., > 2500)
            const beYear = year > 2500 ? year : year + 543;
            return `${parts[2]}/${parts[1]}/${beYear}`;
        }
    }

    // Handle full Date objects, ISO strings, etc.
    const d = new Date(dateStr);
    if (!isNaN(d.getTime())) {
        const y = d.getFullYear();
        const beYear = y > 2500 ? y : y + 543;
        const m = String(d.getMonth() + 1).padStart(2, '0');
        const day = String(d.getDate()).padStart(2, '0');

        let result = `${day}/${m}/${beYear}`;

        if (includeTime) {
            const h = String(d.getHours()).padStart(2, '0');
            const min = String(d.getMinutes()).padStart(2, '0');
            result += ` ${h}:${min}`;
        }
        return result;
    }

    return dateStr;
}

// ─── History / Hash-based Navigation ──────────────────────────────────────
// We push history entries so the browser back/forward buttons work intuitively.
// Hash format:  #products | #moves | #flags | #customer | #invoice
//               #product/<sku>
//               #customer/<code>
//               #invoice/<number>

/** Push a new history entry (unless we're already at that hash). */
function navPush(hash) {
    if (location.hash === '#' + hash || location.hash === hash) return;
    history.pushState({ nav: hash }, '', '#' + hash);
}

/** Replace the current history entry without creating a new one. */
function navReplace(hash) {
    history.replaceState({ nav: hash }, '', '#' + hash);
}

/** True while we are programmatically handling a popstate to avoid re-entrant pushes. */
let _handlingPopstate = false;

/**
 * Central router – called both on popstate AND on initial load.
 * Reads `location.hash` and shows the correct view.
 */
function handleNavigation() {
    const hash = location.hash.replace(/^#/, '') || 'products';

    // ── Product modal: #product/<sku> ────────────────────────
    if (hash.startsWith('product/')) {
        const sku = decodeURIComponent(hash.slice('product/'.length));
        // If the modal is already showing this product, nothing to do
        if (!els.modal.classList.contains('hidden') && state.currentModalSku === sku) return;
        // Find the product in the current list and open it
        const idx = state.modalList?.findIndex(p => p.sku === sku) ?? -1;
        if (idx >= 0) {
            // Product is in the current list – use it directly
            openModalInternal(state.modalList[idx]);
            state.modalIndex = idx;
            updateModalNav();
        } else {
            // Product not in modalList (e.g. page was refreshed) – fetch from server
            fetchProductDetail(sku).then(product => {
                if (product) {
                    openModalInternal(product);
                } else {
                    // Fallback: open with minimal data (better than nothing)
                    openModalInternal({ sku });
                }
            });
        }
        return;
    }

    // ── If the product modal is open but we navigated away, close it ──
    if (!els.modal.classList.contains('hidden')) {
        closeModalInternal();
    }

    // ── Customer detail: #customer/<code> ────────────────────
    if (hash.startsWith('customer/')) {
        const code = decodeURIComponent(hash.slice('customer/'.length));
        switchTabInternal('customer');
        openCustomerDetailInternal(code);
        return;
    }

    // ── Invoice detail: #invoice/<number> ────────────────────
    if (hash.startsWith('invoice/')) {
        const num = decodeURIComponent(hash.slice('invoice/'.length));
        switchTabInternal('invoice');
        openInvoiceDetail(num);
        return;
    }

    // ── Plain tab: #products | #moves | #flags | #photo-flags | #customer | #invoice ──
    const tabName = hash || 'products';
    const validTabs = ['products', 'moves', 'flags', 'photo-flags', 'customer', 'invoice'];
    if (validTabs.includes(tabName)) {
        // If we're going back to #customer from customer detail, show list
        if (tabName === 'customer' && state.customerDetailCode) {
            state.customerDetailCode = null;
            showCustomerListMode();
        }
        // If we're going back to #invoice from invoice detail, show list
        if (tabName === 'invoice' && state.invoiceDetailNumber) {
            state.invoiceDetailNumber = null;
            showInvoiceListMode();
        }
        switchTabInternal(tabName);
    }
}

// Initialize app
let _initialized = false;
async function init() {
    if (_initialized) return;
    _initialized = true;
    setupEventListeners();
    _setupUploadHandlers();
    setupPickupListeners();
    await fetchStats();
    await fetchFilters();
    await fetchProducts();

    // Set up sortable headers for all tables (reusable for any future table)
    setupSortableHeaders('#view-products .data-table', 'sort', 'sortDir', fetchProducts, 'part_code', 'asc');
    setupSortableHeaders('#view-moves .data-table', 'movesSort', 'movesSortDir', fetchMoves, '', '');
    setupSortableHeaders('#view-flags .data-table', 'flagsSort', 'flagsSortDir', fetchFlags, '', '');
    setupSortableHeaders('#view-photo-flags .data-table', 'photoFlagsSort', 'photoFlagsSortDir', fetchPhotoFlags, '', '');
    setupSortableHeaders('#invoice-table', 'invoicesSort', 'invoicesSortDir', fetchInvoices, 'invoice_date', 'desc');

    // Load sync changes from server (for users arriving after a sync completed)
    await loadSyncChanges();

    // Fetch flags count for tab badge (lightweight — just first page)
    fetchFlagsCount();
    fetchPhotoFlagsCount();

    // Set initial hash (replaceState so we don't add an extra entry)
    if (!location.hash) {
        navReplace('products');
    } else {
        // Restore from hash on page load / refresh
        handleNavigation();
    }
}

// Fetch last sync changes from server so new page loads see highlights
async function loadSyncChanges() {
    try {
        const res = await fetch('/api/sync/changes');
        const data = await res.json();
        if (data.changed_product_skus && data.changed_product_skus.length > 0) {
            state.syncNewProductSkus = new Set(data.changed_product_skus);
            if (data.detection_times) {
                state.syncDetectionTimes = new Map(Object.entries(data.detection_times));
            }
            renderProducts();
            console.log(`[Sync] Loaded ${data.changed_product_skus.length} product highlight(s) from server`);
        }
        if (data.new_move_keys && data.new_move_keys.length > 0) {
            state.syncNewMoveKeys = new Set(data.new_move_keys);
            console.log(`[Sync] Loaded ${data.new_move_keys.length} move highlight(s) from server`);
        }
    } catch (err) {
        // Not critical — highlights just won't show for new arrivals
        console.log('[Sync] No sync changes available from server');
    }
}

/**
 * Generic sortable table headers utility.
 * Clicking a header toggles: Natural → Ascending → Descending → Natural.
 * 
 * @param {string} tableSelector - CSS selector for the table element
 * @param {string} sortKey       - state property name for the sort column (e.g. 'sort', 'movesSort')
 * @param {string} dirKey        - state property name for the sort direction (e.g. 'sortDir', 'movesSortDir')
 * @param {Function} fetchFn     - function to call after sort changes
 * @param {string} defaultSort   - default sort column when in 'natural' mode
 * @param {string} defaultDir    - default direction when in 'natural' mode
 */
function setupSortableHeaders(tableSelector, sortKey, dirKey, fetchFn, defaultSort, defaultDir) {
    const table = document.querySelector(tableSelector);
    if (!table) return;

    const headers = table.querySelectorAll('th.sortable');
    headers.forEach(th => {
        th.addEventListener('click', () => {
            const col = th.dataset.sort;
            if (!col) return;

            const currentSort = state[sortKey];
            const currentDir = state[dirKey];

            // Three-state toggle: natural → asc → desc → natural
            if (currentSort !== col) {
                // Clicking a new column: start ascending
                state[sortKey] = col;
                state[dirKey] = 'asc';
            } else if (currentDir === 'asc') {
                // Same column, currently asc → switch to desc
                state[dirKey] = 'desc';
            } else {
                // Same column, currently desc → reset to natural
                state[sortKey] = defaultSort;
                state[dirKey] = defaultDir;
            }

            // Update visual indicators across all headers in this table
            headers.forEach(h => {
                h.classList.remove('sort-asc', 'sort-desc', 'sort-active');
            });

            if (state[sortKey] && state[sortKey] === col) {
                th.classList.add('sort-active');
                th.classList.add(state[dirKey] === 'asc' ? 'sort-asc' : 'sort-desc');
            }

            // Reset to page 1 and re-fetch
            if (sortKey === 'sort') state.page = 1;
            else if (sortKey === 'movesSort') state.movesPage = 1;
            else if (sortKey === 'flagsSort') state.flagsPage = 1;
            else if (sortKey === 'photoFlagsSort') state.photoFlagsPage = 1;
            else if (sortKey === 'invoicesSort') state.invoicesPage = 1;

            fetchFn();
        });
    });

    // Set initial visual state if there's a default sort
    if (defaultSort) {
        headers.forEach(th => {
            if (th.dataset.sort === defaultSort) {
                th.classList.add('sort-active', defaultDir === 'asc' ? 'sort-asc' : 'sort-desc');
            }
        });
    }
}

// Event Listeners
function setupEventListeners() {
    // Tabs Navigation
    els.tabBtnProducts.addEventListener('click', () => switchTab('products'));
    els.tabBtnMoves.addEventListener('click', () => switchTab('moves'));
    els.tabBtnFlags.addEventListener('click', () => switchTab('flags'));
    if (els.tabBtnPhotoFlags) els.tabBtnPhotoFlags.addEventListener('click', () => switchTab('photo-flags'));
    if (els.tabBtnCustomer) els.tabBtnCustomer.addEventListener('click', () => switchTab('customer'));
    if (els.tabBtnInvoice) els.tabBtnInvoice.addEventListener('click', () => switchTab('invoice'));

    // --- PRODUCTS ---
    let debounceTimer;
    els.searchInput.addEventListener('input', (e) => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => {
            state.search = e.target.value;
            state.page = 1;
            fetchProducts();
        }, 400);
    });

    els.brandFilter.addEventListener('change', (e) => {
        state.brand = e.target.value;
        state.page = 1;
        fetchProducts();
    });

    els.suffixFilter.addEventListener('change', (e) => {
        state.suffix = e.target.value;
        state.page = 1;
        fetchProducts();
    });

    els.activeFilter.addEventListener('change', (e) => {
        state.activeDays = e.target.value;
        state.page = 1;
        fetchProducts();
    });

    els.sortFilter.addEventListener('change', (e) => {
        state.sort = e.target.value;
        state.page = 1;
        fetchProducts();
    });

    els.thumbSizeSlider.addEventListener('input', (e) => {
        document.documentElement.style.setProperty('--thumb-size', `${e.target.value}px`);
    });
    document.documentElement.style.setProperty('--thumb-size', `${els.thumbSizeSlider.value}px`);

    els.sortDirBtn.addEventListener('click', () => {
        state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
        if (state.sortDir === 'asc') {
            els.sortIconAsc.classList.remove('hidden');
            els.sortIconDesc.classList.add('hidden');
        } else {
            els.sortIconAsc.classList.add('hidden');
            els.sortIconDesc.classList.remove('hidden');
        }
        state.page = 1;
        fetchProducts();
    });

    els.btnPrev.addEventListener('click', () => {
        if (state.page > 1) { state.page--; fetchProducts(); }
    });

    els.btnNext.addEventListener('click', () => {
        if (state.page < state.totalPages) { state.page++; fetchProducts(); }
    });


    // --- MOVES ---
    let movesDebounce;
    els.movesSearchInput.addEventListener('input', (e) => {
        clearTimeout(movesDebounce);
        movesDebounce = setTimeout(() => {
            state.movesSearch = e.target.value;
            state.movesPage = 1;
            fetchMoves();
        }, 400);
    });

    els.movesTypeFilter.addEventListener('change', (e) => {
        state.movesType = e.target.value;
        state.movesPage = 1;
        fetchMoves();
    });

    els.movesBtnPrev.addEventListener('click', () => {
        if (state.movesPage > 1) { state.movesPage--; fetchMoves(); }
    });

    els.movesBtnNext.addEventListener('click', () => {
        if (state.movesPage < state.movesTotalPages) { state.movesPage++; fetchMoves(); }
    });

    // Modal
    els.closeModal.addEventListener('click', closeModal);
    els.modal.addEventListener('click', (e) => {
        if (e.target === els.modal) closeModal();
    });

    // Main image trash button (hide the currently displayed image)
    els.mainImageTrashBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        const filename = els.modalMainImg.dataset.filename;
        if (filename) hideImage(filename);
    });

    // Modal keyboard shortcuts (Escape, ArrowUp, ArrowDown)
    document.addEventListener('keydown', (e) => {
        if (els.modal.classList.contains('hidden')) return;

        // Don't intercept when typing in an input/textarea
        const tag = document.activeElement?.tagName;
        if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

        if (e.key === 'Escape') {
            closeModal();
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            navigateModal(-1);
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            navigateModal(1);
        } else if (e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
            e.preventDefault();
            const thumbs = els.modalThumbnails.querySelectorAll('.gallery-thumb');
            if (thumbs.length <= 1) return;
            const activeThumb = els.modalThumbnails.querySelector('.gallery-thumb.active');
            let currentIdx = activeThumb ? Array.from(thumbs).indexOf(activeThumb) : 0;
            if (e.key === 'ArrowLeft') {
                currentIdx = (currentIdx - 1 + thumbs.length) % thumbs.length;
            } else {
                currentIdx = (currentIdx + 1) % thumbs.length;
            }
            thumbs[currentIdx].click();
        }
    });

    // Modal navigation buttons
    els.modalPrevBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        navigateModal(-1);
    });
    els.modalNextBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        navigateModal(1);
    });

    // ── Unified popstate handler ──────────────────────────────────────
    window.addEventListener('popstate', () => {
        _handlingPopstate = true;
        handleNavigation();
        _handlingPopstate = false;
    });

    // Flags Specific Event Listeners
    let flagsDebounce;
    els.flagsSearchInput.addEventListener('input', (e) => {
        clearTimeout(flagsDebounce);
        flagsDebounce = setTimeout(() => {
            state.flagsSearch = e.target.value;
            state.flagsPage = 1;
            fetchFlags();
        }, 400);
    });

    els.flagsBtnPrev.addEventListener('click', () => {
        if (state.flagsPage > 1) { state.flagsPage--; fetchFlags(); }
    });

    els.flagsBtnNext.addEventListener('click', () => {
        if (state.flagsPage < state.flagsTotalPages) { state.flagsPage++; fetchFlags(); }
    });

    // --- Resolve (unflag) button – delegated listener on the tbody so it survives re-renders ---
    els.flagsList.addEventListener('click', async (e) => {
        const btn = e.target.closest('.unflag-btn');
        if (!btn) return;
        e.stopPropagation();

        // Guard: only admins can resolve
        if (!_currentUser || _currentUser.role !== 'admin') {
            alert('เฉพาะ Admin เท่านั้นที่สามารถ Resolve ได้');
            return;
        }

        const sku = btn.dataset.sku;
        if (!confirm('ยืนยันการ Resolve รายการนี้?')) return;
        try {
            btn.disabled = true;
            const res = await fetch(`/api/products/${sku}/flag`, { method: 'DELETE' });
            if (res.ok) {
                fetchFlags();
                fetchProducts();
            } else if (res.status === 403) {
                alert('เฉพาะ Admin เท่านั้นที่สามารถ Resolve ได้');
                btn.disabled = false;
            } else {
                alert('Failed to unflag.');
                btn.disabled = false;
            }
        } catch (err) {
            console.error(err);
            btn.disabled = false;
        }
    });

    // --- PHOTO FLAGS ---
    let photoFlagsDebounce;
    if (els.photoFlagsSearchInput) {
        els.photoFlagsSearchInput.addEventListener('input', (e) => {
            clearTimeout(photoFlagsDebounce);
            photoFlagsDebounce = setTimeout(() => {
                state.photoFlagsSearch = e.target.value;
                state.photoFlagsPage = 1;
                fetchPhotoFlags();
            }, 400);
        });
    }

    if (els.photoFlagsBtnPrev) {
        els.photoFlagsBtnPrev.addEventListener('click', () => {
            if (state.photoFlagsPage > 1) { state.photoFlagsPage--; fetchPhotoFlags(); }
        });
    }

    if (els.photoFlagsBtnNext) {
        els.photoFlagsBtnNext.addEventListener('click', () => {
            if (state.photoFlagsPage < state.photoFlagsTotalPages) { state.photoFlagsPage++; fetchPhotoFlags(); }
        });
    }

    // --- Batch upload from photo flags table (mirrors product modal UX) ---
    let _photoFlagsUploadSku = null;
    let _pfPendingFiles = [];          // accumulates across multiple picks
    let _pfIsAddingMore = false;       // true when tapping "เพิ่มรูป"

    const _pfFileInput = document.createElement('input');
    _pfFileInput.type = 'file';
    _pfFileInput.accept = 'image/jpeg,image/png,image/webp';
    // Only set capture on mobile — on desktop it can block the file picker
    const _isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
    if (_isMobile) _pfFileInput.setAttribute('capture', 'environment');
    _pfFileInput.multiple = true;
    _pfFileInput.style.display = 'none';
    document.body.appendChild(_pfFileInput);

    const _pfOverlay      = document.getElementById('pf-upload-overlay');
    const _pfPreviewArea  = document.getElementById('pf-upload-preview-area');
    const _pfSkuLabel     = document.getElementById('pf-upload-sku');
    const _pfAddMoreBtn   = document.getElementById('pf-btn-add-more');
    const _pfCancelBtn    = document.getElementById('pf-btn-cancel-upload');
    const _pfConfirmBtn   = document.getElementById('pf-btn-confirm-upload');
    const _pfCommentInput = document.getElementById('pf-upload-comment');
    const _pfProgressBar  = document.getElementById('pf-upload-progress');
    const _pfProgressInner = document.getElementById('pf-upload-progress-bar');

    // Helper: add a single file's preview thumbnail (with delete button)
    function _pfAddPreviewThumb(file) {
        const thumb = document.createElement('div');
        thumb.className = 'upload-preview-thumb';
        const img = document.createElement('img');
        const blobUrl = URL.createObjectURL(file);
        img.src = blobUrl;
        img.onload = () => URL.revokeObjectURL(blobUrl); // Free memory after render
        thumb.appendChild(img);
        // Delete button to remove this photo before uploading
        const delBtn = document.createElement('button');
        delBtn.className = 'upload-preview-delete-btn';
        delBtn.type = 'button';
        delBtn.title = 'ลบรูปนี้ / Remove';
        delBtn.textContent = '✕';
        delBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const idx = _pfPendingFiles.indexOf(file);
            if (idx > -1) _pfPendingFiles.splice(idx, 1);
            thumb.remove();
            _pfUpdateLabel();
            // If no files left, close the overlay
            if (_pfPendingFiles.length === 0) {
                _pfHideOverlay();
                _photoFlagsUploadSku = null;
            }
        });
        thumb.appendChild(delBtn);
        const name = document.createElement('span');
        name.className = 'upload-preview-name';
        name.textContent = file.name;
        thumb.appendChild(name);
        _pfPreviewArea.appendChild(thumb);
    }

    // Helper: update confirm button count badge
    function _pfUpdateLabel() {
        const count = _pfPendingFiles.length;
        _pfConfirmBtn.querySelector('.upload-count')?.remove();
        if (count > 0) {
            const badge = document.createElement('span');
            badge.className = 'upload-count';
            badge.textContent = ` (${count} รูป)`;
            _pfConfirmBtn.appendChild(badge);
        }
    }

    // Helper: open / close the overlay
    function _pfShowOverlay() { _pfOverlay.classList.remove('hidden'); }
    function _pfHideOverlay() {
        _pfOverlay.classList.add('hidden');
        _pfPendingFiles = [];
        _pfPreviewArea.innerHTML = '';
        _pfCommentInput.value = '';
        _pfConfirmBtn.querySelector('.upload-count')?.remove();
        _pfProgressBar.classList.add('hidden');
        _pfProgressInner.style.width = '0%';
        _pfConfirmBtn.disabled = false;
        if (_pfAddMoreBtn) _pfAddMoreBtn.disabled = false;
    }

    // File input change → show preview or append
    _pfFileInput.addEventListener('change', (e) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        if (!_pfIsAddingMore) {
            // Fresh upload: reset everything
            _pfPendingFiles = [];
            _pfPreviewArea.innerHTML = '';
            _pfCommentInput.value = '';
        }

        // Append new files
        Array.from(files).forEach(file => {
            _pfPendingFiles.push(file);
            _pfAddPreviewThumb(file);
        });

        _pfUpdateLabel();
        _pfShowOverlay();
        _pfIsAddingMore = false;
        _pfFileInput.value = '';  // Reset so same file can be selected again
    });

    // "เพิ่มรูป / Add More" button
    if (_pfAddMoreBtn) {
        _pfAddMoreBtn.addEventListener('click', () => {
            _pfIsAddingMore = true;
            _pfFileInput.click();
        });
    }

    // Cancel (only if not mid-upload)
    _pfCancelBtn.addEventListener('click', () => {
        if (_pfConfirmBtn.disabled) return; // Upload in progress, ignore
        _pfHideOverlay();
        _photoFlagsUploadSku = null;
    });

    // Backdrop click to dismiss (only if not mid-upload)
    _pfOverlay.addEventListener('click', (e) => {
        if (e.target === _pfOverlay && !_pfConfirmBtn.disabled) {
            _pfHideOverlay();
            _photoFlagsUploadSku = null;
        }
    });

    // Confirm upload
    _pfConfirmBtn.addEventListener('click', async () => {
        if (_pfPendingFiles.length === 0 || !_photoFlagsUploadSku) return;

        const sku = _photoFlagsUploadSku;
        const comment = _pfCommentInput.value.trim();

        _pfConfirmBtn.disabled = true;
        if (_pfAddMoreBtn) _pfAddMoreBtn.disabled = true;
        _pfProgressBar.classList.remove('hidden');
        _pfProgressInner.style.width = '30%';

        try {
            const formData = new FormData();
            _pfPendingFiles.forEach(file => formData.append('files', file));
            if (comment) formData.append('comment', comment);

            _pfProgressInner.style.width = '60%';

            const res = await fetch(`/api/products/${encodeURIComponent(sku)}/images/upload`, {
                method: 'POST',
                body: formData,
            });
            const data = await res.json();

            _pfProgressInner.style.width = '100%';

            if (data.success) {
                const count = data.uploaded ? data.uploaded.length : _pfPendingFiles.length;
                alert(`อัปโหลดสำเร็จ ${count} รูป`);
                if (data.errors && data.errors.length > 0) {
                    alert('บางไฟล์มีปัญหา:\n' + data.errors.join('\n'));
                }
                fetchPhotoFlags();
                fetchProducts();
            } else {
                alert('อัปโหลดไม่สำเร็จ: ' + (data.error || data.errors?.join('\n') || 'Unknown error'));
            }
        } catch (err) {
            console.error('Photo flags batch upload error:', err);
            alert('อัปโหลดไม่สำเร็จ: ' + err.message);
        } finally {
            _pfHideOverlay();
            _photoFlagsUploadSku = null;
        }
    });

    // Resolve (remove photo flag) button + Upload button – delegated listener
    if (els.photoFlagsList) {
        els.photoFlagsList.addEventListener('click', async (e) => {
            // --- Handle inline upload button ---
            const uploadBtn = e.target.closest('.photo-upload-btn');
            if (uploadBtn) {
                e.stopPropagation();
                _photoFlagsUploadSku = uploadBtn.dataset.sku;
                _pfSkuLabel.textContent = uploadBtn.dataset.sku;
                _pfIsAddingMore = false;
                _pfFileInput.click();
                return;
            }

            // --- Handle resolve/unflag button ---
            const btn = e.target.closest('.photo-unflag-btn');
            if (!btn) return;
            e.stopPropagation();

            if (!_currentUser || _currentUser.role !== 'admin') {
                alert('เฉพาะ Admin เท่านั้นที่สามารถ Resolve ได้');
                return;
            }

            const sku = btn.dataset.sku;
            if (!confirm('ยืนยันว่าถ่ายรูปเรียบร้อยแล้ว?')) return;
            try {
                btn.disabled = true;
                const res = await fetch(`/api/products/${sku}/photo-flag`, { method: 'DELETE' });
                if (res.ok) {
                    fetchPhotoFlags();
                    fetchProducts();
                } else if (res.status === 403) {
                    alert('เฉพาะ Admin เท่านั้นที่สามารถ Resolve ได้');
                    btn.disabled = false;
                } else {
                    alert('Failed to resolve photo flag.');
                    btn.disabled = false;
                }
            } catch (err) {
                console.error(err);
                btn.disabled = false;
            }
        });
    }

    // --- CUSTOMER ACTIVITY ---
    let customerDebounce;
    if (els.customerSearchInput) {
        els.customerSearchInput.addEventListener('input', (e) => {
            clearTimeout(customerDebounce);
            customerDebounce = setTimeout(() => {
                state.customerSearch = e.target.value.trim();
                state.customersPage = 1;
                // If in detail mode, go back to list
                state.customerDetailCode = null;
                fetchCustomers();
            }, 400);
        });
    }

    // Customer list pagination
    if (els.custBtnPrev) {
        els.custBtnPrev.addEventListener('click', () => {
            if (state.customersPage > 1) { state.customersPage--; fetchCustomers(); }
        });
    }
    if (els.custBtnNext) {
        els.custBtnNext.addEventListener('click', () => {
            if (state.customersPage < state.customersTotalPages) { state.customersPage++; fetchCustomers(); }
        });
    }

    // Customer back button – use browser back so history stays consistent
    if (els.custBackBtn) {
        els.custBackBtn.addEventListener('click', () => {
            history.back();
        });
    }

    // --- INVOICE ---
    let invoiceDebounce;
    if (els.invoiceSearchInput) {
        els.invoiceSearchInput.addEventListener('input', (e) => {
            clearTimeout(invoiceDebounce);
            invoiceDebounce = setTimeout(() => {
                state.invoicesSearch = e.target.value.trim();
                state.invoicesPage = 1;
                state.invoiceDetailNumber = null;
                showInvoiceListMode();
                fetchInvoices();
            }, 400);
        });
    }

    if (els.invoiceDocTypeFilter) {
        els.invoiceDocTypeFilter.addEventListener('change', (e) => {
            state.invoicesDocType = e.target.value;
            state.invoicesPage = 1;
            fetchInvoices();
        });
    }

    if (els.invBtnPrev) {
        els.invBtnPrev.addEventListener('click', () => {
            if (state.invoicesPage > 1) { state.invoicesPage--; fetchInvoices(); }
        });
    }
    if (els.invBtnNext) {
        els.invBtnNext.addEventListener('click', () => {
            if (state.invoicesPage < state.invoicesTotalPages) { state.invoicesPage++; fetchInvoices(); }
        });
    }

    // Invoice back button – use browser back so history stays consistent
    if (els.invBackBtn) {
        els.invBackBtn.addEventListener('click', () => {
            history.back();
        });
    }

    // Refresh Customer button — non-blocking background sync
    if (els.refreshCustomerBtn) {
        els.refreshCustomerBtn.addEventListener('click', async () => {
            try {
                const res = await fetch('/api/sync/trigger/customer', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    console.log('Customer sync triggered in background');
                } else {
                    alert(data.message || 'Already syncing');
                }
            } catch (err) {
                console.error('Customer sync trigger error:', err);
            }
        });
    }

    // Refresh Invoice button — non-blocking background sync
    if (els.refreshInvoiceBtn) {
        els.refreshInvoiceBtn.addEventListener('click', async () => {
            try {
                const res = await fetch('/api/sync/trigger/invoice', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    console.log('Invoice sync triggered in background');
                } else {
                    alert(data.message || 'Already syncing');
                }
            } catch (err) {
                console.error('Invoice sync trigger error:', err);
            }
        });
    }

    // Handle Report Dialog Open/Close
    els.btnReportIssue.addEventListener('click', () => {
        els.btnReportIssue.classList.add('hidden');
        els.reportDialog.classList.remove('hidden');
    });

    els.btnCancelReport.addEventListener('click', () => {
        els.btnReportIssue.classList.remove('hidden');
        els.reportDialog.classList.add('hidden');
        // Reset form
        els.reportNote.value = '';
        els.flagTypeRadios.forEach(r => r.checked = false);
    });

    els.btnSubmitReport.addEventListener('click', submitFlag);

    // Handle Photo Flag Dialog Open/Close
    if (els.btnPhotoFlag) {
        els.btnPhotoFlag.addEventListener('click', () => {
            els.photoFlagDialog.classList.toggle('hidden');
        });
    }

    if (els.btnCancelPhotoFlag) {
        els.btnCancelPhotoFlag.addEventListener('click', () => {
            els.photoFlagDialog.classList.add('hidden');
            els.photoFlagNote.value = '';
        });
    }

    if (els.btnSubmitPhotoFlag) {
        els.btnSubmitPhotoFlag.addEventListener('click', async () => {
            const sku = state.currentModalSku;
            if (!sku) return;
            const note = els.photoFlagNote.value.trim();
            try {
                els.btnSubmitPhotoFlag.disabled = true;
                els.btnSubmitPhotoFlag.textContent = 'กำลังส่ง...';
                const res = await fetch(`/api/products/${sku}/photo-flag`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ note })
                });
                if (res.ok) {
                    alert('แจ้งต้องการรูปเพิ่มเรียบร้อยแล้ว');
                    els.photoFlagDialog.classList.add('hidden');
                    els.photoFlagNote.value = '';
                    fetchProducts();
                    if (state.photoFlags.length > 0) fetchPhotoFlags();
                    fetchPhotoFlagsCount();
                } else {
                    const data = await res.json();
                    alert(`Error: ${data.error || 'Failed to submit'}`);
                }
            } catch (err) {
                console.error(err);
                alert('เกิดข้อผิดพลาด');
            } finally {
                els.btnSubmitPhotoFlag.disabled = false;
                els.btnSubmitPhotoFlag.textContent = '📷 ยืนยัน';
            }
        });
    }

    // Refresh Master button — non-blocking background sync
    els.refreshMasterBtn.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/sync/trigger/master', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                console.log('Master sync triggered in background');
            } else {
                alert(data.message || 'Already syncing');
            }
        } catch (err) {
            console.error('Master sync trigger error:', err);
        }
    });

    // Refresh Ledger button — non-blocking background sync
    els.refreshLedgerBtn.addEventListener('click', async () => {
        try {
            const res = await fetch('/api/sync/trigger/ledger', { method: 'POST' });
            const data = await res.json();
            if (data.success) {
                console.log('Ledger sync triggered in background');
            } else {
                alert(data.message || 'Already syncing');
            }
        } catch (err) {
            console.error('Ledger sync trigger error:', err);
        }
    });


}



// API Calls
async function fetchStats() {
    try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        els.totalSkus.textContent = formatNumber(data.total_skus);
        if (els.ledgerModDate && data.ledger_mod_date) {
            els.ledgerModDate.textContent = `Updated: ${data.ledger_mod_date}`;
        }
        if (els.masterModDate && data.master_mod_date) {
            els.masterModDate.textContent = `Updated: ${data.master_mod_date}`;
        }
        if (els.invoiceModDate && data.invoice_mod_date) {
            els.invoiceModDate.textContent = `Updated: ${data.invoice_mod_date}`;
        }
        if (els.customerModDate && data.customer_mod_date) {
            els.customerModDate.textContent = `Updated: ${data.customer_mod_date}`;
        }
    } catch (err) {
        console.error("Error fetching stats:", err);
    }
}

async function fetchFilters() {
    try {
        // Fetch brands
        const resBrands = await fetch('/api/brands');
        state.brands = await resBrands.json();

        state.brands.forEach(brand => {
            const option = document.createElement('option');
            option.value = brand;
            option.textContent = brand;
            els.brandFilter.appendChild(option);
        });

        // Fetch suffixes
        const resSuffixes = await fetch('/api/suffixes');
        state.suffixes = await resSuffixes.json();

        state.suffixes.forEach(suffix => {
            const option = document.createElement('option');
            option.value = suffix.id;
            // Short labels for dropdown
            const label = suffix.id + ' - ' + suffix.label.split(' ')[0];
            option.textContent = label;
            els.suffixFilter.appendChild(option);
        });
    } catch (err) {
        console.error("Error fetching filters:", err);
    }
}

async function fetchProducts() {
    // Show loading state, span across 11 cols if activeDays, otherwise 10
    const colspan = state.activeDays ? '11' : '10';
    els.productList.innerHTML = `
        <tr>
            <td colspan="${colspan}" class="text-center py-8">
                <div class="spinner"></div>
                <p class="text-muted mt-4">Loading inventory data...</p>
            </td>
        </tr>
    `;

    // Manage Amount Sold column header visibility
    if (state.activeDays) {
        els.colAmountSold.classList.remove('hidden');
        if (state.activeDays === '1') {
            els.colAmountSold.textContent = 'Amount Sold (Last 1 Day)';
        } else {
            els.colAmountSold.textContent = `Amount Sold (Last ${state.activeDays} Days)`;
        }
    } else {
        els.colAmountSold.classList.add('hidden');
    }

    // Build URL params
    const params = new URLSearchParams({
        search: state.search,
        brand: state.brand,
        suffix: state.suffix,
        active_days: state.activeDays,
        sort: state.sort,
        dir: state.sortDir,
        page: state.page,
        per_page: state.perPage
    });

    try {
        const res = await fetch(`/api/products?${params}`);
        const data = await res.json();

        state.products = data.items;
        state.totalItems = data.total;
        state.totalPages = data.total_pages;
        state.page = data.page;

        renderProducts();
        updatePaginationInfo();
        renderPaginationControls();
    } catch (err) {
        console.error("Error fetching products:", err);
        const colspan = state.activeDays ? '11' : '10';
        els.productList.innerHTML = `
            <tr>
                <td colspan="${colspan}" class="text-center py-8 text-error">
                    Failed to load data. Please make sure the server is running.
                </td>
            </tr>
        `;
    }
}

async function fetchProductDetail(sku) {
    try {
        const res = await fetch(`/api/products/${encodeURIComponent(sku)}/detail`);
        if (!res.ok) return null;
        return await res.json();
    } catch (err) {
        console.error("Error fetching product detail:", err);
        return null;
    }
}

// Track current gallery permissions and image data for re-use by upload/delete
let _galleryPermissions = { can_upload: false, can_delete: false };
let _galleryImages = [];  // array of {url, source, filename, comment, uploaded_by, uploaded_at}

async function fetchProductImages(sku) {
    try {
        const res = await fetch(`/api/products/${encodeURIComponent(sku)}/images`);
        const data = await res.json();
        // New API returns { images: [...], permissions: {...} }
        if (data && data.images) {
            _galleryPermissions = data.permissions || { can_upload: false, can_delete: false };
            _galleryImages = data.images;
            return data.images;
        }
        // Fallback for any edge case
        _galleryPermissions = { can_upload: false, can_delete: false };
        _galleryImages = [];
        return [];
    } catch (err) {
        console.error("Error fetching product images:", err);
        _galleryPermissions = { can_upload: false, can_delete: false };
        _galleryImages = [];
        return [];
    }
}

// Rendering
function renderProducts() {
    const colspan = state.activeDays ? '11' : '10';
    if (state.products.length === 0) {
        els.productList.innerHTML = `
            <tr>
                <td colspan="${colspan}" class="text-center py-8 text-muted">
                    No products found matching your criteria.
                </td>
            </tr>
        `;
        return;
    }

    els.productList.innerHTML = '';

    state.products.forEach((p, idx) => {
        const tr = document.createElement('tr');
        tr.onclick = () => openModal(p, idx);

        // Highlight row if it was detected as new/changed after sync
        if (state.syncNewProductSkus.has(p.sku)) {
            tr.classList.add('sync-new-row');
        }

        // Highlight row if product is flagged
        if (p.flag_type) {
            tr.classList.add('flagged-row');
            tr.dataset.flagType = p.flag_type;
        }

        const suffixClass = `type-${p.suffix.toLowerCase()}`;

        // Thumbnail content
        let thumbContent = p.thumbnail
            ? `<img src="/images/${p.thumbnail}" alt="${p.part_code} thumbnail" loading="lazy">`
            : `<svg viewBox="0 0 24 24" stroke="currentColor" stroke-width="2" fill="none" class="thumb-placeholder"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>`;

        // Quantity styling (use on_hand_qty from CSV, fallback to qty)
        const displayQty = p.on_hand_qty !== undefined ? p.on_hand_qty : p.qty;
        const qtyClass = displayQty <= 5 ? 'qty-low' : '';

        // Last sold date HTML — uses server-computed days_ago to avoid client clock issues
        let lastSoldHTML = `<span class="text-muted" style="font-size: 0.9em;">-</span>`;
        if (p.last_sold_date) {
            const beDate = formatBuddhistDate(p.last_sold_date);
            if (p.days_ago !== null && p.days_ago !== undefined) {
                if (p.days_ago < 0) {
                    // Future date
                    const futureDays = Math.abs(p.days_ago);
                    const diffText = `${futureDays} วันข้างหน้า`;
                    lastSoldHTML = `
                        <span class="text-muted" style="font-size: 0.9em;">${beDate}</span><br>
                        <span style="font-weight: 700; font-size: 1.1em; color: #f59e0b;">(${diffText})</span>
                    `;
                } else {
                    const diffText = p.days_ago === 0 ? 'วันนี้' : `${p.days_ago} วันก่อน`;
                    // Show detection time for items sold today
                    const detTime = (p.days_ago === 0 && state.syncDetectionTimes.has(p.sku))
                        ? `<br><span class="sync-detection-time">ตรวจพบเมื่อ ${state.syncDetectionTimes.get(p.sku)}</span>`
                        : '';
                    lastSoldHTML = `
                        <span class="text-muted" style="font-size: 0.9em;">${beDate}</span><br>
                        <span style="font-weight: 700; font-size: 1.1em; color: var(--text-primary);">(${diffText})</span>${detTime}
                    `;
                }
            } else {
                // Fallback: just show the date without days_ago
                lastSoldHTML = `<span class="text-muted" style="font-size: 0.9em;">${beDate}</span>`;
            }
        }

        // Flagged styling indicator — color-coded badge with Thai label
        const flagTypeLabels = {
            'out_of_stock': '⚠ สินค้าหมด (ระบบยังแสดง)',
            'less_than': '⚠ น้อยกว่าระบบ',
            'more_than': 'ℹ มากกว่าระบบ'
        };
        const flagIndicator = p.flag_type
            ? `<div class="flag-indicator ${p.flag_type}">
                 <svg viewBox="0 0 24 24" width="12" height="12" stroke="currentColor" stroke-width="2.5" fill="none">
                   <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"></path>
                   <line x1="4" y1="22" x2="4" y2="15"></line>
                 </svg>
                 ${flagTypeLabels[p.flag_type] || p.flag_type}
               </div>`
            : '';

        // Photo flag badge (camera icon)
        const photoFlagBadge = p.photo_flag
            ? `<div class="flag-indicator photo-flag">
                 📷 ต้องการรูปเพิ่ม
               </div>`
            : '';

        tr.innerHTML = `
            <td>
                <div class="thumb-cell">
                    ${thumbContent}
                    ${p.image_count > 1 ? `<span style="position:absolute; background:rgba(0,0,0,0.7); color:white; font-size:10px; padding:2px 4px; border-radius:4px; right:4px; bottom:4px;">+${p.image_count - 1}</span>` : ''}
                </div>
            </td>
            <td>
                <div style="font-family: monospace; font-size: 1.05rem;">${escapeHtml(p.part_code || '')}${state.syncNewProductSkus.has(p.sku) ? '<span class="sync-badge">อัปเดต</span>' : ''}</div>
                ${flagIndicator}
                ${photoFlagBadge}
            </td>
            <td>
                <div class="suffix-indicator" title="${escapeHtml(p.suffix_label || '')}">
                    <div class="suffix-dot ${suffixClass}"></div>
                    <span>${escapeHtml(p.suffix || '')}</span>
                </div>
            </td>
            <td>
                ${p.brand ? `<span class="brand-badge">${escapeHtml(p.brand)}</span>` : '<span class="text-muted">-</span>'}
            </td>
            <td>
                <div class="desc-cell">
                    <div class="desc-eng" title="${escapeHtml(p.name_eng || '')}">${escapeHtml(p.name_eng || '-')}</div>
                    <div class="desc-thai" title="${escapeHtml(p.name_thai || '')}">${escapeHtml(p.name_thai || '-')}</div>
                </div>
            </td>
            <td>
                <span class="text-muted" title="${escapeHtml(p.size || '')}">${escapeHtml(p.size || '-')}</span>
            </td>
            <td>
                <span class="brand-badge location-badge">${escapeHtml(p.locations || '-')}</span>
            </td>
            <td class="text-right">
                <span class="qty-badge ${qtyClass}">${formatNumber(displayQty)}</span>
            </td>
            <td class="text-right">
                <span class="price-val">${p.sale_price ? formatPrice(p.sale_price) : '-'}</span>
            </td>
            <td class="text-right">
                ${lastSoldHTML}
            </td>
            ${state.activeDays ? `<td class="text-right"><span class="qty-badge" style="background: rgba(239, 68, 68, 0.2); color: #ef4444;">${formatNumber(p.amount_sold || 0)}</span></td>` : ''}
        `;

        // Give absolute positioning context to the thumb cell for the image count badge
        tr.querySelector('.thumb-cell').style.position = 'relative';

        els.productList.appendChild(tr);
    });
}

function updatePaginationInfo() {
    els.resultsCount.textContent = formatNumber(state.totalItems);
    els.totalResults.textContent = formatNumber(state.totalItems);

    if (state.totalItems === 0) {
        els.pageStart.textContent = '0';
        els.pageEnd.textContent = '0';
    } else {
        const start = ((state.page - 1) * state.perPage) + 1;
        const end = Math.min(state.page * state.perPage, state.totalItems);
        els.pageStart.textContent = formatNumber(start);
        els.pageEnd.textContent = formatNumber(end);
    }
}

function renderPaginationControls() {
    // Prev/Next buttons
    els.btnPrev.disabled = state.page <= 1;
    els.btnNext.disabled = state.page >= state.totalPages;

    // Page numbers
    els.pageNumbers.innerHTML = '';

    if (state.totalPages <= 1) return;

    // Logic to show a max of 5 page buttons: first, last, current, current-1, current+1
    // Simplification for the example: just show 5 centered around current
    let startPage = Math.max(1, state.page - 2);
    let endPage = Math.min(state.totalPages, startPage + 4);

    // Adjust start if we're near the end
    if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
    }

    if (startPage > 1) {
        addPageButton(1);
        if (startPage > 2) addEllipsis(els.pageNumbers);
    }

    for (let i = startPage; i <= endPage; i++) {
        addPageButton(i);
    }

    if (endPage < state.totalPages) {
        if (endPage < state.totalPages - 1) addEllipsis(els.pageNumbers);
        addPageButton(state.totalPages);
    }
}

function addPageButton(pageNum) {
    const btn = document.createElement('button');
    btn.className = `page-btn ${pageNum === state.page ? 'active' : ''}`;
    btn.textContent = pageNum;
    if (pageNum !== state.page) {
        btn.onclick = () => {
            state.page = pageNum;
            fetchProducts();
        };
    }
    els.pageNumbers.appendChild(btn);
}

function addEllipsis(containerElement) {
    const span = document.createElement('span');
    span.style.alignSelf = 'center';
    span.style.color = 'var(--text-tertiary)';
    span.textContent = '...';
    containerElement.appendChild(span);
}

// Tabs – public entry point (pushes history)
function switchTab(tabName) {
    // When switching tab from a detail view, clear detail state
    if (tabName === 'customer') {
        state.customerDetailCode = null;
    }
    if (tabName === 'invoice') {
        state.invoiceDetailNumber = null;
    }
    if (!_handlingPopstate) navPush(tabName);
    switchTabInternal(tabName);
}

// Internal tab switch (no history push – used by the popstate router)
function switchTabInternal(tabName) {
    state.currentTab = tabName;

    // Remove active/hidden from all
    els.tabBtnProducts.classList.remove('active');
    els.tabBtnMoves.classList.remove('active');
    els.tabBtnFlags.classList.remove('active');
    if (els.tabBtnPhotoFlags) els.tabBtnPhotoFlags.classList.remove('active');
    if (els.tabBtnCustomer) els.tabBtnCustomer.classList.remove('active');
    if (els.tabBtnInvoice) els.tabBtnInvoice.classList.remove('active');

    els.viewProducts.classList.add('hidden');
    els.viewMoves.classList.add('hidden');
    els.viewFlags.classList.add('hidden');
    if (els.viewPhotoFlags) els.viewPhotoFlags.classList.add('hidden');
    if (els.viewCustomer) els.viewCustomer.classList.add('hidden');
    if (els.viewInvoice) els.viewInvoice.classList.add('hidden');

    if (tabName === 'products') {
        els.tabBtnProducts.classList.add('active');
        els.viewProducts.classList.remove('hidden');
    } else if (tabName === 'moves') {
        els.tabBtnMoves.classList.add('active');
        els.viewMoves.classList.remove('hidden');

        fetchMoves();
    } else if (tabName === 'flags') {
        els.tabBtnFlags.classList.add('active');
        els.viewFlags.classList.remove('hidden');

        fetchFlags();
    } else if (tabName === 'photo-flags') {
        if (els.tabBtnPhotoFlags) els.tabBtnPhotoFlags.classList.add('active');
        if (els.viewPhotoFlags) els.viewPhotoFlags.classList.remove('hidden');

        fetchPhotoFlags();
    } else if (tabName === 'customer') {
        if (els.tabBtnCustomer) els.tabBtnCustomer.classList.add('active');
        if (els.viewCustomer) els.viewCustomer.classList.remove('hidden');

        // If in detail mode, keep it; otherwise load list
        if (!state.customerDetailCode) {
            showCustomerListMode();
            if (state.customers.length === 0) fetchCustomers();
        }
    } else if (tabName === 'invoice') {
        if (els.tabBtnInvoice) els.tabBtnInvoice.classList.add('active');
        if (els.viewInvoice) {
            els.viewInvoice.classList.remove('hidden');
            // Show "under maintenance" message
            if (els.invoiceListPanel) els.invoiceListPanel.classList.add('hidden');
            if (els.invoiceDetailPanel) els.invoiceDetailPanel.classList.add('hidden');
            // Insert maintenance banner if not already present
            let banner = els.viewInvoice.querySelector('.invoice-maintenance-banner');
            if (!banner) {
                banner = document.createElement('div');
                banner.className = 'invoice-maintenance-banner card glass';
                banner.style.cssText = 'text-align: center; padding: 4rem 2rem; margin-top: 1rem;';
                banner.innerHTML = `
                    <div style="font-size: 3rem; margin-bottom: 1rem;">🚧</div>
                    <h2 style="margin: 0 0 0.5rem; color: var(--text-primary); font-size: 1.3rem;">กำลังปรับปรุง</h2>
                    <p style="color: var(--text-secondary); font-size: 0.95rem; margin: 0;">ระบบใบกำกับภาษีอยู่ระหว่างปรับปรุง กรุณากลับมาใหม่ภายหลัง</p>
                `;
                els.viewInvoice.appendChild(banner);
            }
            banner.classList.remove('hidden');
        }
    }
}

// Moves specific code
async function fetchMoves() {
    els.movesList.innerHTML = `
        <tr>
            <td colspan="9" class="text-center py-8">
                <div class="spinner"></div>
                <p class="text-muted mt-4">Loading stock moves...</p>
            </td>
        </tr>
    `;

    const params = new URLSearchParams({
        search: state.movesSearch,
        type: state.movesType,
        sort: state.movesSort,
        dir: state.movesSortDir,
        page: state.movesPage,
        per_page: state.movesPerPage
    });

    try {
        const res = await fetch(`/api/moves?${params}`);
        const data = await res.json();

        state.moves = data.items;
        state.movesTotalItems = data.total;
        state.movesTotalPages = data.total_pages;
        state.movesPage = data.page;

        renderMoves();
        updateMovesPaginationInfo();
        renderMovesPaginationControls();
    } catch (err) {
        console.error("Error fetching moves:", err);
        els.movesList.innerHTML = `
            <tr>
                <td colspan="9" class="text-center py-8 text-error">Failed to load stock moves.</td>
            </tr>
        `;
    }
}

function renderMoves() {
    if (state.moves.length === 0) {
        els.movesList.innerHTML = `<tr><td colspan="9" class="text-center py-8 text-muted">No stock moves found.</td></tr>`;
        return;
    }

    els.movesList.innerHTML = '';
    state.moves.forEach((m, idx) => {
        const tr = document.createElement('tr');

        // Highlight row if detected as new after sync
        const moveKey = `${m.part_code}|${m.date}|${m.doc_ref}|${m.qty_in}|${m.qty_out}`;
        if (state.syncNewMoveKeys.has(moveKey)) {
            tr.classList.add('sync-new-row');
        }

        // Setup row click to open modal with move data normalized to product shape
        tr.onclick = () => {
            openModal({
                sku: m.sku, part_code: m.part_code, name_eng: m.name_eng, name_thai: m.name_thai,
                brand: m.brand, suffix: m.sku_type || '-', qty: m.running_balance, sale_price: m.unit_price, thumbnail: m.thumbnail
            }, idx);
        };

        const formattedDate = formatBuddhistDate(m.date);

        let outHtml = m.qty_out > 0 ? `<span class="change-out">${formatNumber(m.qty_out)}</span>` : '<span class="text-muted">0</span>';
        let inHtml = m.qty_in > 0 ? `<span class="change-in">+${formatNumber(m.qty_in)}</span>` : '<span class="text-muted">0</span>';

        tr.innerHTML = `
            <td style="white-space:nowrap;">${formattedDate}</td>
            <td>${m.doc_ref || '-'}</td>
            <td>${getCategoryThai(m.category_name)}</td>
            <td><div style="font-family: monospace; font-size: 1.05rem;">${m.part_code}${state.syncNewMoveKeys.has(moveKey) ? '<span class="sync-badge">อัปเดต</span>' : ''}</div></td>
            <td>
                <div class="desc-cell">
                    <div class="desc-eng">${m.name_eng || '-'}</div>
                    <div class="desc-thai">${m.name_thai || '-'}</div>
                </div>
            </td>
            <td class="text-right">${inHtml}</td>
            <td class="text-right">${outHtml}</td>
            <td class="text-right">${m.unit_price ? formatPrice(m.unit_price) : '-'}</td>
            <td class="text-right"><strong>${formatNumber(m.running_balance)}</strong></td>
        `;

        els.movesList.appendChild(tr);
    });
}

function updateMovesPaginationInfo() {
    els.movesResultsCount.textContent = formatNumber(state.movesTotalItems);
    els.movesTotalResults.textContent = formatNumber(state.movesTotalItems);

    if (state.movesTotalItems === 0) {
        els.movesPageStart.textContent = '0';
        els.movesPageEnd.textContent = '0';
    } else {
        const start = ((state.movesPage - 1) * state.movesPerPage) + 1;
        const end = Math.min(state.movesPage * state.movesPerPage, state.movesTotalItems);
        els.movesPageStart.textContent = formatNumber(start);
        els.movesPageEnd.textContent = formatNumber(end);
    }
}

function renderMovesPaginationControls() {
    els.movesBtnPrev.disabled = state.movesPage <= 1;
    els.movesBtnNext.disabled = state.movesPage >= state.movesTotalPages;

    els.movesPageNumbers.innerHTML = '';
    if (state.movesTotalPages <= 1) return;

    let startPage = Math.max(1, state.movesPage - 2);
    let endPage = Math.min(state.movesTotalPages, startPage + 4);

    if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
    }

    if (startPage > 1) {
        addMovesPageButton(1);
        if (startPage > 2) addEllipsis(els.movesPageNumbers);
    }

    for (let i = startPage; i <= endPage; i++) {
        addMovesPageButton(i);
    }

    if (endPage < state.movesTotalPages) {
        if (endPage < state.movesTotalPages - 1) addEllipsis(els.movesPageNumbers);
        addMovesPageButton(state.movesTotalPages);
    }
}

function addMovesPageButton(pageNum) {
    const btn = document.createElement('button');
    btn.className = `page-btn ${pageNum === state.movesPage ? 'active' : ''}`;
    btn.textContent = pageNum;
    if (pageNum !== state.movesPage) {
        btn.onclick = () => {
            state.movesPage = pageNum;
            fetchMoves();
        };
    }
    els.movesPageNumbers.appendChild(btn);
}

// Modal handling
function openModal(product, sourceIndex) {
    // Build browsable list from the current tab (make a COPY so we can extend it)
    if (state.currentTab === 'products') {
        state.modalList = [...state.products];
        state.modalTotalItems = state.totalItems;
    } else if (state.currentTab === 'moves') {
        state.modalList = state.moves.map(m => ({
            sku: m.sku, part_code: m.part_code, name_eng: m.name_eng, name_thai: m.name_thai,
            brand: m.brand, suffix: m.suffix || '-', qty: m.qty, sale_price: m.price, thumbnail: m.thumbnail
        }));
        state.modalTotalItems = state.movesTotalItems;
    } else if (state.currentTab === 'flags') {
        state.modalList = [...state.flags];
        state.modalTotalItems = state.flagsTotalItems;
    } else if (state.currentTab === 'photo-flags') {
        state.modalList = [...state.photoFlags];
        state.modalTotalItems = state.photoFlagsTotalItems;
    } else {
        state.modalList = [];
        state.modalTotalItems = 0;
    }
    state.modalIndex = typeof sourceIndex === 'number' ? sourceIndex : -1;
    // Track how many pages are already loaded into modalList
    state.modalPagesLoaded = state.currentTab === 'products' ? state.page
        : state.currentTab === 'moves' ? state.movesPage
            : state.currentTab === 'flags' ? state.flagsPage
                : state.currentTab === 'photo-flags' ? state.photoFlagsPage : 1;
    state.modalLoading = false;

    if (!_handlingPopstate) navPush('product/' + encodeURIComponent(product.sku));
    openModalInternal(product);
    updateModalNav();
}

// Highlight search term in text (returns HTML string)
function highlightSearch(text, searchTerm) {
    if (!searchTerm || !text) return escapeHtml(text || '');
    const escaped = escapeHtml(text);
    const escapedTerm = escapeHtml(searchTerm);
    const regex = new RegExp(`(${escapeRegex(escapedTerm)})`, 'gi');
    return escaped.replace(regex, '<mark class="search-hl">$1</mark>');
}

async function openModalInternal(product) {
    // ── Flag warning banner at top of modal ─────────────────────────────
    const existingBanner = document.querySelector('.modal-flag-banner');
    if (existingBanner) existingBanner.remove();

    if (product.flag_type) {
        const flagLabels = {
            'out_of_stock': '⚠️ สินค้าหมด (ระบบยังแสดง)',
            'less_than': '⚠️ สินค้าจริงน้อยกว่าระบบ',
            'more_than': 'ℹ️ สินค้าจริงมากกว่าระบบ'
        };
        const flagNote = product.flag_note ? `<div class="modal-flag-banner-note">${escapeHtml(product.flag_note)}</div>` : '';
        const flagDate = product.flagged_at ? `<div class="modal-flag-banner-date">Flagged: ${formatBuddhistDate(product.flagged_at, true)}</div>` : '';
        const banner = document.createElement('div');
        banner.className = `modal-flag-banner ${product.flag_type}`;
        banner.innerHTML = `
            <div class="modal-flag-banner-icon">🚩</div>
            <div class="modal-flag-banner-text">
                <div class="modal-flag-banner-label">${flagLabels[product.flag_type] || product.flag_type}</div>
                ${flagNote}
                ${flagDate}
            </div>
        `;
        const modalBody = els.modal.querySelector('.modal-body');
        modalBody.insertBefore(banner, modalBody.firstChild);
    }

    // Populate details
    els.modalSuffixLabel.textContent = product.suffix || '-'; // Display the short code like G, C, R, L
    els.modalSuffixLabel.className = `sku-badge type-${(product.suffix || '').toLowerCase()}`;
    els.modalSuffixLabel.style.color = 'white'; // Override text color to white for contrast

    // Get the active search term for highlighting
    const searchTerm = state.search || '';

    els.modalPartCode.innerHTML = highlightSearch(product.part_code || product.sku, searchTerm);
    els.modalNameEng.innerHTML = highlightSearch(product.name_eng || 'No English Description', searchTerm);
    els.modalNameThai.innerHTML = highlightSearch(product.name_thai || 'No Thai Description', searchTerm);
    els.modalBrand.textContent = product.brand || '-';

    // Restricting missed properties
    els.modalSize.textContent = product.size || '-';
    // Use on_hand_qty from CSV, fallback to qty
    const displayQty = product.on_hand_qty !== undefined ? product.on_hand_qty : product.qty;
    els.modalQty.textContent = formatNumber(displayQty);
    els.modalPrice.textContent = product.sale_price ? formatPrice(product.sale_price) : '-';
    els.modalLocation.textContent = product.locations || '-';

    els.modalQty.className = `value qty-value ${displayQty <= 5 ? 'qty-low' : ''}`;

    // Manage Report button state
    state.currentModalSku = product.sku;
    els.btnReportIssue.classList.remove('hidden');
    els.reportDialog.classList.add('hidden');
    els.reportNote.value = '';
    els.flagTypeRadios.forEach(r => r.checked = false);

    // ── Photo flag UI state in modal ────────────────────────────────
    if (els.photoFlagDialog) els.photoFlagDialog.classList.add('hidden');
    if (els.photoFlagNote) els.photoFlagNote.value = '';

    // Update photo-flag button text and disabled state based on flag state
    if (els.btnPhotoFlag) {
        if (product.photo_flag || product.photo_flag_id) {
            els.btnPhotoFlag.innerHTML = '✅ แจ้งถ่ายรูปเพิ่มแล้ว';
            els.btnPhotoFlag.disabled = true;
            els.btnPhotoFlag.style.opacity = '0.5';
            els.btnPhotoFlag.style.cursor = 'not-allowed';
        } else {
            els.btnPhotoFlag.innerHTML = '📷 ต้องการรูปเพิ่ม';
            els.btnPhotoFlag.disabled = false;
            els.btnPhotoFlag.style.opacity = '1';
            els.btnPhotoFlag.style.cursor = 'pointer';
        }
    }

    // ── Photo flag banner at top of modal ────────────────────────────
    const existingPhotoBanner = document.querySelector('.modal-photo-flag-banner');
    if (existingPhotoBanner) existingPhotoBanner.remove();

    if (product.photo_flag || product.photo_flag_id) {
        const photoNote = product.photo_flag_note ? `<div style="font-size: 0.8rem; margin-top: 0.2rem; opacity: 0.8;">${escapeHtml(product.photo_flag_note)}</div>` : '';
        const photoBy = product.photo_flagged_by ? `โดย ${escapeHtml(product.photo_flagged_by)}` : '';
        const photoDate = product.photo_flagged_at ? formatBuddhistDate(product.photo_flagged_at, true) : '';
        const infoLine = (photoBy || photoDate)
            ? `<div style="font-size: 0.75rem; opacity: 0.7; margin-top: 0.15rem;">แจ้ง${photoBy ? ' ' + photoBy : ''}${photoDate ? ' • ' + photoDate : ''}</div>`
            : '';
        const photoBanner = document.createElement('div');
        photoBanner.className = 'modal-photo-flag-banner';
        photoBanner.innerHTML = `
            <div style="display: flex; align-items: center; gap: 0.5rem;">
                <span style="font-size: 1.3rem;">📷</span>
                <div>
                    <div style="font-weight: 600;">ต้องการรูปเพิ่ม</div>
                    ${photoNote}
                    ${infoLine}
                </div>
            </div>
        `;
        const modalBody = els.modal.querySelector('.modal-body');
        const existingStockBanner = modalBody.querySelector('.modal-flag-banner');
        if (existingStockBanner) {
            existingStockBanner.after(photoBanner);
        } else {
            modalBody.insertBefore(photoBanner, modalBody.firstChild);
        }
    }

    // Initial image load
    if (product.thumbnail) {
        els.modalMainImg.src = `/images/${product.thumbnail}`;
        els.modalMainImg.style.display = 'block';
        els.mainImageTrashBtn.classList.remove('hidden');
    } else {
        els.modalMainImg.style.display = 'none';
        els.modalMainImg.src = '';
        els.mainImageTrashBtn.classList.add('hidden');
    }
    els.modalThumbnails.innerHTML = '';
    // Reset caption bar
    const captionBar = document.getElementById('image-caption-bar');
    if (captionBar) captionBar.classList.add('hidden');

    // Show modal
    els.modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden'; // Prevent background scrolling

    // Always fetch images (even with 0 image_count, custom images may exist)
    const images = await fetchProductImages(product.sku);
    els.modalThumbnails.innerHTML = ''; // Clear loading

    if (images && images.length > 0) {
        const firstImg = images[0];
        const firstUrl = firstImg.url || (firstImg.startsWith?.('/') ? firstImg : `/images/${firstImg}`);
        els.modalMainImg.src = firstUrl;
        els.modalMainImg.style.display = 'block';
        els.mainImageTrashBtn.classList.remove('hidden');

        images.forEach((imgData, idx) => {
            insertThumbnail(imgData, idx === 0);
        });
    } else if (!product.thumbnail) {
        // No images at all
        els.modalMainImg.style.display = 'none';
        els.modalMainImg.src = '';
        els.mainImageTrashBtn.classList.add('hidden');
    }

    // Show upload button if user has permission
    const uploadControls = document.getElementById('custom-image-controls');
    if (uploadControls) {
        if (_galleryPermissions.can_upload) {
            uploadControls.classList.remove('hidden');
        } else {
            uploadControls.classList.add('hidden');
        }
    }

    // Add hidden images toggle below thumbnails
    insertHiddenToggle();

    // Fetch and render stock history
    els.modalHistory.innerHTML = '<p class="text-muted">Loading history...</p>';
    fetchAndRenderHistory(product.sku);

    // Fetch and render archived history
    if (els.modalArchivedHistory) {
        els.modalArchivedHistory.innerHTML = '<p class="text-muted">กำลังโหลดประวัติเคลื่อนไหว...</p>';
        fetchAndRenderArchivedHistory(product.sku);
    }

    // Fetch and render possible titles
    els.modalPossibleTitles.innerHTML = '<p class="text-muted" style="font-size:0.9rem;">Loading titles...</p>';
    fetchAndRenderTitles(product.sku);
}

function insertThumbnail(imgData, isActive) {
    // Handle both old format (string path) and new format (object with url/source/etc.)
    const isObj = typeof imgData === 'object' && imgData !== null;
    const imgPath = isObj ? imgData.url : imgData;
    // Use thumb_url for the gallery strip (small 300px version, loads fast)
    const thumbPath = isObj ? (imgData.thumb_url || imgData.url) : imgData;
    const source = isObj ? (imgData.source || '') : '';
    const filename = isObj ? (imgData.filename || imgPath.split('/').pop()) : imgPath.split('/').pop();
    const comment = isObj ? (imgData.comment || '') : '';
    const uploadedBy = isObj ? (imgData.uploaded_by || '') : '';
    const uploadedAt = isObj ? (imgData.uploaded_at || '') : '';

    // Full-size URL for main image display
    const fullSrc = imgPath.startsWith('/') ? imgPath : `/images/${imgPath}`;
    // Small thumbnail URL for the strip
    const thumbSrc = thumbPath.startsWith('/') ? thumbPath : `/images/${thumbPath}`;

    // Wrapper for positioning badge/delete button
    const wrapper = document.createElement('div');
    wrapper.className = 'gallery-thumb-wrapper';
    if (source === 'custom') wrapper.classList.add('custom-thumb');

    const img = document.createElement('img');
    img.src = thumbSrc;  // Use small thumbnail for the strip
    img.className = `gallery-thumb ${isActive ? 'active' : ''}`;
    if (comment) img.title = comment;

    img.onclick = () => {
        // Update main image with FULL-SIZE version
        els.modalMainImg.src = fullSrc;
        els.modalMainImg.dataset.filename = filename;
        els.modalMainImg.dataset.source = source;

        // Update active state
        document.querySelectorAll('.gallery-thumb').forEach(el => el.classList.remove('active'));
        img.classList.add('active');

        // Update caption bar
        _updateCaptionBar(comment, uploadedBy, uploadedAt, source);
    };

    // Source badge (custom images only now)
    if (source === 'custom') {
        const badge = document.createElement('span');
        badge.className = `gallery-source-badge source-${source}`;
        badge.textContent = '📷';
        wrapper.appendChild(badge);
    }

    wrapper.appendChild(img);

    // If this is the active (first) thumbnail, set tracking data
    if (isActive) {
        els.modalMainImg.dataset.filename = filename;
        els.modalMainImg.dataset.source = source;
        _updateCaptionBar(comment, uploadedBy, uploadedAt, source);
    }

    els.modalThumbnails.appendChild(wrapper);
}

function _updateCaptionBar(comment, uploadedBy, uploadedAt, source) {
    const captionBar = document.getElementById('image-caption-bar');
    const captionText = document.getElementById('image-caption-text');
    const captionMeta = document.getElementById('image-caption-meta');
    if (!captionBar) return;

    if (comment || (source === 'custom' && uploadedBy)) {
        captionBar.classList.remove('hidden');
        captionText.textContent = comment || '';

        let metaParts = [];
        if (uploadedBy) metaParts.push(`by ${uploadedBy}`);
        if (uploadedAt) {
            try {
                const d = new Date(uploadedAt);
                metaParts.push(d.toLocaleDateString('th-TH'));
            } catch (e) {
                metaParts.push(uploadedAt);
            }
        }

        captionMeta.textContent = metaParts.join(' · ');
    } else {
        captionBar.classList.add('hidden');
    }
}

async function hideImage(filename) {
    if (!state.currentModalSku) return;
    if (!confirm(`ส่งรูปภาพ "${filename}" ไปถังขยะ?\nSend this image to the Recycle Bin?`)) return;

    try {
        const res = await fetch(`/api/products/${encodeURIComponent(state.currentModalSku)}/images/hide`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename })
        });
        const data = await res.json();
        if (data.success) {
            refreshGallery();
        } else {
            alert('Error: ' + data.message);
        }
    } catch (err) {
        console.error('Error hiding image:', err);
        alert('Failed to hide image');
    }
}

async function unhideImage(hiddenName) {
    if (!state.currentModalSku) return;

    try {
        const res = await fetch(`/api/products/${encodeURIComponent(state.currentModalSku)}/images/unhide`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: hiddenName })
        });
        const data = await res.json();
        if (data.success) {
            refreshGallery();
        } else {
            alert('Error: ' + data.message);
        }
    } catch (err) {
        console.error('Error restoring image:', err);
        alert('Failed to restore image');
    }
}

async function permanentDeleteImage(hiddenName, wrapperEl) {
    if (!state.currentModalSku) return;
    const originalName = hiddenName.replace(/^_hidden_/, '');
    if (!confirm(`ลบรูปภาพ "${originalName}" ถาวร?\nPermanently delete this image? This cannot be undone.`)) return;

    try {
        const res = await fetch(`/api/products/${encodeURIComponent(state.currentModalSku)}/images/permanent-delete`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename: hiddenName })
        });
        const data = await res.json();
        if (data.success) {
            // Just remove this item from the DOM — keep recycle bin open
            if (wrapperEl) wrapperEl.remove();
        } else {
            alert('Error: ' + (data.message || 'Unknown error'));
        }
    } catch (err) {
        console.error('Error permanently deleting image:', err);
        alert('Failed to permanently delete image');
    }
}

async function refreshGallery() {
    if (!state.currentModalSku) return;

    const images = await fetchProductImages(state.currentModalSku);
    els.modalThumbnails.innerHTML = '';

    if (images && images.length > 0) {
        const firstImg = images[0];
        const firstUrl = typeof firstImg === 'object' ? firstImg.url : firstImg;
        const src = firstUrl.startsWith('/') ? firstUrl : `/images/${firstUrl}`;
        els.modalMainImg.src = src;
        els.modalMainImg.style.display = 'block';
        els.mainImageTrashBtn.classList.remove('hidden');
        images.forEach((imgData, idx) => {
            insertThumbnail(imgData, idx === 0);
        });
    } else {
        els.modalMainImg.style.display = 'none';
        els.modalMainImg.src = '';
        els.mainImageTrashBtn.classList.add('hidden');
    }

    // Show/hide upload button based on permissions
    const uploadControls = document.getElementById('custom-image-controls');
    if (uploadControls) {
        if (_galleryPermissions.can_upload) {
            uploadControls.classList.remove('hidden');
        } else {
            uploadControls.classList.add('hidden');
        }
    }

    // Re-insert hidden toggle
    insertHiddenToggle();
}

// ─── Custom Image Upload ────────────────────────────────────────────────────

let _pendingUploadFiles = [];  // Array of File objects (accumulates across multiple picks)

function _setupUploadHandlers() {
    const uploadBtn = document.getElementById('btn-upload-photo');
    const fileInput = document.getElementById('custom-image-input');
    const cancelBtn = document.getElementById('btn-cancel-upload');
    const confirmBtn = document.getElementById('btn-confirm-upload');
    const addMoreBtn = document.getElementById('btn-add-more-photos');
    const uploadDialog = document.getElementById('upload-dialog');

    if (!uploadBtn || !fileInput) return;

    let _isAddingMore = false;  // true when user taps "เพิ่มรูป"

    // Helper: add a single file's preview thumbnail to the preview area (with delete button)
    function _addPreviewThumb(file) {
        const previewArea = document.getElementById('upload-preview-area');
        const thumb = document.createElement('div');
        thumb.className = 'upload-preview-thumb';
        const img = document.createElement('img');
        const blobUrl = URL.createObjectURL(file);
        img.src = blobUrl;
        img.onload = () => URL.revokeObjectURL(blobUrl); // Free memory after render
        thumb.appendChild(img);
        // Delete button to remove this photo before uploading
        const delBtn = document.createElement('button');
        delBtn.className = 'upload-preview-delete-btn';
        delBtn.type = 'button';
        delBtn.title = 'ลบรูปนี้ / Remove';
        delBtn.textContent = '✕';
        delBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const idx = _pendingUploadFiles.indexOf(file);
            if (idx > -1) _pendingUploadFiles.splice(idx, 1);
            thumb.remove();
            _updateUploadLabel();
            // If no files left, hide the upload dialog
            if (_pendingUploadFiles.length === 0) {
                uploadDialog.classList.add('hidden');
            }
        });
        thumb.appendChild(delBtn);
        const name = document.createElement('span');
        name.className = 'upload-preview-name';
        name.textContent = file.name;
        thumb.appendChild(name);
        previewArea.appendChild(thumb);
    }

    // Helper: update the upload button count label
    function _updateUploadLabel() {
        const count = _pendingUploadFiles.length;
        confirmBtn.querySelector('.upload-count')?.remove();
        if (count > 0) {
            const badge = document.createElement('span');
            badge.className = 'upload-count';
            badge.textContent = ` (${count} รูป)`;
            confirmBtn.appendChild(badge);
        }
    }

    // Upload button → trigger file input (fresh upload)
    uploadBtn.addEventListener('click', () => {
        _isAddingMore = false;
        fileInput.click();
    });

    // File input change → show preview or append
    fileInput.addEventListener('change', (e) => {
        const files = e.target.files;
        if (!files || files.length === 0) return;

        if (!_isAddingMore) {
            // Fresh upload: reset everything
            _pendingUploadFiles = [];
            document.getElementById('upload-preview-area').innerHTML = '';
            document.getElementById('upload-comment').value = '';
        }

        // Append new files
        Array.from(files).forEach(file => {
            _pendingUploadFiles.push(file);
            _addPreviewThumb(file);
        });

        _updateUploadLabel();
        uploadDialog.classList.remove('hidden');
        _isAddingMore = false;
        fileInput.value = '';  // Reset so same file can be selected again
    });

    // "เพิ่มรูป / Add More" button → re-open file input to add more photos
    if (addMoreBtn) {
        addMoreBtn.addEventListener('click', () => {
            _isAddingMore = true;
            fileInput.click();
        });
    }

    cancelBtn.addEventListener('click', () => {
        _pendingUploadFiles = [];
        fileInput.value = '';
        uploadDialog.classList.add('hidden');
        _updateUploadLabel();
    });

    confirmBtn.addEventListener('click', async () => {
        if (_pendingUploadFiles.length === 0 || !state.currentModalSku) return;

        const comment = document.getElementById('upload-comment').value.trim();
        const progressBar = document.getElementById('upload-progress');
        const progressBarInner = document.getElementById('upload-progress-bar');

        confirmBtn.disabled = true;
        if (addMoreBtn) addMoreBtn.disabled = true;
        progressBar.classList.remove('hidden');
        progressBarInner.style.width = '30%';

        try {
            const formData = new FormData();
            Array.from(_pendingUploadFiles).forEach(file => {
                formData.append('files', file);
            });
            if (comment) formData.append('comment', comment);

            progressBarInner.style.width = '60%';

            const res = await fetch(`/api/products/${state.currentModalSku}/images/upload`, {
                method: 'POST',
                body: formData,
            });
            const data = await res.json();

            progressBarInner.style.width = '100%';

            if (data.success) {
                console.log(`[Upload] Uploaded ${data.uploaded.length} image(s)`);
                if (data.errors && data.errors.length > 0) {
                    alert('Some files had errors:\n' + data.errors.join('\n'));
                }
            } else {
                alert('Upload failed: ' + (data.error || data.errors?.join('\n') || 'Unknown error'));
            }
        } catch (err) {
            console.error('Upload error:', err);
            alert('Upload failed: ' + err.message);
        } finally {
            _pendingUploadFiles = [];
            fileInput.value = '';
            uploadDialog.classList.add('hidden');
            confirmBtn.disabled = false;
            if (addMoreBtn) addMoreBtn.disabled = false;
            progressBar.classList.add('hidden');
            progressBarInner.style.width = '0%';
            // Refresh gallery to show new images
            refreshGallery();
        }
    });
}

async function deleteCustomImage(filename) {
    if (!state.currentModalSku) return;
    if (!confirm(`ลบรูปภาพ "${filename}" ?\nDelete this photo permanently?`)) return;

    try {
        const res = await fetch(`/api/products/${state.currentModalSku}/images/custom`, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename }),
        });
        const data = await res.json();
        if (data.success) {
            refreshGallery();
        } else {
            alert('Error: ' + data.message);
        }
    } catch (err) {
        console.error('Error deleting custom image:', err);
        alert('Failed to delete image');
    }
}

async function loadHiddenImages() {
    if (!state.currentModalSku) return;

    try {
        const res = await fetch(`/api/products/${encodeURIComponent(state.currentModalSku)}/images/hidden`);
        const hidden = await res.json();

        // Remove any existing hidden images from display
        document.querySelectorAll('.gallery-thumb-wrapper.hidden-wrapper').forEach(el => el.remove());

        if (!hidden || hidden.length === 0) return;

        hidden.forEach(item => {
            const wrapper = document.createElement('div');
            wrapper.className = 'gallery-thumb-wrapper hidden-wrapper';

            const img = document.createElement('img');
            img.src = item.preview;
            img.className = 'gallery-thumb hidden-img';
            img.title = `Hidden: ${item.original_name}`;

            img.onerror = () => {
                // hidden file can't be served directly, use a placeholder style
                img.style.background = 'repeating-linear-gradient(45deg, rgba(255,255,255,0.05), rgba(255,255,255,0.05) 4px, transparent 4px, transparent 8px)';
                img.removeAttribute('src');
            };

            // Restore button
            const restoreBtn = document.createElement('button');
            restoreBtn.className = 'gallery-restore-btn';
            restoreBtn.title = 'กู้คืนรูปภาพ / Restore';
            restoreBtn.innerHTML = '↩';
            restoreBtn.onclick = (e) => {
                e.stopPropagation();
                unhideImage(item.hidden_name);
            };

            wrapper.appendChild(img);
            wrapper.appendChild(restoreBtn);

            // Permanent delete button (admin only)
            const isAdmin = _currentUser && _currentUser.role === 'admin';
            if (isAdmin) {
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'gallery-permanent-delete-btn';
                deleteBtn.title = 'ลบถาวร / Permanently Delete';
                deleteBtn.innerHTML = '✕';
                deleteBtn.onclick = (e) => {
                    e.stopPropagation();
                    permanentDeleteImage(item.hidden_name, wrapper);
                };
                wrapper.appendChild(deleteBtn);
            }

            els.modalThumbnails.appendChild(wrapper);
        });
    } catch (err) {
        console.error('Error loading hidden images:', err);
    }
}

function insertHiddenToggle() {
    // Remove existing toggle
    const existing = els.modalThumbnails.parentElement.querySelector('.gallery-hidden-toggle');
    if (existing) existing.remove();

    const toggle = document.createElement('button');
    toggle.className = 'gallery-hidden-toggle';
    toggle.innerHTML = '🗑 ถังขยะ / Recycle Bin';
    let showing = false;

    toggle.onclick = async () => {
        showing = !showing;
        if (showing) {
            toggle.innerHTML = '🗑 ซ่อนถังขยะ / Hide Recycle Bin';
            await loadHiddenImages();
        } else {
            toggle.innerHTML = '🗑 ถังขยะ / Recycle Bin';
            document.querySelectorAll('.gallery-thumb-wrapper.hidden-wrapper').forEach(el => el.remove());
        }
    };

    // Insert after thumbnail strip
    els.modalThumbnails.parentElement.appendChild(toggle);
}

function closeModal() {
    if (location.hash.startsWith('#product/')) {
        history.back(); // Triggers popstate → handleNavigation → closeModalInternal
    } else {
        closeModalInternal();
    }
}

function closeModalInternal() {
    els.modal.classList.add('hidden');
    document.body.style.overflow = 'auto'; // Restore background scrolling
}

// Modal navigation (prev/next product in list, with auto-loading across pages)
async function navigateModal(direction) {
    if (!state.modalList || state.modalList.length === 0 || state.modalIndex < 0) return;
    if (state.modalLoading) return; // Prevent double-fetching

    const newIndex = state.modalIndex + direction;

    // Going past the end? Try to load the next page
    if (newIndex >= state.modalList.length) {
        const loaded = await loadMoreModalItems();
        if (!loaded || newIndex >= state.modalList.length) return; // No more items
    }

    if (newIndex < 0) return; // Can't go before the first item

    state.modalIndex = newIndex;
    const product = state.modalList[newIndex];
    openModalInternal(product);
    updateModalNav();
}

async function loadMoreModalItems() {
    const tab = state.currentTab;
    const nextPage = state.modalPagesLoaded + 1;
    const totalPages = tab === 'products' ? state.totalPages
        : tab === 'moves' ? state.movesTotalPages
            : tab === 'flags' ? state.flagsTotalPages : 0;

    if (nextPage > totalPages) return false;

    state.modalLoading = true;
    els.modalNavIndicator.textContent = '...';

    try {
        let url, items;

        if (tab === 'products') {
            const params = new URLSearchParams({
                search: state.search, brand: state.brand, suffix: state.suffix,
                active_days: state.activeDays, sort: state.sort, dir: state.sortDir,
                page: nextPage, per_page: state.perPage
            });
            const res = await fetch(`/api/products?${params}`);
            const data = await res.json();
            items = data.items || [];
        } else if (tab === 'moves') {
            const params = new URLSearchParams({
                search: state.movesSearch, type: state.movesType,
                sort: state.movesSort, dir: state.movesSortDir,
                page: nextPage, per_page: state.movesPerPage
            });
            const res = await fetch(`/api/moves?${params}`);
            const data = await res.json();
            items = (data.items || []).map(m => ({
                sku: m.sku, part_code: m.part_code, name_eng: m.name_eng, name_thai: m.name_thai,
                brand: m.brand, suffix: m.suffix || '-', qty: m.qty, sale_price: m.price, thumbnail: m.thumbnail
            }));
        } else if (tab === 'flags') {
            const params = new URLSearchParams({
                search: state.flagsSearch, sort: state.flagsSort, dir: state.flagsSortDir,
                page: nextPage, per_page: 50
            });
            const res = await fetch(`/api/flags?${params}`);
            const data = await res.json();
            items = data.items || [];
        }

        if (items && items.length > 0) {
            state.modalList.push(...items);
            state.modalPagesLoaded = nextPage;
            state.modalLoading = false;
            return true;
        }
    } catch (err) {
        console.error('Error loading more modal items:', err);
    }

    state.modalLoading = false;
    return false;
}

function updateModalNav() {
    const total = state.modalTotalItems || state.modalList.length;
    if (!state.modalList || total <= 1 || state.modalIndex < 0) {
        els.modalNavControls.classList.add('hidden');
        return;
    }

    els.modalNavControls.classList.remove('hidden');
    els.modalNavIndicator.textContent = `${formatNumber(state.modalIndex + 1)} / ${formatNumber(total)}`;
    els.modalPrevBtn.disabled = state.modalIndex <= 0;
    els.modalNextBtn.disabled = state.modalIndex >= total - 1;
}

// Possible Titles
let cachedEngineList = null;
let cachedForkliftBrands = null;

async function getEngineList() {
    if (cachedEngineList) return cachedEngineList;
    try {
        const res = await fetch('/api/engine-list');
        cachedEngineList = await res.json();
    } catch (e) {
        cachedEngineList = [];
    }
    return cachedEngineList;
}

async function getForkliftBrands() {
    if (cachedForkliftBrands) return cachedForkliftBrands;
    try {
        const res = await fetch('/api/forklift-brands');
        cachedForkliftBrands = await res.json();
    } catch (e) {
        cachedForkliftBrands = [];
    }
    return cachedForkliftBrands;
}

function escapeHtml(str) {
    return str.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escapeRegex(str) {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// Highlight colors:
// Engine models + "engine" word = amber/orange
const HL_ENGINE = 'background:#f59e0b;color:#000;padding:0 2px;border-radius:3px;font-weight:600;';
// FG/FD/FB chunks = teal/cyan
const HL_FGFDFB = 'background:#06b6d4;color:#000;padding:0 2px;border-radius:3px;font-weight:600;';
// Forklift brands = purple/violet
const HL_BRAND = 'background:#a78bfa;color:#000;padding:0 2px;border-radius:3px;font-weight:600;';

function highlightTitle(text, engineModels, forkliftBrands) {
    let safe = escapeHtml(text);

    // We need to apply highlights in a specific order using separate passes
    // to assign different colors. We use placeholder tokens to avoid nested replacements.

    // Pass 1: FG/FD/FB chunks (teal) - most specific word-level match first
    const fgPattern = /(\b\S*(?:FG|FD|FB)\S*\b)/gi;
    safe = safe.replace(fgPattern, `<mark style="${HL_FGFDFB}">$1</mark>`);

    // Pass 2: Engine models + "engine" word (amber) - but skip already marked content
    if (engineModels.length > 0) {
        const sorted = [...engineModels].sort((a, b) => b.length - a.length);
        const enginePatterns = ['\\bengine\\b'];
        sorted.forEach(m => {
            enginePatterns.push('\\b' + escapeRegex(m) + '\\b');
        });
        const engineRegex = new RegExp('(' + enginePatterns.join('|') + ')', 'gi');
        // Only replace text NOT already inside a <mark> tag
        safe = safe.replace(/(<mark[^>]*>.*?<\/mark>)|([^<]*)/gi, (fullMatch, marked, unmarked) => {
            if (marked) return marked; // already highlighted, skip
            if (!unmarked) return fullMatch;
            return unmarked.replace(engineRegex, `<mark style="${HL_ENGINE}">$1</mark>`);
        });
    }

    // Pass 3: Forklift brands (purple) - skip already marked content
    if (forkliftBrands.length > 0) {
        const sortedBrands = [...forkliftBrands].sort((a, b) => b.length - a.length);
        const brandPatterns = sortedBrands.map(b => '\\b' + escapeRegex(b) + '\\b');
        const brandRegex = new RegExp('(' + brandPatterns.join('|') + ')', 'gi');
        safe = safe.replace(/(<mark[^>]*>.*?<\/mark>)|([^<]*)/gi, (fullMatch, marked, unmarked) => {
            if (marked) return marked;
            if (!unmarked) return fullMatch;
            return unmarked.replace(brandRegex, `<mark style="${HL_BRAND}">$1</mark>`);
        });
    }

    return safe;
}

async function fetchAndRenderTitles(sku) {
    try {
        const [response, engineModels, forkliftBrands] = await Promise.all([
            fetch(`/api/products/${encodeURIComponent(sku)}/titles`),
            getEngineList(),
            getForkliftBrands()
        ]);
        if (!response.ok) throw new Error('Failed to fetch titles');

        const titles = await response.json();

        if (!titles || titles.length === 0) {
            els.modalPossibleTitles.innerHTML = '<p class="text-muted" style="font-size:0.9rem;">No additional titles found in database.</p>';
            return;
        }

        els.modalPossibleTitles.innerHTML = '';
        titles.forEach(title => {
            const tag = document.createElement('div');
            tag.className = 'title-tag';
            tag.style.cssText = `
                background: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: var(--text-secondary);
                padding: 0.35rem 0.75rem;
                border-radius: var(--radius-md);
                font-size: 0.85rem;
                line-height: 1.4;
                max-width: 100%;
                word-break: break-word;
            `;
            tag.innerHTML = highlightTitle(title, engineModels, forkliftBrands);
            els.modalPossibleTitles.appendChild(tag);
        });
    } catch (err) {
        console.error("Error fetching titles:", err);
        els.modalPossibleTitles.innerHTML = '<p class="text-error" style="font-size:0.9rem;">Failed to load possible titles.</p>';
    }
}

// Stock History
async function fetchAndRenderHistory(sku) {
    try {
        const res = await fetch(`/api/products/${encodeURIComponent(sku)}/history`);
        const history = await res.json();

        if (!history || history.length === 0) {
            els.modalHistory.innerHTML = '<p class="text-muted">No history data available for this product.</p>';
            return;
        }

        let html = `<table class="history-table">
            <thead>
                <tr>
                    <th>Date</th>
                    <th class="text-right">Qty</th>
                    <th class="text-right">Change</th>
                    <th>Type</th>
                </tr>
            </thead>
            <tbody>`;

        // Show oldest first
        for (let i = 0; i < history.length; i++) {
            const h = history[i];
            let changeHtml = '-';
            let labelHtml = '';

            if (h.change !== null) {
                if (h.change < 0) {
                    changeHtml = `<span class="change-out">${h.change}</span>`;
                    labelHtml = '<span class="label-out">Out</span>';
                } else if (h.change > 0) {
                    changeHtml = `<span class="change-in">+${h.change}</span>`;
                    labelHtml = '<span class="label-in">In</span>';
                } else {
                    changeHtml = '<span class="text-muted">0</span>';
                }
            }

            // Format date to Buddhist Era
            const formattedDate = formatBuddhistDate(h.date);

            html += `<tr>
                <td>${formattedDate}</td>
                <td class="text-right">${formatNumber(h.qty)}</td>
                <td class="text-right">${changeHtml}</td>
                <td>${labelHtml}</td>
            </tr>`;
        }

        html += '</tbody></table>';
        els.modalHistory.innerHTML = html;
    } catch (err) {
        console.error('Error fetching history:', err);
        els.modalHistory.innerHTML = '<p class="text-muted">Failed to load history.</p>';
    }
}

async function fetchAndRenderArchivedHistory(sku) {
    try {
        const res = await fetch(`/api/products/${encodeURIComponent(sku)}/archived-history`);
        const history = await res.json();

        if (!history || history.length === 0) {
            els.modalArchivedHistory.innerHTML = '<p class="text-muted">ไม่มีประวัติเคลื่อนไหว</p>';
            if (archivedChartInstance) {
                archivedChartInstance.destroy();
                archivedChartInstance = null;
            }
            if (els.archivedHistoryChart) {
                els.archivedHistoryChart.style.display = 'none';
            }
            // Hide sales-by-year when no data
            if (els.modalSalesByYear) {
                els.modalSalesByYear.classList.add('hidden');
            }
            return;
        }

        if (els.archivedHistoryChart) {
            els.archivedHistoryChart.style.display = 'block';
        }

        let html = `<table class="history-table">
            <thead>
                <tr>
                    <th>วันที่</th>
                    <th>เอกสาร</th>
                    <th>ประเภท</th>
                    <th>จาก/ให้</th>
                    <th class="text-right">ราคา/หน่วย</th>
                    <th class="text-right">รับเข้า</th>
                    <th class="text-right">จ่ายออก</th>
                    <th class="text-right">ยอดคงเหลือ</th>
                </tr>
            </thead>
            <tbody>`;

        for (let i = 0; i < history.length; i++) {
            const h = history[i];

            let outHtml = h.qty_out > 0 ? `<span class="change-out">${formatNumber(h.qty_out)}</span>` : '<span class="text-muted">0</span>';
            let inHtml = h.qty_in > 0 ? `<span class="change-in">+${formatNumber(h.qty_in)}</span>` : '<span class="text-muted">0</span>';

            // Format date tracking
            let formattedDate = formatBuddhistDate(h.date);

            html += `<tr>
                <td style="white-space:nowrap;">${formattedDate}</td>
                <td>${h.doc_ref || '-'}</td>
                <td>${getCategoryThai(h.category_name)}</td>
                <td>${h.from_to ? `<span class="from-to-hover-wrap"><a href="#" class="from-to-link" data-customer-code="${escapeHtml(h.from_to)}" style="color: #60a5fa; text-decoration: none; cursor: pointer;" onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">${escapeHtml(h.from_to)}</a>${h.from_to_name ? `<span class="from-to-bubble">${escapeHtml(h.from_to_name)}</span>` : ''}</span>` : '-'}</td>
                <td class="text-right">${h.unit_price ? formatPrice(h.unit_price) : '-'}</td>
                <td class="text-right">${inHtml}</td>
                <td class="text-right">${outHtml}</td>
                <td class="text-right"><strong>${formatNumber(h.running_balance)}</strong></td>
            </tr>`;
        }

        html += '</tbody></table>';
        els.modalArchivedHistory.innerHTML = html;

        // Attach click handlers for from/to customer links
        els.modalArchivedHistory.querySelectorAll('.from-to-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const customerCode = link.dataset.customerCode;
                if (customerCode) {
                    // Close the modal visually, then navigate to customer detail.
                    // The product modal hash stays in the history stack so
                    // pressing browser-back returns the user to the modal.
                    closeModalInternal();
                    switchTabInternal('customer');
                    openCustomerDetail(customerCode);
                }
            });
        });

        // ── Sales by Year aggregation ─────────────────────────────────────
        if (els.modalSalesByYear && els.salesByYearGrid) {
            const yearMap = {};
            for (const h of history) {
                if (!h.date || h.qty_out <= 0) continue;
                const year = h.date.split('-')[0];
                if (!year) continue;
                yearMap[year] = (yearMap[year] || 0) + h.qty_out;
            }

            const years = Object.keys(yearMap).sort((a, b) => b - a); // newest first

            if (years.length > 0) {
                els.salesByYearGrid.innerHTML = years.map(y => {
                    const ceYear = parseInt(y, 10);
                    const beYear = ceYear > 2500 ? ceYear : ceYear + 543;
                    return `<div class="year-card">
                        <span class="year-label">${beYear}</span>
                        <span class="year-qty">${formatNumber(yearMap[y])}</span>
                    </div>`;
                }).join('');
                els.modalSalesByYear.classList.remove('hidden');
            } else {
                els.modalSalesByYear.classList.add('hidden');
            }
        }

        // Render Chart.js
        if (els.archivedHistoryChart) {
            // Destroy existing chart if any
            if (archivedChartInstance) {
                archivedChartInstance.destroy();
            }

            // Prepare chart data (chronological order)
            const labels = [];      // Short labels for display (DD/MM/YY)
            const fullLabels = [];  // Full labels for tooltips (DD/MM/YYYY)
            const dataPts = [];

            // Helper: compact date for chart axis (2-digit year to save space)
            function shortBuddhistDate(dateStr) {
                const full = formatBuddhistDate(dateStr);
                if (!full || full === '-') return full;
                // DD/MM/YYYY → DD/MM/YY
                const parts = full.split('/');
                if (parts.length === 3 && parts[2].length === 4) {
                    return `${parts[0]}/${parts[1]}/${parts[2].slice(-2)}`;
                }
                return full;
            }

            for (let i = 0; i < history.length; i++) {
                const h = history[i];
                if (h.date) {
                    labels.push(shortBuddhistDate(h.date));
                    fullLabels.push(formatBuddhistDate(h.date));
                    dataPts.push(h.running_balance);
                }
            }

            // Extend the graph to the current date
            if (dataPts.length > 0) {
                const today = new Date();
                const shortToday = shortBuddhistDate(today);
                const fullToday = formatBuddhistDate(today);

                if (labels[labels.length - 1] !== shortToday) {
                    labels.push(shortToday);
                    fullLabels.push(fullToday);
                    dataPts.push(dataPts[dataPts.length - 1]); // plateau to today
                }
            }

            const ctx = els.archivedHistoryChart.getContext('2d');
            archivedChartInstance = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: 'Running Balance',
                        data: dataPts,
                        borderColor: '#8b5cf6',
                        backgroundColor: 'rgba(139, 92, 246, 0.1)',
                        borderWidth: 2,
                        pointRadius: 2,
                        pointHoverRadius: 5,
                        fill: true,
                        tension: 0.1
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    layout: {
                        padding: {
                            bottom: 4
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            grid: {
                                color: getThemeColors().gridColor
                            },
                            ticks: {
                                color: getThemeColors().tickColor,
                                font: {
                                    size: 18
                                }
                            }
                        },
                        x: {
                            grid: {
                                display: false
                            },
                            ticks: {
                                color: getThemeColors().tickColor,
                                maxTicksLimit: 8,
                                autoSkip: true,
                                autoSkipPadding: 12,
                                maxRotation: 45,
                                minRotation: 0,
                                font: {
                                    size: 20
                                }
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: false
                        },
                        tooltip: {
                            mode: 'index',
                            intersect: false,
                            backgroundColor: 'rgba(0,0,0,0.85)',
                            titleColor: '#fff',
                            bodyColor: '#fff',
                            borderColor: 'rgba(139, 92, 246, 0.3)',
                            borderWidth: 1,
                            padding: 15,
                            cornerRadius: 8,
                            titleFont: { size: 18, weight: '600' },
                            bodyFont: { size: 18 },
                            callbacks: {
                                // Show full date (DD/MM/YYYY) in tooltip instead of the short label
                                title: function(tooltipItems) {
                                    const idx = tooltipItems[0].dataIndex;
                                    return fullLabels[idx] || labels[idx];
                                },
                                label: function(context) {
                                    return `ยอดคงเหลือ: ${formatNumber(context.parsed.y)}`;
                                }
                            }
                        }
                    },
                    interaction: {
                        mode: 'nearest',
                        axis: 'x',
                        intersect: false
                    }
                }
            });
        }

    } catch (err) {
        console.error('Error fetching archived history:', err);
        els.modalArchivedHistory.innerHTML = '<p class="text-muted">โหลดประวัติเคลื่อนไหวไม่สำเร็จ</p>';
    }
}

// ─── Flags Specific Code ──────────────────────────────────────────────────

async function submitFlag() {
    if (!state.currentModalSku) return;

    let selectedType = null;
    els.flagTypeRadios.forEach(r => {
        if (r.checked) selectedType = r.value;
    });

    if (!selectedType) {
        alert("Please select an issue type.");
        return;
    }

    const note = els.reportNote.value.trim();

    try {
        els.btnSubmitReport.disabled = true;
        els.btnSubmitReport.textContent = "Submitting...";

        const res = await fetch(`/api/products/${state.currentModalSku}/flag`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ flag_type: selectedType, note: note })
        });

        if (res.ok) {
            alert("Stock mismatch reported successfully.");
            els.btnCancelReport.click(); // close the dialog

            // Re-fetch products to update the indicators, and flags table if needed
            fetchProducts();
            if (state.flags.length > 0) fetchFlags();
        } else {
            const data = await res.json();
            alert(`Error: ${data.error || 'Failed to submit'}`);
        }
    } catch (err) {
        console.error(err);
        alert("An error occurred while submitting.");
    } finally {
        els.btnSubmitReport.disabled = false;
        els.btnSubmitReport.textContent = "Submit Flag";
    }
}

async function fetchFlags() {
    els.flagsList.innerHTML = `
        <tr>
            <td colspan="8" class="text-center py-8">
                <div class="spinner"></div>
                <p class="text-muted mt-4">Loading flagged items...</p>
            </td>
        </tr>
    `;

    const params = new URLSearchParams({
        search: state.flagsSearch,
        sort: state.flagsSort,
        dir: state.flagsSortDir,
        page: state.flagsPage,
        per_page: state.flagsPerPage
    });

    try {
        const res = await fetch(`/api/flags?${params}`);
        const data = await res.json();

        state.flags = data.items;
        state.flagsTotalItems = data.total;
        state.flagsTotalPages = data.total_pages;
        state.flagsPage = data.page;

        renderFlags();
        updateFlagsPaginationInfo();
        renderFlagsPaginationControls();
        updateFlagsTabBadge(data.total);
    } catch (err) {
        console.error("Error fetching flags:", err);
        els.flagsList.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-8 text-error">
                    Failed to load flagged items.
                </td>
            </tr>
        `;
    }
}

function renderFlags() {
    if (state.flags.length === 0) {
        els.flagsList.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-8 text-muted">
                    No flagged items found.
                </td>
            </tr>
        `;
        return;
    }

    els.flagsList.innerHTML = '';

    const typeMap = {
        'out_of_stock': { label: 'สินค้าหมด (ระบบยังแสดง)', color: '#ef4444', bg: 'rgba(239, 68, 68, 0.2)' },
        'less_than': { label: 'สินค้าจริงน้อยกว่าระบบ', color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.2)' },
        'more_than': { label: 'สินค้าจริงมากกว่าระบบ', color: '#10b981', bg: 'rgba(16, 185, 129, 0.2)' }
    };

    state.flags.forEach((f, idx) => {
        const tr = document.createElement('tr');
        tr.onclick = (e) => { if (e.target.closest('.unflag-btn')) return; openModal(f, idx); };

        const thumbContent = f.thumbnail
            ? `<img src="/images/${f.thumbnail}" alt="${f.part_code} thumbnail" loading="lazy">`
            : `<div class="thumb-placeholder"></div>`;

        const typeInfo = typeMap[f.flag_type] || { label: f.flag_type, color: '#ccc', bg: '#333' };

        // Parse date
        let dateStr = formatBuddhistDate(f.flagged_at, true);

        // Reporter info
        const reporterHtml = f.flagged_by
            ? `<div style="margin-top: 4px; font-size: 0.8em; color: var(--text-secondary);">รายงานโดย: <strong>${escapeHtml(f.flagged_by)}</strong></div>`
            : '';

        // Only show Resolve button for admin users
        const isAdmin = _currentUser && _currentUser.role === 'admin';
        const resolveBtn = isAdmin
            ? `<button class="btn btn-outline unflag-btn" data-sku="${f.sku}" style="padding: 0.25rem 0.5rem; font-size: 0.85rem;">
                    <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none" style="margin-right: 4px; display: inline-block; vertical-align: text-bottom;">
                        <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                    Resolve
                </button>`
            : '';

        tr.innerHTML = `
            <td><div class="thumb-cell">${thumbContent}</div></td>
            <td><div style="font-family: monospace; font-size: 1.05rem;">${escapeHtml(f.part_code)}</div></td>
            <td>
                <div class="desc-cell">
                    <div class="desc-eng">${escapeHtml(f.name_eng || '-')}</div>
                    <div class="desc-thai">${escapeHtml(f.name_thai || '-')}</div>
                </div>
            </td>
            <td><span class="brand-badge">${escapeHtml(f.brand || '-')}</span></td>
            <td class="text-right">
                <span class="qty-badge">${formatNumber(f.system_qty)}</span>
            </td>
            <td>
                <div><span class="badge" style="background: ${typeInfo.bg}; color: ${typeInfo.color}; border: 1px solid ${typeInfo.color}40;">${typeInfo.label}</span></div>
                ${f.flag_note ? `<div style="margin-top: 4px; font-size: 0.85em; color: var(--text-secondary); max-width: 250px; white-space: normal; line-height: 1.3;">${escapeHtml(f.flag_note)}</div>` : ''}
            </td>
            <td>
                <span class="text-muted" style="font-size: 0.9em;">${dateStr}</span>
                ${reporterHtml}
            </td>
            <td class="text-right">
                ${resolveBtn}
            </td>
        `;

        els.flagsList.appendChild(tr);
    });

    // Note: unflag (.unflag-btn) click handling is done via delegated listener
    // on els.flagsList (set up once in setupEventListeners) so it survives re-renders.
}

function updateFlagsPaginationInfo() {
    els.flagsResultsCount.textContent = formatNumber(state.flagsTotalItems);
    els.flagsTotalResults.textContent = formatNumber(state.flagsTotalItems);

    if (state.flagsTotalItems === 0) {
        els.flagsPageStart.textContent = '0';
        els.flagsPageEnd.textContent = '0';
    } else {
        const start = ((state.flagsPage - 1) * state.flagsPerPage) + 1;
        const end = Math.min(state.flagsPage * state.flagsPerPage, state.flagsTotalItems);
        els.flagsPageStart.textContent = formatNumber(start);
        els.flagsPageEnd.textContent = formatNumber(end);
    }
}

function renderFlagsPaginationControls() {
    els.flagsBtnPrev.disabled = state.flagsPage <= 1;
    els.flagsBtnNext.disabled = state.flagsPage >= state.flagsTotalPages;

    els.flagsPageNumbers.innerHTML = '';
    if (state.flagsTotalPages <= 1) return;

    let startPage = Math.max(1, state.flagsPage - 2);
    let endPage = Math.min(state.flagsTotalPages, startPage + 4);

    if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
    }

    if (startPage > 1) {
        addFlagsPageButton(1);
        if (startPage > 2) addEllipsis(els.flagsPageNumbers);
    }

    for (let i = startPage; i <= endPage; i++) {
        addFlagsPageButton(i);
    }

    if (endPage < state.flagsTotalPages) {
        if (endPage < state.flagsTotalPages - 1) addEllipsis(els.flagsPageNumbers);
        addFlagsPageButton(state.flagsTotalPages);
    }
}

function addFlagsPageButton(pageNum) {
    const btn = document.createElement('button');
    btn.className = `page-btn ${pageNum === state.flagsPage ? 'active' : ''}`;
    btn.textContent = pageNum;
    if (pageNum !== state.flagsPage) {
        btn.onclick = () => {
            state.flagsPage = pageNum;
            fetchFlags();
        };
    }
    els.flagsPageNumbers.appendChild(btn);
}

// ─── Flags Tab Badge ──────────────────────────────────────────────────────
/** Update (or remove) the count badge on the flags tab button. */
function updateFlagsTabBadge(count) {
    const tabBtn = els.tabBtnFlags;
    let badge = tabBtn.querySelector('.tab-flag-count');
    if (count > 0) {
        if (!badge) {
            badge = document.createElement('span');
            badge.className = 'tab-flag-count';
            tabBtn.appendChild(badge);
        }
        badge.textContent = count;
    } else if (badge) {
        badge.remove();
    }
}

/** Lightweight fetch to get the flags count for the tab badge on page load. */
async function fetchFlagsCount() {
    try {
        const res = await fetch('/api/flags?page=1&per_page=1');
        const data = await res.json();
        updateFlagsTabBadge(data.total || 0);
    } catch (err) {
        // Non-critical — badge just won't show
        console.log('[Flags] Could not fetch flag count for tab badge');
    }
}

// ─── Photo Flags Specific Code ───────────────────────────────────────────────

async function fetchPhotoFlags() {
    els.photoFlagsList.innerHTML = `
        <tr>
            <td colspan="12" class="text-center py-8">
                <div class="spinner"></div>
                <p class="text-muted mt-4">กำลังโหลดรายการที่ต้องถ่ายรูป...</p>
            </td>
        </tr>
    `;

    const params = new URLSearchParams({
        search: state.photoFlagsSearch,
        sort: state.photoFlagsSort,
        dir: state.photoFlagsSortDir,
        page: state.photoFlagsPage,
        per_page: state.photoFlagsPerPage
    });

    try {
        const res = await fetch(`/api/photo-flags?${params}`);
        const data = await res.json();

        state.photoFlags = data.items;
        state.photoFlagsTotalItems = data.total;
        state.photoFlagsTotalPages = data.total_pages;
        state.photoFlagsPage = data.page;

        renderPhotoFlags();
        updatePhotoFlagsPaginationInfo();
        renderPhotoFlagsPaginationControls();
        updatePhotoFlagsTabBadge(data.total);
    } catch (err) {
        console.error("Error fetching photo flags:", err);
        els.photoFlagsList.innerHTML = `
            <tr>
                <td colspan="12" class="text-center py-8 text-error">
                    โหลดรายการไม่สำเร็จ
                </td>
            </tr>
        `;
    }
}

function renderPhotoFlags() {
    if (state.photoFlags.length === 0) {
        els.photoFlagsList.innerHTML = `
            <tr>
                <td colspan="11" class="text-center py-8 text-muted">
                    ไม่มีรายการที่ต้องถ่ายรูป
                </td>
            </tr>
        `;
        return;
    }

    els.photoFlagsList.innerHTML = '';

    state.photoFlags.forEach((f, idx) => {
        const tr = document.createElement('tr');
        tr.onclick = (e) => { if (e.target.closest('.photo-unflag-btn') || e.target.closest('.photo-upload-btn')) return; openModal(f, idx); };

        const thumbContent = f.thumbnail
            ? `<img src="/images/${f.thumbnail}" alt="${f.part_code} thumbnail" loading="lazy">`
            : `<div class="thumb-placeholder"></div>`;

        let dateStr = formatBuddhistDate(f.photo_flagged_at, true);

        const reporterHtml = f.photo_flagged_by
            ? `<strong>${escapeHtml(f.photo_flagged_by)}</strong>`
            : '<span class="text-muted">-</span>';

        const noteHtml = f.photo_flag_note
            ? escapeHtml(f.photo_flag_note)
            : '<span class="text-muted">-</span>';

        // Upload button (available to all users)
        const uploadBtn = `<button class="btn photo-upload-btn" data-sku="${f.sku}" title="ถ่ายรูป / เลือกรูป">
                    <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none" style="margin-right: 4px; display: inline-block; vertical-align: text-bottom;">
                        <path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"></path>
                        <circle cx="12" cy="13" r="4"></circle>
                    </svg>
                    ถ่ายรูป/เลือกรูป
                </button>`;

        // Resolve button (admin-only)
        const isAdmin = _currentUser && _currentUser.role === 'admin';
        const resolveBtn = isAdmin
            ? `<button class="btn btn-outline photo-unflag-btn" data-sku="${f.sku}" style="padding: 0.25rem 0.5rem; font-size: 0.85rem; border-color: rgba(59,130,246,0.5); color: #3b82f6;">
                    <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none" style="margin-right: 4px; display: inline-block; vertical-align: text-bottom;">
                        <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                    ถ่ายแล้ว
                </button>`
            : '';

        tr.innerHTML = `
            <td><div class="thumb-cell">${thumbContent}</div></td>
            <td><div style="font-family: monospace; font-size: 1.05rem;">${escapeHtml(f.part_code)}</div></td>
            <td>${f.suffix ? `<span class="brand-badge">${escapeHtml(f.suffix)}</span>` : '<span class="text-muted">-</span>'}</td>
            <td>
                <div class="desc-cell">
                    <div class="desc-eng">${escapeHtml(f.name_eng || '-')}</div>
                    <div class="desc-thai">${escapeHtml(f.name_thai || '-')}</div>
                </div>
            </td>
            <td>${f.brand ? `<span class="brand-badge">${escapeHtml(f.brand)}</span>` : '<span class="text-muted">-</span>'}</td>
            <td><span class="brand-badge location-badge">${f.locations || '-'}</span></td>
            <td class="text-right" style="font-family: monospace; font-weight: 600;">${f.qty != null ? formatNumber(f.qty) : '-'}</td>
            <td style="max-width: 200px; word-break: break-word;">${noteHtml}</td>
            <td>${reporterHtml}</td>
            <td style="white-space: nowrap;">${dateStr}</td>
            <td class="text-right"><span class="qty-badge" style="${f.photos_since_flag > 0 ? 'background: rgba(34,197,94,0.2); color: #4ade80; border: 1px solid rgba(34,197,94,0.3);' : 'background: rgba(239,68,68,0.2); color: #f87171; border: 1px solid rgba(239,68,68,0.3);'}">${f.photos_since_flag}</span></td>
            <td class="text-right"><div class="photo-flag-actions">${uploadBtn}${resolveBtn}</div></td>
        `;

        els.photoFlagsList.appendChild(tr);
    });
}

function updatePhotoFlagsPaginationInfo() {
    els.photoFlagsResultsCount.textContent = formatNumber(state.photoFlagsTotalItems);
    els.photoFlagsTotalResults.textContent = formatNumber(state.photoFlagsTotalItems);

    if (state.photoFlagsTotalItems === 0) {
        els.photoFlagsPageStart.textContent = '0';
        els.photoFlagsPageEnd.textContent = '0';
    } else {
        const start = ((state.photoFlagsPage - 1) * state.photoFlagsPerPage) + 1;
        const end = Math.min(state.photoFlagsPage * state.photoFlagsPerPage, state.photoFlagsTotalItems);
        els.photoFlagsPageStart.textContent = formatNumber(start);
        els.photoFlagsPageEnd.textContent = formatNumber(end);
    }
}

function renderPhotoFlagsPaginationControls() {
    els.photoFlagsBtnPrev.disabled = state.photoFlagsPage <= 1;
    els.photoFlagsBtnNext.disabled = state.photoFlagsPage >= state.photoFlagsTotalPages;

    els.photoFlagsPageNumbers.innerHTML = '';
    if (state.photoFlagsTotalPages <= 1) return;

    let startPage = Math.max(1, state.photoFlagsPage - 2);
    let endPage = Math.min(state.photoFlagsTotalPages, startPage + 4);

    if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
    }

    if (startPage > 1) {
        addPhotoFlagsPageButton(1);
        if (startPage > 2) addEllipsis(els.photoFlagsPageNumbers);
    }

    for (let i = startPage; i <= endPage; i++) {
        addPhotoFlagsPageButton(i);
    }

    if (endPage < state.photoFlagsTotalPages) {
        if (endPage < state.photoFlagsTotalPages - 1) addEllipsis(els.photoFlagsPageNumbers);
        addPhotoFlagsPageButton(state.photoFlagsTotalPages);
    }
}

function addPhotoFlagsPageButton(pageNum) {
    const btn = document.createElement('button');
    btn.className = `page-btn ${pageNum === state.photoFlagsPage ? 'active' : ''}`;
    btn.textContent = pageNum;
    if (pageNum !== state.photoFlagsPage) {
        btn.onclick = () => {
            state.photoFlagsPage = pageNum;
            fetchPhotoFlags();
        };
    }
    els.photoFlagsPageNumbers.appendChild(btn);
}

function updatePhotoFlagsTabBadge(count) {
    const tabBtn = els.tabBtnPhotoFlags;
    if (!tabBtn) return;
    let badge = tabBtn.querySelector('.tab-badge');
    if (count > 0) {
        if (!badge) {
            badge = document.createElement('span');
            badge.className = 'tab-badge';
            badge.style.cssText = 'margin-left: 0.4rem; background: #3b82f6; color: white; font-size: 0.7rem; padding: 0.15rem 0.45rem; border-radius: 10px; font-weight: 600;';
            tabBtn.appendChild(badge);
        }
        badge.textContent = count;
    } else if (badge) {
        badge.remove();
    }
}

/** Lightweight fetch to get photo-flags count for the tab badge on page load. */
async function fetchPhotoFlagsCount() {
    try {
        const res = await fetch('/api/photo-flags?page=1&per_page=1');
        const data = await res.json();
        updatePhotoFlagsTabBadge(data.total || 0);
    } catch (err) {
        console.log('[PhotoFlags] Could not fetch photo-flag count for tab badge');
    }
}

// ─── Pickup Mode ─────────────────────────────────────────────────────────────
// Location-grouped checklist view for warehouse item pickup.
// Toggled from the photo flags tab via the "📋หยิบสินค้า" button.
// Checked state is stored on the SERVER (shared across all users).

/** Toggle between normal table view and pickup mode. */
async function togglePickupMode() {
    const btn = document.getElementById('pickup-mode-toggle');
    const container = document.getElementById('pickup-mode-container');
    const tableSection = document.getElementById('photo-flags-table-section');
    const paginationSection = tableSection ? tableSection.nextElementSibling : null;

    state.pickupMode = !state.pickupMode;

    if (state.pickupMode) {
        btn.classList.add('active');
        btn.innerHTML = '📋 กลับไปตาราง';
        container.classList.remove('hidden');
        if (tableSection) tableSection.classList.add('hidden');
        // Hide photo flags pagination controls (next sibling of table section)
        if (paginationSection && paginationSection.classList.contains('pagination-controls')) {
            paginationSection.classList.add('hidden');
        }
        await fetchPickupData();
    } else {
        btn.classList.remove('active');
        btn.innerHTML = '📋 หยิบสินค้า';
        container.classList.add('hidden');
        if (tableSection) tableSection.classList.remove('hidden');
        if (paginationSection && paginationSection.classList.contains('pagination-controls')) {
            paginationSection.classList.remove('hidden');
        }
    }
}

/** Fetch all photo-flagged items grouped by location. */
async function fetchPickupData() {
    const groupsEl = document.getElementById('pickup-groups');
    groupsEl.innerHTML = `
        <div style="text-align:center; padding:2rem;">
            <div class="spinner"></div>
            <p class="text-muted mt-4">กำลังโหลดรายการหยิบสินค้า...</p>
        </div>
    `;

    try {
        const res = await fetch('/api/photo-flags/pickup');
        const data = await res.json();
        state.pickupData = data;
        renderPickupMode(data);
    } catch (err) {
        console.error('[Pickup] Error fetching pickup data:', err);
        groupsEl.innerHTML = `<p class="text-error" style="padding:1rem;">โหลดข้อมูลไม่สำเร็จ</p>`;
    }
}

/** Render the grouped-by-location pickup checklist. */
function renderPickupMode(data) {
    const groupsEl = document.getElementById('pickup-groups');

    if (!data.groups || data.groups.length === 0) {
        groupsEl.innerHTML = `<p class="text-muted" style="padding:2rem; text-align:center;">ไม่มีรายการที่ต้องหยิบ</p>`;
        updatePickupProgress(0, 0);
        return;
    }

    let html = '';
    let totalItems = 0;
    let totalChecked = 0;

    data.groups.forEach(group => {
        const groupCheckedCount = group.items.filter(it => it.checked || it.status === 'crossed').length;
        totalItems += group.count;
        totalChecked += groupCheckedCount;

        const checkLabel = groupCheckedCount === group.count
            ? '<span class="pickup-location-check">✅ ครบแล้ว</span>'
            : groupCheckedCount > 0
                ? `<span class="pickup-location-check">${groupCheckedCount}/${group.count}</span>`
                : '';

        html += `<div class="pickup-location-group">`;
        html += `<div class="pickup-location-header">`;
        html += `  <span class="pickup-location-icon">📦</span>`;
        html += `  <span class="pickup-location-code">${escapeHtml(group.location)}</span>`;
        html += `  <span class="pickup-location-count">${group.count} รายการ</span>`;
        html += `  ${checkLabel}`;
        html += `</div>`;

        group.items.forEach(item => {
            const isChecked = item.checked && item.status !== 'crossed' ? 'checked' : '';
            const isCrossed = item.status === 'crossed' ? 'crossed' : '';
            const ghostClass = item.ghost ? 'ghost-stock' : '';
            const ghostBadge = item.ghost ? '<span class="pickup-ghost-badge">⚠️ อาจไม่มีของ</span>' : '';
            const qtyDisplay = item.qty != null ? formatNumber(item.qty) : '-';
            const flaggedClass = item.stock_flag ? `pickup-flagged pickup-flag-${item.stock_flag}` : '';
            const flagLabels = { out_of_stock: '⚠ สินค้าหมด (ระบบยังแสดง)', less_than: '⚠ สินค้าจริงน้อยกว่าระบบ', more_than: 'ℹ สินค้าจริงมากกว่าระบบ' };
            const flagBadge = item.stock_flag ? `<span class="pickup-flagged-badge ${item.stock_flag}">${flagLabels[item.stock_flag] || '🚩 แจ้งแล้ว'}</span>` : '';
            const checkedByLabel = item.checked && item.checked_by ? `<span class="pickup-checked-by">${item.status === 'crossed' ? '✗' : '✓'} ${escapeHtml(item.checked_by)}</span>` : '';

            html += `<div class="pickup-item ${isChecked} ${isCrossed} ${ghostClass} ${flaggedClass}" data-sku="${item.sku}">`;
            html += `  <div class="pickup-checkbox"></div>`;
            html += `  <div class="pickup-item-info">`;
            const typeBadge = item.suffix ? `<span class="pickup-type-badge type-${(item.suffix || '').toLowerCase()}">${escapeHtml(item.suffix)}</span>` : '';
            html += `    <div class="pickup-item-code-row"><span class="pickup-item-code">${escapeHtml(item.part_code)}</span>${typeBadge}</div>`;
            html += `    <span class="pickup-item-name">${escapeHtml(item.name_thai || item.name_eng || '-')}</span>`;
            html += `    ${flagBadge}`;
            html += `  </div>`;
            html += `  ${ghostBadge}`;
            html += `  <button class="pickup-flag-btn" data-sku="${item.sku}" data-part="${escapeHtml(item.part_code)}" title="แจ้งปัญหาสต็อก">🚩</button>`;
            html += `  ${checkedByLabel}`;
            html += `  <span class="pickup-item-qty">${qtyDisplay}</span>`;
            html += `</div>`;
        });

        html += `</div>`;
    });

    groupsEl.innerHTML = html;
    updatePickupProgress(totalChecked, totalItems);

    // Click handler for items (delegated) — remove first to prevent duplicates on re-render
    groupsEl.removeEventListener('click', handlePickupItemClick);
    groupsEl.addEventListener('click', handlePickupItemClick);
}

/** Handle clicking a pickup item to toggle checked state.
 *  3-state cycle: unchecked → checked (green ✓) → crossed (red ✗) → unchecked */
async function handlePickupItemClick(e) {
    // If the flag button was clicked, handle that instead
    const flagBtn = e.target.closest('.pickup-flag-btn');
    if (flagBtn) {
        e.stopPropagation();
        showPickupFlagPopup(flagBtn);
        return;
    }

    const itemEl = e.target.closest('.pickup-item');
    if (!itemEl) return;

    const sku = itemEl.dataset.sku;
    const wasChecked = itemEl.classList.contains('checked');
    const wasCrossed = itemEl.classList.contains('crossed');

    // Determine next state in the cycle: unchecked → checked → crossed → unchecked
    let nextState;
    if (wasChecked) {
        nextState = 'crossed';  // checked → crossed (red ✗)
    } else if (wasCrossed) {
        nextState = 'unchecked'; // crossed → unchecked
    } else {
        nextState = 'checked';  // unchecked → checked (green ✓)
    }

    // Optimistic UI update
    itemEl.classList.remove('checked', 'crossed');
    const byLabel = itemEl.querySelector('.pickup-checked-by');
    if (byLabel) byLabel.remove();
    if (nextState === 'checked') {
        itemEl.classList.add('checked');
    } else if (nextState === 'crossed') {
        itemEl.classList.add('crossed');
    }

    // Call server to persist
    try {
        if (nextState === 'unchecked') {
            await fetch(`/api/pickup-checks/${encodeURIComponent(sku)}`, { method: 'DELETE' });
        } else {
            const res = await fetch(`/api/pickup-checks/${encodeURIComponent(sku)}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: nextState })
            });
            const data = await res.json();
            // Add checked-by label
            if (data.checked_by && !itemEl.querySelector('.pickup-checked-by')) {
                const badge = document.createElement('span');
                badge.className = 'pickup-checked-by';
                badge.textContent = `${nextState === 'crossed' ? '✗' : '✓'} ${data.checked_by}`;
                const qtyEl = itemEl.querySelector('.pickup-item-qty');
                if (qtyEl) itemEl.insertBefore(badge, qtyEl);
            }
        }
    } catch (err) {
        console.error('[Pickup] Error toggling check:', err);
        // Revert optimistic update on failure
        itemEl.classList.remove('checked', 'crossed');
        if (wasChecked) itemEl.classList.add('checked');
        else if (wasCrossed) itemEl.classList.add('crossed');
        return;
    }

    // Update progress counter
    _updatePickupCounters();

    // Update the header counter for this location group
    const groupEl = itemEl.closest('.pickup-location-group');
    if (groupEl) {
        const items = groupEl.querySelectorAll('.pickup-item');
        const total = items.length;
        const groupChecked = groupEl.querySelectorAll('.pickup-item.checked, .pickup-item.crossed').length;
        const headerCheck = groupEl.querySelector('.pickup-location-check');
        if (groupChecked === total) {
            if (headerCheck) headerCheck.innerHTML = '✅ ครบแล้ว';
            else {
                const hdr = groupEl.querySelector('.pickup-location-header');
                const span = document.createElement('span');
                span.className = 'pickup-location-check';
                span.innerHTML = '✅ ครบแล้ว';
                hdr.appendChild(span);
            }
        } else if (groupChecked > 0) {
            if (headerCheck) headerCheck.textContent = `${groupChecked}/${total}`;
            else {
                const hdr = groupEl.querySelector('.pickup-location-header');
                const span = document.createElement('span');
                span.className = 'pickup-location-check';
                span.textContent = `${groupChecked}/${total}`;
                hdr.appendChild(span);
            }
        } else if (headerCheck) {
            headerCheck.remove();
        }
    }
}

/** Re-count checked/crossed items from DOM and update progress bar. */
function _updatePickupCounters() {
    const groupsEl = document.getElementById('pickup-groups');
    if (!groupsEl) return;
    const allItems = groupsEl.querySelectorAll('.pickup-item');
    const doneItems = groupsEl.querySelectorAll('.pickup-item.checked, .pickup-item.crossed');
    updatePickupProgress(doneItems.length, allItems.length);
}

/** Show a quick flag-type popup near the flag button. */
function showPickupFlagPopup(btn) {
    // Remove any existing popup
    const existing = document.getElementById('pickup-flag-popup');
    if (existing) existing.remove();

    const sku = btn.dataset.sku;
    const partCode = btn.dataset.part;

    const popup = document.createElement('div');
    popup.id = 'pickup-flag-popup';
    popup.className = 'pickup-flag-popup';
    popup.innerHTML = `
        <div class="pickup-flag-popup-title">🚩 แจ้งปัญหาสต็อก<br><small>${partCode}</small></div>
        <button class="pickup-flag-option out-of-stock" data-type="out_of_stock">⚠ สินค้าหมด (ระบบยังแสดง)</button>
        <button class="pickup-flag-option less-than" data-type="less_than">⚠ สินค้าจริงน้อยกว่าระบบ</button>
        <button class="pickup-flag-option more-than" data-type="more_than">ℹ สินค้าจริงมากกว่าระบบ</button>
    `;

    document.body.appendChild(popup);

    // Position near the button
    const rect = btn.getBoundingClientRect();
    popup.style.top = (rect.bottom + 4) + 'px';
    popup.style.right = (window.innerWidth - rect.right) + 'px';

    // Handle option clicks
    popup.querySelectorAll('.pickup-flag-option').forEach(opt => {
        opt.addEventListener('click', async () => {
            const flagType = opt.dataset.type;
            opt.disabled = true;
            opt.textContent = '⏳ กำลังบันทึก...';

            try {
                const res = await fetch(`/api/products/${sku}/flag`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ flag_type: flagType, note: 'แจ้งจากหน้าหยิบสินค้า' })
                });

                if (res.ok) {
                    // Mark the item visually as flagged
                    const itemEl = document.querySelector(`.pickup-item[data-sku="${sku}"]`);
                    if (itemEl) {
                        itemEl.classList.add('pickup-flagged', `pickup-flag-${flagType}`);
                        // Add a small flagged badge if not already there
                        if (!itemEl.querySelector('.pickup-flagged-badge')) {
                            const badge = document.createElement('span');
                            badge.className = `pickup-flagged-badge ${flagType}`;
                            const labels = { out_of_stock: '⚠ สินค้าหมด (ระบบยังแสดง)', less_than: '⚠ สินค้าจริงน้อยกว่าระบบ', more_than: 'ℹ สินค้าจริงมากกว่าระบบ' };
                            badge.textContent = labels[flagType] || '🚩 แจ้งแล้ว';
                            itemEl.querySelector('.pickup-item-info').appendChild(badge);
                        }
                        // Auto-check item off via server (since they reported it, they're done with it)
                        if (!itemEl.classList.contains('checked')) {
                            itemEl.classList.add('checked');
                            try {
                                await fetch(`/api/pickup-checks/${encodeURIComponent(sku)}`, { method: 'POST' });
                            } catch (err) {
                                console.error('[Pickup] Error auto-checking flagged item:', err);
                            }
                            _updatePickupCounters();
                        }
                    }
                    popup.remove();
                } else {
                    opt.textContent = '⚠️ ไม่สำเร็จ';
                    setTimeout(() => popup.remove(), 1500);
                }
            } catch (err) {
                console.error('[Pickup] Flag error:', err);
                opt.textContent = '⚠️ ไม่สำเร็จ';
                setTimeout(() => popup.remove(), 1500);
            }
        });
    });

    // Close on outside click
    setTimeout(() => {
        document.addEventListener('click', function closePopup(ev) {
            if (!popup.contains(ev.target) && ev.target !== btn) {
                popup.remove();
                document.removeEventListener('click', closePopup);
            }
        });
    }, 50);
}

/** Update the pickup progress bar and text. */
function updatePickupProgress(checked, total) {
    const textEl = document.getElementById('pickup-progress-text');
    const fillEl = document.getElementById('pickup-progress-fill');
    if (textEl) textEl.textContent = `✅ ${checked} / ${total} หยิบแล้ว`;
    if (fillEl) {
        const pct = total > 0 ? Math.round((checked / total) * 100) : 0;
        fillEl.style.width = pct + '%';
    }
}

/** Reset all pickup checkboxes (server-side). */
async function resetPickupChecked() {
    if (!confirm('รีเซ็ตรายการที่หยิบแล้วทั้งหมด?')) return;
    try {
        const res = await fetch('/api/pickup-checks', { method: 'DELETE' });
        if (res.ok) {
            if (state.pickupData) {
                // Clear checked/crossed state in local data and re-render
                state.pickupData.groups.forEach(g => g.items.forEach(it => { it.checked = false; it.checked_by = ''; it.status = ''; }));
                state.pickupData.total_checked = 0;
                renderPickupMode(state.pickupData);
            }
        } else {
            const data = await res.json();
            alert(data.error || 'ไม่สามารถรีเซ็ตได้');
        }
    } catch (err) {
        console.error('[Pickup] Error resetting checks:', err);
        alert('เกิดข้อผิดพลาดในการรีเซ็ต');
    }
}

// Wire up pickup mode event listeners (called once after DOM ready)
function setupPickupListeners() {
    const toggleBtn = document.getElementById('pickup-mode-toggle');
    if (toggleBtn) toggleBtn.addEventListener('click', togglePickupMode);

    const resetBtn = document.getElementById('pickup-reset-btn');
    if (resetBtn) resetBtn.addEventListener('click', resetPickupChecked);
}

// Start app — check authentication first
document.addEventListener('DOMContentLoaded', authCheckAndInit);

// ─── Customer List & Detail Code ────────────────────────────────────────────

function showCustomerListMode() {
    if (els.customerListPanel) els.customerListPanel.classList.remove('hidden');
    if (els.customerDetailPanel) els.customerDetailPanel.classList.add('hidden');
}

function showCustomerDetailMode() {
    if (els.customerListPanel) els.customerListPanel.classList.add('hidden');
    if (els.customerDetailPanel) els.customerDetailPanel.classList.remove('hidden');
}

async function fetchCustomers() {
    els.customerList.innerHTML = `
        <tr>
            <td colspan="6" class="text-center py-8">
                <div class="spinner"></div>
                <p class="text-muted mt-4">กำลังโหลดรายชื่อลูกค้า...</p>
            </td>
        </tr>
    `;
    showCustomerListMode();

    const params = new URLSearchParams({
        search: state.customerSearch,
        page: state.customersPage,
        per_page: state.customersPerPage
    });

    try {
        const res = await fetch(`/api/customers?${params}`);
        const data = await res.json();

        state.customers = data.items;
        state.customersTotalItems = data.total;
        state.customersTotalPages = data.total_pages;
        state.customersPage = data.page;

        renderCustomers();
        updateCustomersPaginationInfo();
        renderCustomersPaginationControls();
    } catch (err) {
        console.error("Error fetching customers:", err);
        els.customerList.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-8 text-error">
                    ไม่สามารถโหลดรายชื่อลูกค้าได้
                </td>
            </tr>
        `;
    }
}

function renderCustomers() {
    if (state.customers.length === 0) {
        els.customerList.innerHTML = `
            <tr>
                <td colspan="6" class="text-center py-8 text-muted">
                    ไม่พบลูกค้าที่ตรงกัน
                </td>
            </tr>
        `;
        return;
    }

    els.customerList.innerHTML = '';

    state.customers.forEach((c) => {
        const tr = document.createElement('tr');
        tr.style.cursor = 'pointer';
        tr.onclick = () => openCustomerDetail(c.customer_code);

        const statusBadge = c.status === 'active'
            ? '<span class="brand-badge" style="background: rgba(34,197,94,0.2); color: #4ade80;">Active</span>'
            : '<span class="brand-badge" style="background: rgba(239,68,68,0.2); color: #f87171;">Inactive</span>';

        const creditDays = c.credit_days ? parseFloat(c.credit_days) : 0;
        const creditFormatted = creditDays > 0 ? `${creditDays}` : '<span class="text-muted">-</span>';

        tr.innerHTML = `
            <td><div style="font-family: monospace; font-size: 1.05rem;">${escapeHtml(c.customer_code)}</div></td>
            <td>${escapeHtml(c.customer_name || '-')}</td>
            <td>${c.phone ? escapeHtml(c.phone) : '<span class="text-muted">-</span>'}</td>
            <td class="text-right">${creditFormatted}</td>
            <td>${statusBadge}</td>
            <td class="text-right"><span class="qty-badge">${formatNumber(c.txn_count || 0)}</span></td>
        `;

        els.customerList.appendChild(tr);
    });
}

function updateCustomersPaginationInfo() {
    els.customerResultsCount.textContent = formatNumber(state.customersTotalItems);
    els.custTotalResults.textContent = formatNumber(state.customersTotalItems);

    if (state.customersTotalItems === 0) {
        els.custPageStart.textContent = '0';
        els.custPageEnd.textContent = '0';
    } else {
        const start = ((state.customersPage - 1) * state.customersPerPage) + 1;
        const end = Math.min(state.customersPage * state.customersPerPage, state.customersTotalItems);
        els.custPageStart.textContent = formatNumber(start);
        els.custPageEnd.textContent = formatNumber(end);
    }
}

function renderCustomersPaginationControls() {
    els.custBtnPrev.disabled = state.customersPage <= 1;
    els.custBtnNext.disabled = state.customersPage >= state.customersTotalPages;

    els.custPageNumbers.innerHTML = '';
    if (state.customersTotalPages <= 1) return;

    let startPage = Math.max(1, state.customersPage - 2);
    let endPage = Math.min(state.customersTotalPages, startPage + 4);
    if (endPage - startPage < 4) startPage = Math.max(1, endPage - 4);

    if (startPage > 1) {
        addCustPageButton(1);
        if (startPage > 2) addEllipsis(els.custPageNumbers);
    }
    for (let i = startPage; i <= endPage; i++) addCustPageButton(i);
    if (endPage < state.customersTotalPages) {
        if (endPage < state.customersTotalPages - 1) addEllipsis(els.custPageNumbers);
        addCustPageButton(state.customersTotalPages);
    }
}

function addCustPageButton(pageNum) {
    const btn = document.createElement('button');
    btn.className = `page-btn ${pageNum === state.customersPage ? 'active' : ''}`;
    btn.textContent = pageNum;
    if (pageNum !== state.customersPage) {
        btn.onclick = () => {
            state.customersPage = pageNum;
            fetchCustomers();
        };
    }
    els.custPageNumbers.appendChild(btn);
}

async function openCustomerDetail(code) {
    if (!_handlingPopstate) navPush('customer/' + encodeURIComponent(code));
    openCustomerDetailInternal(code);
}

async function openCustomerDetailInternal(code) {
    state.customerDetailCode = code;
    showCustomerDetailMode();

    // Show loading
    els.customerInfoCard.innerHTML = '<div class="spinner" style="margin:1rem auto;"></div>';
    els.custDetailTxnList.innerHTML = '<tr><td colspan="6" class="text-center py-8"><div class="spinner"></div></td></tr>';

    try {
        const res = await fetch(`/api/customers/${encodeURIComponent(code)}`);
        if (!res.ok) throw new Error('Customer not found');
        const data = await res.json();

        const c = data.customer;
        const txns = data.transactions;

        // Render info card
        const statusBadge = c.status === 'active'
            ? '<span class="brand-badge" style="background: rgba(34,197,94,0.2); color: #4ade80;">Active</span>'
            : '<span class="brand-badge" style="background: rgba(239,68,68,0.2); color: #f87171;">Inactive</span>';



        els.customerInfoCard.innerHTML = `
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 1rem;">
                <div>
                    <div style="display: flex; align-items: baseline; gap: 0.75rem; flex-wrap: wrap; margin-bottom: 0.25rem;">
                        <h2 style="margin:0; font-family: monospace; font-size: 1.3rem; color: var(--accent);">${c.customer_code}</h2>
                        ${statusBadge}
                        ${c.branch_type_name ? `<span class="brand-badge">${c.branch_type_name}</span>` : ''}
                    </div>
                    <h3 style="margin: 0.25rem 0 0; font-weight: 500; color: var(--text-primary); font-size: 1.1rem;">${c.customer_name || '-'}</h3>
                </div>
            </div>

            <div class="detail-grid" style="margin-top: 1rem; display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 0.75rem;">
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">โทรศัพท์</span>
                    <span class="value" style="color: var(--text-primary);">${c.phone || '-'}</span>
                </div>
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">ที่อยู่</span>
                    <span class="value" style="color: var(--text-primary); font-size: 0.9em;">${c.address || '-'}</span>
                </div>
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">เลขผู้เสียภาษี</span>
                    <span class="value" style="color: var(--text-primary); font-family: monospace;">${c.tax_id || '-'}</span>
                </div>
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">ผู้ติดต่อ</span>
                    <span class="value" style="color: var(--text-primary);">${c.contact_person || '-'}</span>
                </div>
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">เครดิต (วัน)</span>
                    <span class="value" style="color: var(--text-primary); font-weight: 600;">${c.credit_days ? parseFloat(c.credit_days) : '-'}</span>
                </div>
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">วงเงินเครดิต</span>
                    <span class="value" style="color: var(--text-primary);">${c.credit_limit ? formatPrice(parseFloat(c.credit_limit)) : '-'}</span>
                </div>

                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">กำหนดเก็บ</span>
                    <span class="value" style="color: var(--text-primary);">${c.collection_schedule || '-'}</span>
                </div>
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">หมายเหตุเก็บเงิน</span>
                    <span class="value" style="color: var(--text-primary);">${c.collection_note || '-'}</span>
                </div>
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">เปิดบัญชี</span>
                    <span class="value" style="color: var(--text-primary);">${c.date_opened ? formatBuddhistDate(c.date_opened) : '-'}</span>
                </div>
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">ใบกำกับล่าสุด</span>
                    <span class="value" style="color: var(--text-primary);">${c.date_last_invoice ? formatBuddhistDate(c.date_last_invoice) : '-'} ${c.last_invoice_no || ''}</span>
                </div>
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">ชำระล่าสุด</span>
                    <span class="value" style="color: var(--text-primary);">${c.date_last_payment ? formatBuddhistDate(c.date_last_payment) : '-'} ${c.last_receipt_no || ''}</span>
                </div>
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">พนักงานขาย</span>
                    <span class="value" style="color: var(--text-primary);">${c.salesperson_code || '-'}</span>
                </div>
            </div>
        `;

        // Render transactions
        els.custDetailTxnCount.textContent = formatNumber(txns.length);

        if (txns.length === 0) {
            els.custDetailTxnList.innerHTML = `<tr><td colspan="6" class="text-center py-8 text-muted">ไม่พบประวัติการซื้อ</td></tr>`;
        } else {
            els.custDetailTxnList.innerHTML = '';
            txns.forEach((h) => {
                const tr = document.createElement('tr');
                let outHtml = h.qty_out > 0 ? `<span class="change-out">${formatNumber(h.qty_out)}</span>` : '<span class="text-muted">0</span>';
                let inHtml = h.qty_in > 0 ? `<span class="change-in">+${formatNumber(h.qty_in)}</span>` : '<span class="text-muted">0</span>';
                tr.innerHTML = `
                    <td style="white-space:nowrap;">${formatBuddhistDate(h.date)}</td>
                    <td>${h.doc_ref || '-'}</td>
                    <td>${getCategoryThai(h.category_name)}</td>
                    <td><div style="font-family: monospace; font-size: 1.05rem;">${h.sku}</div></td>
                    <td>${h.name_en || '-'}</td>
                    <td class="text-right">${inHtml}</td>
                    <td class="text-right">${outHtml}</td>
                    <td class="text-right">${h.unit_price ? formatPrice(h.unit_price) : '-'}</td>
                `;
                els.custDetailTxnList.appendChild(tr);
            });
        }
    } catch (err) {
        console.error("Error fetching customer detail:", err);
        els.customerInfoCard.innerHTML = `<p class="text-error">ไม่สามารถโหลดข้อมูลลูกค้าได้</p>`;
        els.custDetailTxnList.innerHTML = '';
    }
}

// ─── Invoice List & Detail Code ────────────────────────────────────────────

function showInvoiceListMode() {
    if (els.invoiceListPanel) els.invoiceListPanel.classList.remove('hidden');
    if (els.invoiceDetailPanel) els.invoiceDetailPanel.classList.add('hidden');
}

function showInvoiceDetailMode() {
    if (els.invoiceListPanel) els.invoiceListPanel.classList.add('hidden');
    if (els.invoiceDetailPanel) els.invoiceDetailPanel.classList.remove('hidden');
}

async function fetchInvoices() {
    els.invoiceList.innerHTML = `
        <tr>
            <td colspan="9" class="text-center py-8">
                <div class="spinner"></div>
                <p class="text-muted mt-4">กำลังโหลดใบกำกับภาษี...</p>
            </td>
        </tr>
    `;

    const params = new URLSearchParams({
        search: state.invoicesSearch,
        doc_type: state.invoicesDocType,
        sort: state.invoicesSort,
        dir: state.invoicesSortDir,
        page: state.invoicesPage,
        per_page: state.invoicesPerPage
    });

    try {
        const res = await fetch(`/api/invoices?${params}`);
        const data = await res.json();

        state.invoices = data.items;
        state.invoicesTotalItems = data.total;
        state.invoicesTotalPages = data.total_pages;
        state.invoicesPage = data.page;

        renderInvoices();
        updateInvoicesPaginationInfo();
        renderInvoicesPaginationControls();
    } catch (err) {
        console.error("Error fetching invoices:", err);
        els.invoiceList.innerHTML = `
            <tr>
                <td colspan="9" class="text-center py-8 text-error">ไม่สามารถโหลดข้อมูลใบกำกับภาษีได้</td>
            </tr>
        `;
    }
}

function renderInvoices() {
    if (state.invoices.length === 0) {
        els.invoiceList.innerHTML = `<tr><td colspan="9" class="text-center py-8 text-muted">ไม่พบใบกำกับภาษี</td></tr>`;
        return;
    }

    els.invoiceList.innerHTML = '';
    state.invoices.forEach((inv) => {
        const tr = document.createElement('tr');
        tr.style.cursor = 'pointer';
        tr.onclick = () => openInvoiceDetail(inv.invoice_number);

        const docTypeBadge = inv.doc_type === 'IV'
            ? `<span class="brand-badge" style="background: rgba(59, 130, 246, 0.2); color: #93c5fd;">IV</span>`
            : inv.doc_type === 'OR'
                ? `<span class="brand-badge" style="background: rgba(245, 158, 11, 0.2); color: #fcd34d;">OR</span>`
                : `<span class="brand-badge">${inv.doc_type || '-'}</span>`;

        const voidIndicator = inv.void_date ? ` <span style="color: #ef4444; font-size: 0.8em;">(ยกเลิก)</span>` : '';

        tr.innerHTML = `
            <td><div style="font-family: monospace; font-size: 1.05rem;">${escapeHtml(inv.invoice_number)}${voidIndicator}</div></td>
            <td>${docTypeBadge}</td>
            <td style="white-space:nowrap;">${formatBuddhistDate(inv.invoice_date)}</td>
            <td><div style="font-family: monospace;">${escapeHtml(inv.customer_code || '-')}</div></td>
            <td>${escapeHtml(inv.customer_name || '-')}</td>
            <td class="text-right">${inv.subtotal ? formatPrice(inv.subtotal) : '-'}</td>
            <td class="text-right">${inv.vat_amount ? formatPrice(inv.vat_amount) : '-'}</td>
            <td class="text-right"><strong>${inv.grand_total ? formatPrice(inv.grand_total) : '-'}</strong></td>
            <td class="text-right"><span class="badge">${inv.line_item_count || 0}</span></td>
        `;

        els.invoiceList.appendChild(tr);
    });
}

function updateInvoicesPaginationInfo() {
    els.invoiceResultsCount.textContent = formatNumber(state.invoicesTotalItems);
    els.invTotalResults.textContent = formatNumber(state.invoicesTotalItems);

    if (state.invoicesTotalItems === 0) {
        els.invPageStart.textContent = '0';
        els.invPageEnd.textContent = '0';
    } else {
        const start = ((state.invoicesPage - 1) * state.invoicesPerPage) + 1;
        const end = Math.min(state.invoicesPage * state.invoicesPerPage, state.invoicesTotalItems);
        els.invPageStart.textContent = formatNumber(start);
        els.invPageEnd.textContent = formatNumber(end);
    }
}

function renderInvoicesPaginationControls() {
    els.invBtnPrev.disabled = state.invoicesPage <= 1;
    els.invBtnNext.disabled = state.invoicesPage >= state.invoicesTotalPages;

    els.invPageNumbers.innerHTML = '';
    if (state.invoicesTotalPages <= 1) return;

    let startPage = Math.max(1, state.invoicesPage - 2);
    let endPage = Math.min(state.invoicesTotalPages, startPage + 4);
    if (endPage - startPage < 4) {
        startPage = Math.max(1, endPage - 4);
    }

    if (startPage > 1) {
        addInvPageButton(1);
        if (startPage > 2) addEllipsis(els.invPageNumbers);
    }

    for (let i = startPage; i <= endPage; i++) {
        addInvPageButton(i);
    }

    if (endPage < state.invoicesTotalPages) {
        if (endPage < state.invoicesTotalPages - 1) addEllipsis(els.invPageNumbers);
        addInvPageButton(state.invoicesTotalPages);
    }
}

function addInvPageButton(pageNum) {
    const btn = document.createElement('button');
    btn.className = `page-btn ${pageNum === state.invoicesPage ? 'active' : ''}`;
    btn.textContent = pageNum;
    if (pageNum !== state.invoicesPage) {
        btn.onclick = () => {
            state.invoicesPage = pageNum;
            fetchInvoices();
        };
    }
    els.invPageNumbers.appendChild(btn);
}

async function openInvoiceDetail(invoiceNumber) {
    if (!_handlingPopstate) navPush('invoice/' + encodeURIComponent(invoiceNumber));
    state.invoiceDetailNumber = invoiceNumber;
    showInvoiceDetailMode();

    // Show loading
    els.invoiceInfoCard.innerHTML = `<div class="spinner"></div><p class="text-muted">กำลังโหลดข้อมูล...</p>`;
    els.invDetailItemsList.innerHTML = '';
    els.invDetailItemCount.textContent = '--';

    try {
        const res = await fetch(`/api/invoices/${encodeURIComponent(invoiceNumber)}`);
        const data = await res.json();

        if (data.error) {
            els.invoiceInfoCard.innerHTML = `<p class="text-error">ไม่พบใบกำกับภาษี: ${invoiceNumber}</p>`;
            return;
        }

        const h = data.header;
        const items = data.line_items || [];

        const docTypeBadge = h.doc_type === 'IV'
            ? `<span class="brand-badge" style="background: rgba(59, 130, 246, 0.3); color: #93c5fd; font-size: 1rem; padding: 0.3rem 0.8rem;">ใบกำกับภาษี (IV)</span>`
            : h.doc_type === 'OR'
                ? `<span class="brand-badge" style="background: rgba(245, 158, 11, 0.3); color: #fcd34d; font-size: 1rem; padding: 0.3rem 0.8rem;">นอกระบบ (OR)</span>`
                : `<span class="brand-badge">${h.doc_type || '-'}</span>`;

        const voidBadge = h.void_date
            ? `<span style="background: rgba(239, 68, 68, 0.3); color: #fca5a5; padding: 0.3rem 0.8rem; border-radius: var(--radius-sm); font-size: 0.9rem; margin-left: 0.5rem;">ยกเลิก ${formatBuddhistDate(h.void_date)}</span>`
            : '';

        els.invoiceInfoCard.innerHTML = `
            <div style="display: flex; align-items: center; gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem;">
                <h2 style="margin: 0; font-family: monospace; font-size: 1.5rem; color: var(--text-primary);">${h.invoice_number}</h2>
                ${docTypeBadge}
                ${voidBadge}
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 1rem;">
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">วันที่</span>
                    <span class="value" style="color: var(--text-primary);">${formatBuddhistDate(h.invoice_date)}</span>
                </div>
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">วันครบกำหนด</span>
                    <span class="value" style="color: var(--text-primary);">${formatBuddhistDate(h.due_date)}</span>
                </div>
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">รหัสลูกค้า</span>
                    <span class="value" style="color: var(--text-primary); font-family: monospace;">${h.customer_code || '-'}</span>
                </div>
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">ชื่อลูกค้า</span>
                    <span class="value" style="color: var(--text-primary);">${h.customer_name || '-'}</span>
                </div>
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">พนักงานขาย</span>
                    <span class="value" style="color: var(--text-primary);">${h.salesperson_code || '-'}</span>
                </div>
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">เครดิต (วัน)</span>
                    <span class="value" style="color: var(--text-primary);">${h.credit_days || '-'}</span>
                </div>
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">ยอดรวม</span>
                    <span class="value price-value" style="color: var(--text-primary);">${formatPrice(h.subtotal || 0)}</span>
                </div>
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">ส่วนลด</span>
                    <span class="value" style="color: var(--text-primary);">${h.discount ? formatPrice(h.discount) : '-'}</span>
                </div>
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">ภาษี (${h.vat_rate || 0}%)</span>
                    <span class="value" style="color: var(--text-primary);">${formatPrice(h.vat_amount || 0)}</span>
                </div>
                <div class="detail-item">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">ยอดสุทธิ</span>
                    <span class="value" style="color: #22c55e; font-size: 1.3rem; font-weight: 700;">${formatPrice(h.grand_total || 0)}</span>
                </div>
                <div class="detail-item" style="grid-column: span 2;">
                    <span class="label" style="font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase;">ที่อยู่จัดส่ง</span>
                    <span class="value" style="color: var(--text-primary);">${h.delivery_address || '-'}</span>
                </div>
            </div>
        `;

        // Render line items
        els.invDetailItemCount.textContent = formatNumber(items.length);

        if (items.length === 0) {
            els.invDetailItemsList.innerHTML = `<tr><td colspan="9" class="text-center py-8 text-muted">ไม่พบรายการสินค้า</td></tr>`;
        } else {
            els.invDetailItemsList.innerHTML = '';
            items.forEach((li, idx) => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${li.line_number || (idx + 1)}</td>
                    <td><div style="font-family: monospace; font-size: 1.05rem;">${li.sku || '-'}</div></td>
                    <td>${li.product_name || '-'}</td>
                    <td>${li.location || '-'}</td>
                    <td class="text-right"><strong>${formatNumber(li.qty || 0)}</strong></td>
                    <td class="text-right">${li.unit_price ? formatPrice(li.unit_price) : '-'}</td>
                    <td class="text-right"><strong>${li.total_price ? formatPrice(li.total_price) : '-'}</strong></td>
                    <td>${li.salesperson_name || '-'}</td>
                    <td><span style="font-family: monospace; font-size: 0.9rem;">${li.or_doc_ref || '-'}</span></td>
                `;
                els.invDetailItemsList.appendChild(tr);
            });
        }
    } catch (err) {
        console.error("Error fetching invoice detail:", err);
        els.invoiceInfoCard.innerHTML = `<p class="text-error">ไม่สามารถโหลดข้อมูลใบกำกับภาษีได้</p>`;
        els.invDetailItemsList.innerHTML = '';
    }
}

// ─── Auto-Sync: Real-time sync status via SSE ─────────────────────────────────
// Connects to the server's SSE endpoint. When source files on Z:\ change, the
// server detects this and runs extraction in the background. The UI gets live
// updates and auto-refreshes affected data when sync completes.

(function initAutoSync() {
    const statusBar = document.getElementById('sync-status-bar');
    const syncDot = document.getElementById('sync-dot');
    const syncLabel = document.getElementById('sync-label');
    const progressText = document.getElementById('sync-progress-text');

    if (!statusBar) return;

    const sourceItems = {
        master: document.querySelector('.sync-item[data-source="master"]'),
        ledger: document.querySelector('.sync-item[data-source="ledger"]'),
        customer: document.querySelector('.sync-item[data-source="customer"]'),
        invoice: document.querySelector('.sync-item[data-source="invoice"]'),
    };

    const sourceDots = {
        master: document.getElementById('sync-dot-master'),
        ledger: document.getElementById('sync-dot-ledger'),
        customer: document.getElementById('sync-dot-customer'),
        invoice: document.getElementById('sync-dot-invoice'),
    };

    const sourceToggles = {
        master: document.getElementById('sync-toggle-master'),
        ledger: document.getElementById('sync-toggle-ledger'),
        customer: document.getElementById('sync-toggle-customer'),
        invoice: document.getElementById('sync-toggle-invoice'),
    };

    // ── Toggle State Management ──────────────────────────────────────────────

    // Load saved toggle states from localStorage
    function loadToggleStates() {
        const saved = localStorage.getItem('syncAutoEnabled');
        if (saved) {
            try {
                return JSON.parse(saved);
            } catch (e) { /* ignore */ }
        }
        // Default: all OFF
        return { master: false, ledger: false, customer: false, invoice: false };
    }

    // Save toggle states to localStorage
    function saveToggleStates(states) {
        localStorage.setItem('syncAutoEnabled', JSON.stringify(states));
    }

    // Apply toggle states to UI checkboxes and item styling
    function applyToggleUI(states) {
        for (const [source, enabled] of Object.entries(states)) {
            const toggle = sourceToggles[source];
            const item = sourceItems[source];
            if (toggle) {
                toggle.checked = enabled;
            }
            if (item) {
                item.classList.toggle('disabled', !enabled);
            }
        }
        updateOverallLabel(states);
    }

    // Update the main label to show how many are enabled
    function updateOverallLabel(states) {
        const enabledCount = Object.values(states).filter(v => v).length;
        if (enabledCount === 0) {
            syncLabel.textContent = 'Auto-Sync';
        } else {
            syncLabel.textContent = `Auto-Sync (${enabledCount}/4)`;
        }
    }

    // Send toggle states to the server
    async function syncConfigToServer(states) {
        try {
            await fetch('/api/sync/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(states),
            });
        } catch (err) {
            console.error('[AutoSync] Failed to sync config to server:', err);
        }
    }

    // Handle toggle change
    function onToggleChange(source, enabled) {
        const states = loadToggleStates();
        states[source] = enabled;
        saveToggleStates(states);
        applyToggleUI(states);
        syncConfigToServer(states);
        console.log(`[AutoSync] ${source} auto-sync ${enabled ? 'ON' : 'OFF'}`);
    }

    // Wire up toggle event listeners
    for (const [source, toggle] of Object.entries(sourceToggles)) {
        if (toggle) {
            toggle.addEventListener('change', (e) => {
                e.stopPropagation(); // Don't trigger the parent click-to-sync
                onToggleChange(source, e.target.checked);
            });
        }
    }

    // Initialize toggles from localStorage for immediate display (before SSE connects).
    // Do NOT push to server here — the server is the source of truth.
    // When SSE 'init' arrives, it will overwrite localStorage with the server's actual state.
    const initialStates = loadToggleStates();
    applyToggleUI(initialStates);

    // ── Source Status UI Updates ──────────────────────────────────────────────

    function updateSourceUI(source, status) {
        const dot = sourceDots[source];
        const item = sourceItems[source];
        if (dot) {
            dot.className = `sync-item-dot ${status}`;
        }
        if (item) {
            // Preserve 'disabled' class based on toggle state
            const states = loadToggleStates();
            const isDisabled = !states[source];
            item.className = `sync-item ${status}${isDisabled ? ' disabled' : ''}`;
        }
    }

    function updateOverallStatus() {
        const allDots = Object.values(sourceDots);
        const anySyncing = allDots.some(d => d && d.classList.contains('syncing'));
        const anyError = allDots.some(d => d && d.classList.contains('error'));

        statusBar.classList.toggle('syncing', anySyncing);
        statusBar.classList.toggle('has-error', anyError);

        const states = loadToggleStates();
        if (anySyncing) {
            syncDot.className = 'sync-dot syncing';
        } else if (anyError) {
            syncDot.className = 'sync-dot error';
        } else {
            syncDot.className = 'sync-dot idle';
        }
        updateOverallLabel(states);
    }

    // Auto-refresh the relevant data views when sync completes.
    // Uses server-provided changes when available (from SSE event payload).
    // Falls back to local snapshot diff if server changes are not provided.
    // Highlights PERSIST until the next sync replaces them.
    async function onSyncDone(source, serverChanges) {
        console.log(`[AutoSync] ${source} sync done — refreshing data...`);
        try {
            const hadPreviousHighlights = state.syncNewProductSkus.size > 0 || state.syncNewMoveKeys.size > 0;

            // ── Refresh data ────────────────────────────────────────────────
            if (source === 'master') {
                await fetchStats();
                if (state.currentTab === 'products') await fetchProducts();
            } else if (source === 'ledger') {
                await fetchStats();
                if (state.currentTab === 'products') await fetchProducts();
                if (state.currentTab === 'moves') await fetchMoves();
            } else if (source === 'customer') {
                await fetchStats();
                if (state.currentTab === 'customer') await fetchCustomers();
            } else if (source === 'invoice') {
                await fetchStats();
                if (state.currentTab === 'invoice') await fetchInvoices();
            }

            // ── Apply changes from server ─────────────────────────────────
            if (source === 'master' || source === 'ledger') {
                const changedSkus = serverChanges?.changed_product_skus || [];
                const newMoveKeysArr = serverChanges?.new_move_keys || [];
                const detTimes = serverChanges?.detection_times || {};

                state.syncNewProductSkus = new Set(changedSkus);
                state.syncNewMoveKeys = new Set(newMoveKeysArr);
                // Merge detection times — keep previous detections from today,
                // add new ones (server already merges, but SSE only sends the
                // latest sync's changes so we merge on the client too).
                for (const [sku, time] of Object.entries(detTimes)) {
                    state.syncDetectionTimes.set(sku, time);
                }

                // Re-render to apply (or clear) highlights
                const needsRerender = changedSkus.length > 0 || newMoveKeysArr.length > 0 || hadPreviousHighlights;
                if (needsRerender && state.currentTab === 'products') renderProducts();
                if (needsRerender && state.currentTab === 'moves') renderMoves();

                if (changedSkus.length > 0) console.log(`[AutoSync] Highlighted ${changedSkus.length} changed product(s)`);
                if (newMoveKeysArr.length > 0) console.log(`[AutoSync] Highlighted ${newMoveKeysArr.length} new move(s)`);
            }

            // ── Disappeared transaction alert ──────────────────────────
            if (serverChanges?.disappeared_count > 0) {
                showDisappearedWarning(
                    serverChanges.disappeared_count,
                    serverChanges.disappeared_transactions || []
                );
            }
        } catch (err) {
            console.error(`[AutoSync] Error refreshing after ${source} sync:`, err);
        }
    }

    // ── SSE Message Handler ──────────────────────────────────────────────────

    function handleSyncMessage(data) {
        try {
            const msg = JSON.parse(data);

            switch (msg.type) {
                case 'init':
                    // Initial state snapshot
                    for (const [source, info] of Object.entries(msg.state || {})) {
                        updateSourceUI(source, info.status || 'idle');
                    }
                    // Sync toggle states from server (in case another tab changed them)
                    if (msg.enabled) {
                        saveToggleStates(msg.enabled);
                        applyToggleUI(msg.enabled);
                    }
                    updateOverallStatus();
                    break;

                case 'config_update':
                    // Another tab or the server changed toggle config
                    if (msg.enabled) {
                        saveToggleStates(msg.enabled);
                        applyToggleUI(msg.enabled);
                    }
                    break;

                case 'sync_start':
                    updateSourceUI(msg.source, 'syncing');
                    progressText.textContent = `${msg.source}: Starting extraction...`;
                    updateOverallStatus();
                    break;

                case 'sync_progress':
                    updateSourceUI(msg.source, 'syncing');
                    progressText.textContent = `${msg.source}: ${msg.progress || '...'}`;
                    updateOverallStatus();
                    break;

                case 'sync_done':
                    updateSourceUI(msg.source, 'done');
                    progressText.textContent = `${msg.source}: ✅ Complete`;
                    updateOverallStatus();
                    onSyncDone(msg.source, msg.changes);
                    setTimeout(() => {
                        updateSourceUI(msg.source, 'idle');
                        progressText.textContent = '';
                        updateOverallStatus();
                    }, 5000);
                    break;

                case 'sync_error':
                    updateSourceUI(msg.source, 'error');
                    progressText.textContent = `${msg.source}: ❌ ${msg.error || 'Error'}`;
                    updateOverallStatus();
                    setTimeout(() => {
                        updateSourceUI(msg.source, 'idle');
                        progressText.textContent = '';
                        updateOverallStatus();
                    }, 10000);
                    break;
            }
        } catch (e) {
            console.error('[AutoSync] Parse error:', e);
        }
    }

    // ── SSE Connection ───────────────────────────────────────────────────────

    let evtSource = null;
    let reconnectTimer = null;

    function connectSSE() {
        if (evtSource) {
            evtSource.close();
        }

        evtSource = new EventSource('/api/sync/events');

        evtSource.onmessage = (event) => {
            handleSyncMessage(event.data);
        };

        evtSource.onerror = () => {
            evtSource.close();
            syncDot.className = 'sync-dot idle';
            syncLabel.textContent = 'Auto-Sync: Reconnecting...';
            clearTimeout(reconnectTimer);
            reconnectTimer = setTimeout(connectSSE, 5000);
        };

        evtSource.onopen = () => {
            console.log('[AutoSync] SSE connected');
            // Server is the source of truth — do NOT push localStorage on reconnect.
            // The 'init' SSE message will send the server's current state to us.
        };
    }

    // ── Click-to-Sync (on dot/label, not on toggle) ─────────────────────────

    for (const [source, item] of Object.entries(sourceItems)) {
        if (item) {
            // Only trigger manual sync when clicking the dot or label, not the toggle
            const dot = sourceDots[source];
            const label = item.querySelector('.sync-item-label');

            const triggerManualSync = async (e) => {
                e.stopPropagation();
                if (dot && dot.classList.contains('syncing')) return;
                try {
                    const res = await fetch(`/api/sync/trigger/${source}`, { method: 'POST' });
                    const data = await res.json();
                    if (!data.success) {
                        console.warn(`[AutoSync] Trigger failed: ${data.message}`);
                    }
                } catch (err) {
                    console.error(`[AutoSync] Trigger error:`, err);
                }
            };

            if (dot) {
                dot.addEventListener('click', triggerManualSync);
                dot.style.cursor = 'pointer';
                dot.title = `Click to manually sync ${source}`;
            }
            if (label) {
                label.addEventListener('click', triggerManualSync);
                label.style.cursor = 'pointer';
                label.title = `Click to manually sync ${source}`;
            }
        }
    }

    // Start SSE connection
    connectSSE();
})();

// ─── Image Hover Preview on Product Table & Modal ──────────────────────────
// Shows full-size image when user hovers over a thumbnail in the product list
// or over the main image in the product modal.
// Uses delegated events so it works with dynamically-rendered rows.
// No extra network requests — reuses the already-cached image.
(function initImageHoverPreview() {
    // Create the preview element once
    const preview = document.createElement('div');
    preview.className = 'image-hover-preview preview-sm';
    preview.innerHTML = '<img>';
    document.body.appendChild(preview);
    const previewImg = preview.querySelector('img');

    let isVisible = false;
    let currentSizeClass = '';

    // Position the preview near the cursor (for small previews) or centered (for large)
    function positionPreview(e) {
        if (currentSizeClass === 'preview-lg') {
            // Full-size: center in viewport
            preview.style.left = '50%';
            preview.style.top = '50%';
            preview.style.transform = 'translate(-50%, -50%) scale(1)';
            return;
        }

        // Small preview: follow cursor
        const gap = 16;
        const vw = window.innerWidth;
        const vh = window.innerHeight;
        const pw = preview.offsetWidth || 400;
        const ph = preview.offsetHeight || 400;

        let x = e.clientX + gap;
        let y = e.clientY - ph / 2;

        // Keep within right edge
        if (x + pw > vw - gap) {
            x = e.clientX - pw - gap;
        }
        // Keep within top/bottom
        if (y < gap) y = gap;
        if (y + ph > vh - gap) y = vh - ph - gap;

        preview.style.left = x + 'px';
        preview.style.top = y + 'px';
        preview.style.transform = 'scale(1)';
    }

    function showPreview(imgSrc, e, sizeClass) {
        previewImg.src = imgSrc;
        currentSizeClass = sizeClass;
        preview.className = `image-hover-preview ${sizeClass}`;
        isVisible = true;
        positionPreview(e);
        requestAnimationFrame(() => preview.classList.add('visible'));
    }

    function hidePreview() {
        isVisible = false;
        currentSizeClass = '';
        preview.classList.remove('visible');
        preview.style.transform = '';
    }

    // ── Product list table thumbnails ──────────────────────────────────
    const productList = document.getElementById('product-list');
    if (productList) {
        productList.addEventListener('mouseenter', (e) => {
            const thumbCell = e.target.closest('.thumb-cell');
            if (!thumbCell) return;
            const img = thumbCell.querySelector('img');
            if (!img) return;
            showPreview(img.src, e, 'preview-sm');
        }, true);

        productList.addEventListener('mouseleave', (e) => {
            const thumbCell = e.target.closest('.thumb-cell');
            if (!thumbCell) return;
            hidePreview();
        }, true);

        productList.addEventListener('mousemove', (e) => {
            if (!isVisible) return;
            positionPreview(e);
        });
    }

    // ── Modal main image ──────────────────────────────────────────────
    const modalMainImg = document.getElementById('modal-main-image');
    if (modalMainImg) {
        modalMainImg.addEventListener('mouseenter', (e) => {
            if (!modalMainImg.src || modalMainImg.style.display === 'none') return;
            showPreview(modalMainImg.src, e, 'preview-lg');
        });

        modalMainImg.addEventListener('mouseleave', () => {
            hidePreview();
        });

        // No mousemove needed for preview-lg since it's centered
    }

    // ── Hide preview when modal closes ────────────────────────────────
    const modal = document.getElementById('product-modal');
    if (modal) {
        const observer = new MutationObserver(() => {
            if (modal.classList.contains('hidden')) {
                hidePreview();
            }
        });
        observer.observe(modal, { attributes: true, attributeFilter: ['class'] });
    }
})();

// ─── Disappeared Transactions Warning Banner ────────────────────────────────

(function initDisappearedWarning() {
    const banner = document.getElementById('disappeared-warning');
    const titleEl = document.getElementById('disappeared-title');
    const detailsEl = document.getElementById('disappeared-details');
    const viewBtn = document.getElementById('disappeared-view-btn');
    const dismissBtn = document.getElementById('disappeared-dismiss-btn');
    const detailList = document.getElementById('disappeared-detail-list');

    if (!banner) return;

    // Dismiss button hides the banner
    if (dismissBtn) {
        dismissBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            banner.classList.add('hidden');
        });
    }

    // View button toggles the detail list
    if (viewBtn) {
        viewBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            if (detailList) {
                detailList.classList.toggle('hidden');
                viewBtn.textContent = detailList.classList.contains('hidden') ? 'ดูรายละเอียด' : 'ซ่อนรายละเอียด';
            }
        });
    }

    // Check on page load if there are disappeared transactions from last sync
    fetch('/api/sync/changes')
        .then(res => res.json())
        .then(data => {
            if (data.disappeared_count > 0) {
                showDisappearedWarning(data.disappeared_count, data.disappeared_transactions || []);
            }
        })
        .catch(() => {});
})();

function showDisappearedWarning(count, transactions) {
    const banner = document.getElementById('disappeared-warning');
    const titleEl = document.getElementById('disappeared-title');
    const detailsEl = document.getElementById('disappeared-details');
    const detailList = document.getElementById('disappeared-detail-list');
    const viewBtn = document.getElementById('disappeared-view-btn');

    if (!banner) return;

    titleEl.textContent = `⚠️ ตรวจพบ ${count} รายการถูกลบจากระบบ ERP เก่า`;
    detailsEl.textContent = `Detected ${count} transaction(s) that previously existed but are now missing from source data.`;

    // Build detail table
    if (detailList && transactions.length > 0) {
        let html = `<table>
            <thead><tr>
                <th>วันที่</th><th>เอกสาร</th><th>Part Code</th>
                <th>ประเภท</th><th>รับเข้า</th><th>จ่ายออก</th>
            </tr></thead><tbody>`;

        transactions.forEach(t => {
            html += `<tr>
                <td>${t.date || '-'}</td>
                <td>${t.doc_ref || '-'}</td>
                <td>${t.part_code || '-'}</td>
                <td style="font-family: var(--font-sans);">${t.category_name || '-'}</td>
                <td>${t.qty_in || 0}</td>
                <td>${t.qty_out || 0}</td>
            </tr>`;
        });

        if (count > transactions.length) {
            html += `<tr><td colspan="6" class="more-label">... และอีก ${count - transactions.length} รายการ (ดูทั้งหมดที่ /api/disappeared-transactions)</td></tr>`;
        }

        html += '</tbody></table>';
        detailList.innerHTML = html;
        detailList.classList.add('hidden'); // Start collapsed
        if (viewBtn) viewBtn.textContent = 'ดูรายละเอียด';
    } else if (detailList) {
        detailList.innerHTML = '';
        detailList.classList.add('hidden');
    }

    banner.classList.remove('hidden');
    console.log(`[AutoSync] ⚠️ Showing disappeared warning: ${count} transaction(s)`);
}

// ─── Authentication System ──────────────────────────────────────────────────
// Handles login overlay, session check, logout, and admin user management.

/** Current user info — set after successful auth check. */
let _currentUser = null;

/**
 * Entry point: check if user is authenticated.
 * If already logged in, show app directly.
 * If not, auto-login as guest so the app loads without a login wall.
 * Users can still manually log in via the header button to get admin access.
 */
async function authCheckAndInit() {
    const overlay = document.getElementById('login-overlay');
    const appEl = document.getElementById('app');
    overlay.classList.add('hidden');
    appEl.style.display = '';

    try {
        const res = await fetch('/api/auth/me');
        if (res.ok) {
            _currentUser = await res.json();
            _showUserUI();
            init();
        } else {
            // Not authenticated — auto-login as guest silently
            await _autoGuestLogin();
        }
    } catch (err) {
        console.error('[Auth] Error checking session:', err);
        // Network error — still try guest login
        await _autoGuestLogin();
    }
}

/**
 * Silently log in as guest so the app works without a login wall.
 */
async function _autoGuestLogin() {
    const appEl = document.getElementById('app');
    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: 'guest', password: 'guest' })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            _currentUser = data.user;
            _showUserUI();
            init();
        } else {
            // Guest login failed — still show app (some features may not work)
            console.warn('[Auth] Auto guest login failed:', data.error);
            _currentUser = { username: 'guest', role: 'viewer' };
            _showUserUI();
            init();
        }
    } catch (err) {
        console.error('[Auth] Auto guest login error:', err);
        // Still show app even if auth fails entirely
        _currentUser = { username: 'guest', role: 'viewer' };
        _showUserUI();
        init();
    }
}

/**
 * Show the login overlay manually (triggered from header "Login" button).
 */
function _showLoginOverlay() {
    const overlay = document.getElementById('login-overlay');
    overlay.classList.remove('hidden');
    _setupLoginHandlers();
    // Focus the username field
    const usernameInput = document.getElementById('login-username');
    if (usernameInput) usernameInput.focus();
}

/** Flag to prevent double-binding login listeners. */
let _loginHandlersBound = false;

function _setupLoginHandlers() {
    if (_loginHandlersBound) return;
    _loginHandlersBound = true;

    const form = document.getElementById('login-form');
    const guestBtn = document.getElementById('login-guest-btn');
    const errorDiv = document.getElementById('login-error');
    const submitBtn = document.getElementById('login-submit-btn');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('login-username').value.trim();
        const password = document.getElementById('login-password').value;
        errorDiv.classList.add('hidden');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Logging in...';

        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });
            const data = await res.json();
            if (res.ok && data.success) {
                // Reload the page to fully reset UI with new user permissions
                location.reload();
            } else {
                errorDiv.textContent = data.error || 'Login failed';
                errorDiv.classList.remove('hidden');
                submitBtn.disabled = false;
                submitBtn.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg> Login`;
            }
        } catch (err) {
            errorDiv.textContent = 'Connection error. Is the server running?';
            errorDiv.classList.remove('hidden');
            submitBtn.disabled = false;
            submitBtn.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M15 3h4a2 2 0 012 2v14a2 2 0 01-2 2h-4"/><polyline points="10 17 15 12 10 7"/><line x1="15" y1="12" x2="3" y2="12"/></svg> Login`;
        }
    });

    // Guest login button
    guestBtn.addEventListener('click', async () => {
        errorDiv.classList.add('hidden');
        guestBtn.disabled = true;
        guestBtn.textContent = 'Logging in as guest...';

        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: 'guest', password: 'guest' })
            });
            const data = await res.json();
            if (res.ok && data.success) {
                // Reload the page to fully reset UI with new user permissions
                location.reload();
            } else {
                errorDiv.textContent = data.error || 'Guest login failed';
                errorDiv.classList.remove('hidden');
                guestBtn.disabled = false;
                guestBtn.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg> Login as Guest`;
            }
        } catch (err) {
            errorDiv.textContent = 'Connection error';
            errorDiv.classList.remove('hidden');
            guestBtn.disabled = false;
            guestBtn.innerHTML = `<svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2"/><circle cx="12" cy="7" r="4"/></svg> Login as Guest`;
        }
    });
}


/**
 * Show user badge, admin button, and logout button in the navbar.
 */
let _userUIBound = false;
function _showUserUI() {
    if (!_currentUser) return;

    const badge = document.getElementById('user-badge');
    const loginHeaderBtn = document.getElementById('login-header-btn');
    const adminBtn = document.getElementById('admin-panel-btn');
    const logoutBtn = document.getElementById('logout-btn');

    // Show user badge
    badge.textContent = _currentUser.username;
    badge.classList.remove('hidden');

    // For guest users, show the "Login" button so they can authenticate
    // For authenticated (non-guest) users, hide it
    if (_currentUser.username === 'guest') {
        loginHeaderBtn.classList.remove('hidden');
    } else {
        loginHeaderBtn.classList.add('hidden');
    }

    // Show admin panel button only for admin users
    if (_currentUser.role === 'admin' && !_userUIBound) {
        adminBtn.classList.remove('hidden');
        adminBtn.addEventListener('click', _openAdminPanel);
    }

    // Logout button (shown for non-guest authenticated users)
    if (_currentUser.username !== 'guest') {
        logoutBtn.classList.remove('hidden');
    } else {
        logoutBtn.classList.add('hidden');
    }

    if (!_userUIBound) {
        // Login header button opens the login overlay
        loginHeaderBtn.addEventListener('click', _showLoginOverlay);

        // Logout button
        logoutBtn.addEventListener('click', async () => {
            try {
                await fetch('/api/auth/logout', { method: 'POST' });
            } catch (e) { /* ignore */ }
            location.reload();
        });
    }

    // ── Admin-only: Refresh buttons & Auto-Sync controls ──────────────────
    const isAdmin = _currentUser.role === 'admin';

    // Disable/enable the 4 refresh buttons in the navbar
    const refreshBtnIds = ['refresh-invoice-btn', 'refresh-customer-btn', 'refresh-master-btn', 'refresh-ledger-btn'];
    refreshBtnIds.forEach(id => {
        const btn = document.getElementById(id);
        if (btn) {
            btn.disabled = !isAdmin;
            btn.classList.toggle('admin-only-disabled', !isAdmin);
            if (!isAdmin) btn.title = 'Admin only';
        }
    });

    // Disable/enable the 4 auto-sync toggles
    const syncToggleIds = ['sync-toggle-master', 'sync-toggle-ledger', 'sync-toggle-customer', 'sync-toggle-invoice'];
    syncToggleIds.forEach(id => {
        const toggle = document.getElementById(id);
        if (toggle) {
            toggle.disabled = !isAdmin;
            const label = toggle.closest('.sync-toggle');
            if (label) label.classList.toggle('admin-only-disabled', !isAdmin);
        }
    });

    // Disable/enable click-to-sync dots & labels in the sync status bar
    document.querySelectorAll('.sync-item-dot, .sync-item-label').forEach(el => {
        if (!isAdmin) {
            el.style.pointerEvents = 'none';
            el.style.cursor = 'default';
            el.title = 'Admin only';
        } else {
            el.style.pointerEvents = '';
            el.style.cursor = 'pointer';
        }
    });

    _userUIBound = true;
}


// ─── Admin Panel ────────────────────────────────────────────────────────────

function _openAdminPanel() {
    const modal = document.getElementById('admin-modal');
    modal.classList.remove('hidden');
    _loadAdminUsers();
    _loadBackupList();
    _loadWatcherDebugState();
    _loadImagePermissions();
    _setupAdminHandlers();

    // Close button
    document.getElementById('admin-close-btn').onclick = () => modal.classList.add('hidden');
    modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.classList.add('hidden');
    });
}

let _adminHandlersBound = false;

function _setupAdminHandlers() {
    if (_adminHandlersBound) return;
    _adminHandlersBound = true;

    // Add user
    document.getElementById('admin-add-btn').addEventListener('click', async () => {
        const username = document.getElementById('admin-new-username').value.trim();
        const password = document.getElementById('admin-new-password').value;
        const role = document.getElementById('admin-new-role').value;
        const errDiv = document.getElementById('admin-add-error');
        errDiv.classList.add('hidden');

        if (!username || !password) {
            errDiv.textContent = 'Username and password required';
            errDiv.classList.remove('hidden');
            return;
        }

        try {
            const res = await fetch('/api/admin/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password, role })
            });
            const data = await res.json();
            if (res.ok && data.success) {
                document.getElementById('admin-new-username').value = '';
                document.getElementById('admin-new-password').value = '';
                _loadAdminUsers();
            } else {
                errDiv.textContent = data.error || 'Failed to create user';
                errDiv.classList.remove('hidden');
            }
        } catch (err) {
            errDiv.textContent = 'Connection error';
            errDiv.classList.remove('hidden');
        }
    });

    // Change own password
    document.getElementById('admin-change-pw-btn').addEventListener('click', async () => {
        const currentPw = document.getElementById('admin-current-pw').value;
        const newPw = document.getElementById('admin-new-pw').value;
        const msgDiv = document.getElementById('admin-pw-msg');

        if (!currentPw || !newPw) {
            msgDiv.textContent = 'Both fields required';
            msgDiv.style.color = '#fca5a5';
            msgDiv.classList.remove('hidden');
            return;
        }

        try {
            const res = await fetch('/api/auth/change-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ current_password: currentPw, new_password: newPw })
            });
            const data = await res.json();
            if (res.ok && data.success) {
                msgDiv.textContent = '✓ Password updated successfully';
                msgDiv.style.color = '#10b981';
                document.getElementById('admin-current-pw').value = '';
                document.getElementById('admin-new-pw').value = '';
            } else {
                msgDiv.textContent = data.error || 'Failed to change password';
                msgDiv.style.color = '#fca5a5';
            }
            msgDiv.classList.remove('hidden');
        } catch (err) {
            msgDiv.textContent = 'Connection error';
            msgDiv.style.color = '#fca5a5';
            msgDiv.classList.remove('hidden');
        }
    });

    // ── Backup Handlers ──────────────────────────────────────────────────

    // Create backup button
    document.getElementById('backup-create-btn').addEventListener('click', _createBackup);

    // Auto-backup toggle
    document.getElementById('backup-auto-toggle').addEventListener('change', async (e) => {
        const enabled = e.target.checked;
        try {
            await fetch('/api/admin/backup/schedule', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ auto_backup: enabled })
            });
            _showBackupStatus(enabled ? 'Auto daily backup enabled' : 'Auto daily backup disabled', 'success');
        } catch (err) {
            _showBackupStatus('Failed to update setting', 'error');
            e.target.checked = !enabled; // Revert toggle
        }
    });

    // Watcher debug toggle
    document.getElementById('watcher-debug-toggle').addEventListener('change', async (e) => {
        const enabled = e.target.checked;
        try {
            await fetch('/api/sync/config', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ watcher_debug: enabled })
            });
            console.log(`[Sync] Watcher debug logging ${enabled ? 'enabled' : 'disabled'}`);
        } catch (err) {
            console.error('[Sync] Failed to update watcher debug setting', err);
            e.target.checked = !enabled; // Revert toggle
        }
    });

    // Cooldown settings (debounced save on change)
    let _cooldownSaveTimer = null;
    const saveCooldownSetting = async (key, value) => {
        // Debounce: wait 600ms after last change before saving
        clearTimeout(_cooldownSaveTimer);
        _cooldownSaveTimer = setTimeout(async () => {
            try {
                const payload = {};
                payload[key] = parseInt(value, 10);
                await fetch('/api/sync/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                const msg = document.getElementById('cooldown-save-msg');
                if (msg) {
                    msg.classList.remove('hidden');
                    clearTimeout(msg._hideTimer);
                    msg._hideTimer = setTimeout(() => msg.classList.add('hidden'), 2000);
                }
                console.log(`[Sync] Cooldown ${key} updated to ${value}`);
            } catch (err) {
                console.error(`[Sync] Failed to update cooldown ${key}`, err);
            }
        }, 600);
    };

    document.getElementById('cooldown-threshold-input').addEventListener('change', (e) => {
        saveCooldownSetting('cooldown_threshold', e.target.value);
    });
    document.getElementById('cooldown-seconds-input').addEventListener('change', (e) => {
        saveCooldownSetting('cooldown_seconds', e.target.value);
    });
}


async function _loadAdminUsers() {
    const tbody = document.getElementById('admin-user-list');
    try {
        const res = await fetch('/api/admin/users');
        const users = await res.json();
        if (!Array.isArray(users)) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center">Error loading users</td></tr>';
            return;
        }
        tbody.innerHTML = users.map(u => `
            <tr>
                <td><strong>${escapeHtml(u.username)}</strong></td>
                <td><span class="badge">${escapeHtml(u.role)}</span></td>
                <td style="font-size: 0.85rem; color: var(--text-secondary);">${escapeHtml(u.created_at || '-')}</td>
                <td class="text-right">
                    <button class="btn btn-outline btn-compact" onclick="_adminResetPassword(${u.id}, '${escapeHtml(u.username)}')" title="Reset password" style="margin-right:0.25rem;">
                        Reset PW
                    </button>
                    <button class="btn btn-outline btn-compact" onclick="_adminDeleteUser(${u.id}, '${escapeHtml(u.username)}')" title="Delete user" style="border-color: rgba(239,68,68,0.4); color: #fca5a5;">
                        Delete
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center">Failed to load users</td></tr>';
    }
}

async function _adminDeleteUser(userId, username) {
    if (!confirm(`Delete user "${username}"?`)) return;
    try {
        const res = await fetch(`/api/admin/users/${userId}`, { method: 'DELETE' });
        const data = await res.json();
        if (res.ok && data.success) {
            _loadAdminUsers();
        } else {
            alert(data.error || 'Failed to delete user');
        }
    } catch (err) {
        alert('Connection error');
    }
}

async function _adminResetPassword(userId, username) {
    const newPw = prompt(`Enter new password for "${username}":`);
    if (!newPw) return;
    try {
        const res = await fetch(`/api/admin/users/${userId}/reset-password`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: newPw })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            alert(`Password for "${username}" has been reset.`);
        } else {
            alert(data.error || 'Failed to reset password');
        }
    } catch (err) {
        alert('Connection error');
    }
}


// ─── Backup Management Functions ────────────────────────────────────────────

function _showBackupStatus(message, type) {
    const el = document.getElementById('backup-status-msg');
    if (!el) return;
    el.textContent = message;
    el.classList.remove('hidden');
    el.style.background = type === 'error' ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)';
    el.style.color = type === 'error' ? '#fca5a5' : '#6ee7b7';
    // Auto-hide after 5s
    clearTimeout(el._hideTimer);
    el._hideTimer = setTimeout(() => el.classList.add('hidden'), 5000);
}

async function _loadWatcherDebugState() {
    const toggle = document.getElementById('watcher-debug-toggle');
    const thresholdInput = document.getElementById('cooldown-threshold-input');
    const secondsInput = document.getElementById('cooldown-seconds-input');
    try {
        const res = await fetch('/api/sync/config');
        const data = await res.json();
        if (toggle) toggle.checked = !!data.watcher_debug;
        if (thresholdInput) thresholdInput.value = data.cooldown_threshold || 3;
        if (secondsInput) secondsInput.value = data.cooldown_seconds || 120;
    } catch (err) {
        console.error('[Sync] Failed to load sync settings', err);
    }
}

let _permHandlersBound = false;
async function _loadImagePermissions() {
    try {
        const res = await fetch('/api/permissions');
        const perms = await res.json();

        const uploadViewer = document.getElementById('perm-upload-viewer');
        const deleteViewer = document.getElementById('perm-delete-viewer');

        if (uploadViewer) uploadViewer.checked = perms.custom_image_upload.includes('viewer');
        if (deleteViewer) deleteViewer.checked = perms.custom_image_delete.includes('viewer');

        if (!_permHandlersBound) {
            _permHandlersBound = true;

            const savePerms = async () => {
                const payload = {
                    custom_image_upload: ['admin'].concat(uploadViewer?.checked ? ['viewer'] : []),
                    custom_image_delete: ['admin'].concat(deleteViewer?.checked ? ['viewer'] : []),
                };
                try {
                    const r = await fetch('/api/permissions', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload),
                    });
                    const d = await r.json();
                    const msg = document.getElementById('perm-save-msg');
                    if (d.success && msg) {
                        msg.textContent = '✓ Saved';
                        msg.classList.remove('hidden');
                        setTimeout(() => msg.classList.add('hidden'), 2000);
                    }
                } catch (e) {
                    console.error('[Perms] save error', e);
                }
            };

            [uploadViewer, deleteViewer].forEach(el => {
                if (el) el.addEventListener('change', savePerms);
            });
        }
    } catch (err) {
        console.error('[Perms] load error', err);
    }
}

async function _loadBackupList() {
    const tbody = document.getElementById('backup-list');
    const autoToggle = document.getElementById('backup-auto-toggle');
    if (!tbody) return;

    try {
        const res = await fetch('/api/admin/backups');
        const data = await res.json();

        // Set auto-backup toggle state
        if (autoToggle) {
            autoToggle.checked = data.auto_backup;
        }

        const backups = data.backups || [];
        if (backups.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center" style="padding: 1rem; color: var(--text-secondary);">No backups yet. Click "Create Backup Now" to create one.</td></tr>';
            return;
        }

        tbody.innerHTML = backups.map(b => {
            const safetyBadge = b.is_safety ? ' <span style="font-size:0.7rem; padding:0.1rem 0.3rem; background:rgba(251,191,36,0.2); color:#fbbf24; border-radius:3px;">safety</span>' : '';
            return `<tr>
                <td style="font-family: monospace; font-size: 0.75rem;">${escapeHtml(b.filename)}${safetyBadge}</td>
                <td class="text-right" style="white-space: nowrap;">${b.size_mb} MB</td>
                <td style="white-space: nowrap; font-size: 0.75rem;">${escapeHtml(b.created_at)}</td>
                <td class="text-right" style="white-space: nowrap;">
                    <button class="btn btn-outline btn-compact" onclick="_backupRestore('${escapeHtml(b.filename)}')" title="Restore this backup" style="font-size: 0.7rem; margin-right: 0.2rem; border-color: rgba(251,191,36,0.4); color: #fbbf24;">
                        Restore
                    </button>
                    <button class="btn btn-outline btn-compact" onclick="_backupDownload('${escapeHtml(b.filename)}')" title="Download" style="font-size: 0.7rem; margin-right: 0.2rem;">
                        ↓
                    </button>
                    <button class="btn btn-outline btn-compact" onclick="_backupDelete('${escapeHtml(b.filename)}')" title="Delete" style="font-size: 0.7rem; border-color: rgba(239,68,68,0.4); color: #fca5a5;">
                        ✕
                    </button>
                </td>
            </tr>`;
        }).join('');
    } catch (err) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center" style="color: #fca5a5;">Failed to load backups</td></tr>';
    }
}

async function _createBackup() {
    const btn = document.getElementById('backup-create-btn');
    const origHTML = btn.innerHTML;
    btn.disabled = true;
    btn.textContent = 'Creating...';

    try {
        const res = await fetch('/api/admin/backup', { method: 'POST' });
        const data = await res.json();
        if (res.ok && data.success) {
            _showBackupStatus(`Backup created: ${data.filename}`, 'success');
            _loadBackupList();
        } else {
            _showBackupStatus(data.error || 'Backup failed', 'error');
        }
    } catch (err) {
        _showBackupStatus('Connection error', 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = origHTML;
    }
}

async function _backupRestore(filename) {
    if (!confirm(`⚠️ RESTORE DATABASE from backup:\n\n${filename}\n\nThis will replace the current database. A safety backup will be created first.\n\nAre you sure?`)) return;
    if (!confirm('This is a DESTRUCTIVE operation. Are you absolutely sure?')) return;

    try {
        const res = await fetch('/api/admin/backup/restore', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename })
        });
        const data = await res.json();
        if (res.ok && data.success) {
            alert(`Database restored from: ${data.restored_from}\nSafety backup: ${data.safety_backup}\n\nThe page will now reload.`);
            location.reload();
        } else {
            _showBackupStatus(data.error || 'Restore failed', 'error');
        }
    } catch (err) {
        _showBackupStatus('Connection error during restore', 'error');
    }
}

function _backupDownload(filename) {
    window.open(`/api/admin/backup/download/${encodeURIComponent(filename)}`, '_blank');
}

async function _backupDelete(filename) {
    if (!confirm(`Delete backup "${filename}"?`)) return;

    try {
        const res = await fetch(`/api/admin/backup/${encodeURIComponent(filename)}`, { method: 'DELETE' });
        const data = await res.json();
        if (res.ok && data.success) {
            _showBackupStatus('Backup deleted', 'success');
            _loadBackupList();
        } else {
            _showBackupStatus(data.error || 'Delete failed', 'error');
        }
    } catch (err) {
        _showBackupStatus('Connection error', 'error');
    }
}
