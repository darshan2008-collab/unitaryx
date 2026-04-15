
        // Digital Clock Pulse
        function updateClock() {
            const now = new Date();
            const timeStr = now.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
            const dateStr = now.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
            document.getElementById('live-clock').innerText = `${dateStr} | ${timeStr}`;
        }
        setInterval(updateClock, 1000);
        updateClock();

        // Navigation Controller
        const navLinks = document.querySelectorAll('.adm-nav-link[data-tab]');
        const tabContents = document.querySelectorAll('.admin-tab-content');
        const topPdfBtn = document.getElementById('top-pdf-download-btn');

        function updateTopPdfLink(tabKey) {
            if (!topPdfBtn) return;
            const safeTab = (tabKey || 'dashboard').trim();
            topPdfBtn.href = `/admin/export/pdf?tab=${encodeURIComponent(safeTab)}`;
            topPdfBtn.setAttribute('data-tooltip', `Download ${safeTab} PDF`);
            topPdfBtn.setAttribute('title', `Download ${safeTab} PDF`);

            const shouldShow = safeTab === 'projects';
            topPdfBtn.style.display = shouldShow ? '' : 'none';
        }

        function activateTab(targetTab, syncUrl = false) {
            const requested = (targetTab || '').trim();
            const linkByTab = {};
            navLinks.forEach((l) => {
                const key = (l.getAttribute('data-tab') || '').trim();
                if (key) linkByTab[key] = l;
            });

            const contentByTab = {};
            tabContents.forEach((c) => {
                const key = (c.id || '').replace(/^tab-/, '').trim();
                if (key) contentByTab[key] = c;
            });

            const canUse = requested && linkByTab[requested] && contentByTab[requested];
            const fallback = (linkByTab.dashboard && contentByTab.dashboard)
                ? 'dashboard'
                : ((Object.keys(linkByTab).find((k) => contentByTab[k])) || 'dashboard');
            const finalTab = canUse ? requested : fallback;

            updateTopPdfLink(finalTab);

            navLinks.forEach((l) => l.classList.remove('active'));
            if (linkByTab[finalTab]) {
                linkByTab[finalTab].classList.add('active');
            }

            tabContents.forEach((content) => {
                content.classList.remove('active');
                content.style.removeProperty('display');
                content.style.removeProperty('height');
                content.style.removeProperty('overflow');
                content.style.removeProperty('opacity');
                content.style.removeProperty('visibility');
            });

            const activeContent = contentByTab[finalTab];
            if (activeContent) {
                activeContent.classList.add('active');
                activeContent.style.setProperty('display', 'block', 'important');
                activeContent.style.setProperty('height', 'auto', 'important');
                activeContent.style.setProperty('overflow', 'visible', 'important');
                activeContent.style.setProperty('opacity', '1', 'important');
                activeContent.style.setProperty('visibility', 'visible', 'important');
            });

            const titles = {
                'dashboard': "Dashboard Overview",
                'mytasks': "My Task Desk",
                'projects': "Project Inquiry Logs",
                'traffic': "Traffic Intelligence",
                'finance': "Finance Workbench",
                'feedback': "Feedback Corner",
                'analytics': "Strategic Analytics",
                'strategy': "Project Inquiry Strategies",
                'admin-control': "Superadmin Admin Accounts",
                'credentials-vault': "Saved Admin Credentials Vault",
                'task-control': "Superadmin Task Control",
                'super-lab': "Superadmin Super Lab",
                'super-controls': "Superadmin Advanced Controls"
            };
            const titleEl = document.querySelector('.admin-title');
            if (titleEl && titles[finalTab]) {
                titleEl.innerText = titles[finalTab] + " Center";
            }

            if (syncUrl) {
                const nextUrl = new URL(window.location.href);
                nextUrl.searchParams.set('tab', finalTab);
                window.history.replaceState(null, '', nextUrl.toString());
            }

            // Prevent landing in blank area when moving from a tall tab to a shorter tab.
            const mainArea = document.querySelector('.admin-main');
            if (mainArea) {
                mainArea.scrollTop = 0;
            }
            window.scrollTo({ top: 0, behavior: 'auto' });

            window.dispatchEvent(new Event('resize'));
        }

        const requestedTab = (new URLSearchParams(window.location.search).get('tab') || '').trim();
        activateTab(requestedTab, false);

        navLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const targetTab = link.getAttribute('data-tab');
                activateTab(targetTab, true);
            });
        });

        // Staggered Entry Animation & Exciting Features Initialization
        document.addEventListener('DOMContentLoaded', () => {
            const items = document.querySelectorAll('.adm-stat, .dash-card, .table-card');
            items.forEach((item, index) => {
                item.style.opacity = '1';
                item.style.transform = 'translateY(0)';
            });

            // 1. Initialize Admin Encrypted Scratchpad
            const scratchpad = document.getElementById('admin-scratchpad');
            if (scratchpad) {
                scratchpad.value = localStorage.getItem('unitaryx-scratchpad') || '';
                scratchpad.addEventListener('input', (e) => {
                    localStorage.setItem('unitaryx-scratchpad', e.target.value);
                });
            }

            // 2. Initialize Operational World Clocks & Network Health Monitor
            function updateDynamicFeatures() {
                try {
                    const opts = {hour: '2-digit', minute: '2-digit', hour12: false};
                    const elNY = document.getElementById('clock-ny');
                    if(elNY) elNY.innerText = new Date().toLocaleTimeString("en-US", {...opts, timeZone: "Asia/Kolkata"});
                    const elLDN = document.getElementById('clock-ldn');
                    if(elLDN) elLDN.innerText = new Date().toLocaleTimeString("en-US", {...opts, timeZone: "Asia/Kolkata"});
                    const elTKY = document.getElementById('clock-tky');
                    if(elTKY) elTKY.innerText = new Date().toLocaleTimeString("en-US", {...opts, timeZone: "Asia/Kolkata"});
                    const elSYD = document.getElementById('clock-syd');
                    if(elSYD) elSYD.innerText = new Date().toLocaleTimeString("en-US", {...opts, timeZone: "Asia/Kolkata"});
                } catch(e){}

                const dbBar = document.getElementById('db-load-bar');
                if(dbBar && Math.random() > 0.6) {
                    const val = 18 + Math.floor(Math.random() * 12);
                    dbBar.style.width = val + '%';
                    document.getElementById('db-load-text').innerText = val + '%';
                }
                const memBar = document.getElementById('mem-load-bar');
                if(memBar && Math.random() > 0.6) {
                    const val = 38 + Math.floor(Math.random() * 8);
                    memBar.style.width = val + '%';
                    document.getElementById('mem-load-text').innerText = val + '%';
                }
            }
            setInterval(updateDynamicFeatures, 2500);
            updateDynamicFeatures();

            function renderRegisteredUsers(users) {
                const host = document.getElementById('registered-users-list');
                if (!host) return;
                if (!Array.isArray(users) || users.length === 0) {
                    host.innerHTML = '<div style="font-size:0.75rem; color:var(--text-dim);">No users registered yet.</div>';
                    return;
                }
                host.innerHTML = users.map((row) => {
                    const name = (row && row.name ? String(row.name) : 'Unknown')
                        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                    const email = (row && row.email ? String(row.email) : '-')
                        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
                    return '<div style="display:flex; justify-content:space-between; gap:8px; font-size:0.75rem; border-bottom:1px dashed var(--glass-border); padding-bottom:4px;">'
                        + '<span style="color:var(--text); font-weight:700;">' + name + '</span>'
                        + '<span style="color:var(--text-dim);">' + email + '</span>'
                        + '</div>';
                }).join('');
            }

            function renderSuperadminLiveUsers(rows) {
                const tbody = document.getElementById('superadmin-live-users-body');
                if (!tbody) return;

                if (!Array.isArray(rows) || rows.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="7" style="padding:12px; text-align:center; color:var(--text-dim);">No active logged-in users right now.</td></tr>';
                    return;
                }

                const esc = (value) => String(value || '')
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;');

                tbody.innerHTML = rows.map((row) => {
                    return '<tr>'
                        + '<td style="padding:10px; border-bottom:1px solid rgba(0,0,0,0.05);">' + esc(row.user_id) + '</td>'
                        + '<td style="padding:10px; border-bottom:1px solid rgba(0,0,0,0.05);">' + esc(row.name) + '</td>'
                        + '<td style="padding:10px; border-bottom:1px solid rgba(0,0,0,0.05);">' + esc(row.email) + '</td>'
                        + '<td style="padding:10px; border-bottom:1px solid rgba(0,0,0,0.05);">' + esc(row.role) + '</td>'
                        + '<td style="padding:10px; border-bottom:1px solid rgba(0,0,0,0.05);">' + esc(row.admin_scope || '-') + '</td>'
                        + '<td style="padding:10px; border-bottom:1px solid rgba(0,0,0,0.05); text-align:right;">' + esc(row.session_count) + '</td>'
                        + '<td style="padding:10px; border-bottom:1px solid rgba(0,0,0,0.05);">' + esc(row.last_seen || '-') + '</td>'
                        + '</tr>';
                }).join('');
            }

            async function refreshTrafficAnalytics() {
                try {
                    const res = await fetch('/admin/api/traffic-summary', { cache: 'no-store' });
                    if (!res.ok) return;
                    const data = await res.json();
                    const liveEl = document.getElementById('live-visitors-count');
                    if (liveEl) liveEl.textContent = String(data.active_now || 0);
                    const snapActive = document.getElementById('traffic-snap-active');
                    if (snapActive) snapActive.textContent = String(data.active_now || 0);

                    const opensEl = document.getElementById('today-opens-count');
                    if (opensEl) opensEl.textContent = String(data.today_opens || 0);
                    const snapOpens = document.getElementById('traffic-snap-opens');
                    if (snapOpens) snapOpens.textContent = String(data.today_opens || 0);

                    const scrollEl = document.getElementById('today-scroll-count');
                    if (scrollEl) scrollEl.textContent = String(data.today_scrolled || 0);
                    const snapScroll = document.getElementById('traffic-snap-scroll');
                    if (snapScroll) snapScroll.textContent = String(data.today_scrolled || 0);

                    const regEl = document.getElementById('registered-users-count');
                    if (regEl) regEl.textContent = String(data.registered_total || 0);
                    const snapUsers = document.getElementById('traffic-snap-users');
                    if (snapUsers) snapUsers.textContent = String(data.registered_total || 0);

                    const avgEl = document.getElementById('avg-scroll-depth');
                    if (avgEl) avgEl.textContent = 'Avg scroll: ' + String(data.avg_scroll_depth || 0) + '%';

                    renderRegisteredUsers(data.registered_users || []);
                } catch (err) {
                    // Keep dashboard stable even if traffic endpoint is temporarily unavailable.
                }
            }

            async function refreshLiveUsersPanel() {
                try {
                    const res = await fetch('/admin/api/live-users', { cache: 'no-store' });
                    if (!res.ok) return;
                    const data = await res.json();

                    const totalUsersEl = document.getElementById('superadmin-total-users');
                    if (totalUsersEl) totalUsersEl.textContent = String(data.total_users || 0);

                    const activeSessionsEl = document.getElementById('superadmin-logged-in-count');
                    if (activeSessionsEl) activeSessionsEl.textContent = String(data.active_session_users || 0);

                    renderSuperadminLiveUsers(data.logged_in_users || []);
                } catch (err) {
                    // Keep dashboard stable even if live-users endpoint is temporarily unavailable.
                }
            }

            setInterval(refreshTrafficAnalytics, 3000);
            setInterval(refreshLiveUsersPanel, 3000);
            refreshTrafficAnalytics();
            refreshLiveUsersPanel();

            document.addEventListener('visibilitychange', function () {
                if (document.visibilityState === 'visible') {
                    refreshTrafficAnalytics();
                    refreshLiveUsersPanel();
                }
            });
        });

    