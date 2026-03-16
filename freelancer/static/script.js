/* ============================================================
   UNITARY X — realistic_hud_engine.js
   Physical Interaction & System Diagnostics Logic
   ============================================================ */

(() => {
    'use strict';

    const CONFIG = {
        gridSize: 50,
        mouseRadius: 250,
        parallaxPower: 40,
        cursorLag: 0.15
    };

    const state = {
        mouse: { x: window.innerWidth / 2, y: window.innerHeight / 2 },
        cursorPos: { x: 0, y: 0 },
        elements: {},
        ctx: null,
        nodes: []
    };

    // ── INITIALIZATION ──────────────────────────────────────────

    const init = () => {
        cacheElements();
        initCanvas();
        initParallax();
        initDiagnostics();
        initCursor();
        attachAuthEvents();
    };

    const cacheElements = () => {
        state.elements = {
            canvas: document.getElementById('x-canvas'),
            panel: document.getElementById('x-panel'),
            cursorM: document.getElementById('x-cursor-m'),
            cursorO: document.getElementById('x-cursor-o'),
            form: document.getElementById('x-form'),
            diagLoad: document.getElementById('diag-load'),
            diagMs: document.getElementById('diag-ms')
        };
    };

    // ── HUD VECTOR CANVAS ───────────────────────────────────────

    const initCanvas = () => {
        const { canvas } = state.elements;
        if (!canvas) return;

        state.ctx = canvas.getContext('2d');
        
        const resize = () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
            createGrid();
        };

        const createGrid = () => {
            state.nodes = [];
            const cols = Math.ceil(canvas.width / CONFIG.gridSize) + 1;
            const rows = Math.ceil(canvas.height / CONFIG.gridSize) + 1;

            for (let i = 0; i < cols; i++) {
                for (let j = 0; j < rows; j++) {
                    state.nodes.push({
                        bx: i * CONFIG.gridSize,
                        by: j * CONFIG.gridSize,
                        x: i * CONFIG.gridSize,
                        y: j * CONFIG.gridSize,
                        a: Math.random() * 0.2
                    });
                }
            }
        };

        const draw = () => {
            const { ctx, canvas: c } = state;
            ctx.clearRect(0, 0, c.width, c.height);

            // Draw Vector Distortions
            state.nodes.forEach(node => {
                const dx = state.mouse.x - node.bx;
                const dy = state.mouse.y - node.by;
                const d = Math.sqrt(dx * dx + dy * dy);
                
                if (d < CONFIG.mouseRadius) {
                    const f = (CONFIG.mouseRadius - d) / CONFIG.mouseRadius;
                    node.x = node.bx - dx * f * 0.3;
                    node.y = node.by - dy * f * 0.3;
                } else {
                    node.x += (node.bx - node.x) * 0.1;
                    node.y += (node.by - node.y) * 0.1;
                }

                ctx.fillStyle = d < 150 ? `rgba(0, 242, 255, 0.4)` : `rgba(255, 255, 255, ${node.a})`;
                ctx.beginPath();
                ctx.arc(node.x, node.y, 1, 0, Math.PI * 2);
                ctx.fill();
            });

            requestAnimationFrame(draw);
        };

        window.addEventListener('resize', resize);
        resize();
        draw();
    };

    // ── ADVANCED PARALLAX & CURSOR ──────────────────────────────

    const initParallax = () => {
        const { panel } = state.elements;
        if (!panel) return;

        window.addEventListener('mousemove', (e) => {
            const x = (window.innerWidth / 2 - e.clientX) / CONFIG.parallaxPower;
            const y = (window.innerHeight / 2 - e.clientY) / -CONFIG.parallaxPower;

            panel.style.transform = `rotateY(${x}deg) rotateX(${y}deg)`;
            panel.style.setProperty('--mouse-x', `${(e.clientX / window.innerWidth) * 100}%`);
            panel.style.setProperty('--mouse-y', `${(e.clientY / window.innerHeight) * 100}%`);
        });
    };

    const initCursor = () => {
        const { cursorM, cursorO } = state.elements;
        if (!cursorM) return;

        const updateCursor = () => {
            // Smooth lagging ring
            state.cursorPos.x += (state.mouse.x - state.cursorPos.x) * CONFIG.cursorLag;
            state.cursorPos.y += (state.mouse.y - state.cursorPos.y) * CONFIG.cursorLag;

            cursorO.style.left = `${state.cursorPos.x}px`;
            cursorO.style.top = `${state.cursorPos.y}px`;
            
            // Fast pinpoint
            cursorM.style.left = `${state.mouse.x}px`;
            cursorM.style.top = `${state.mouse.y}px`;

            requestAnimationFrame(updateCursor);
        };

        window.addEventListener('mousemove', (e) => {
            state.mouse.x = e.clientX;
            state.mouse.y = e.clientY;
        });

        updateCursor();
    };

    // ── SYSTEM DIAGNOSTICS LOGIC ───────────────────────────────

    const initDiagnostics = () => {
        const { diagLoad, diagMs } = state.elements;
        
        setInterval(() => {
            if (diagLoad) diagLoad.innerText = `${(Math.random() * 10 + 40).toFixed(1)}%`;
            if (diagMs) diagMs.innerText = `${(Math.random() * 0.05 + 0.01).toFixed(2)}ms`;
        }, 2000);
    };

    // ── AUTH EVENTS ─────────────────────────────────────────────

    const attachAuthEvents = () => {
        const { form, panel } = state.elements;
        if (!form) return;

        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            const btn = document.getElementById('x-btn');
            const alert = document.getElementById('x-alert');
            const alertMsg = document.getElementById('x-alert-msg');
            
            btn.disabled = true;
            btn.querySelector('.x-btn-label').innerText = 'VALIDATING_CREDENTIALS...';
            btn.style.opacity = '0.5';

            const formData = new FormData(form);
            try {
                const response = await fetch(form.action, {
                    method: 'POST',
                    body: formData,
                    headers: { 'X-Requested-With': 'XMLHttpRequest' }
                });
                const data = await response.json();

                if (data.success) {
                    btn.style.background = '#00ff9d';
                    btn.querySelector('.x-btn-label').innerText = 'AUTH_GRANTED';
                    setTimeout(() => window.location.href = data.redirect, 1000);
                } else {
                    btn.style.background = '#ff3e3e';
                    btn.querySelector('.x-btn-label').innerText = 'AUTH_DENIED';
                    
                    // Show HUD Alert
                    alertMsg.innerText = `FAILURE: ${data.error.toUpperCase()}`;
                    alert.classList.add('active');
                    panel.animate([
                        { transform: 'translateZ(50px) translateX(-5px)' },
                        { transform: 'translateZ(50px) translateX(5px)' },
                        { transform: 'translateZ(50px) translateX(0)' }
                    ], { duration: 100, iterations: 3 });

                    setTimeout(() => {
                        btn.disabled = false;
                        btn.style.background = '';
                        btn.style.opacity = '1';
                        btn.querySelector('.x-btn-label').innerText = 'INITIATE_AUTH';
                        alert.classList.remove('active');
                    }, 3000);
                }
            } catch (err) {
                console.error("Critical Auth Fault", err);
            }
        });
    };

    init();
})();
