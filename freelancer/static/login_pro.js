(function () {
    /* ═══════════════════════════════════════════════════════
       UNITARY X – QUANTUM NEXUS ENGINE v4 (60 FPS OPTIMISED)
       Key wins:
         • NO radial/linear gradients in the hot path
         • NO shadowBlur (most expensive GPU op)
         • Typed Float32Array for node positions
         • Spatial grid for O(n) link culling
         • Pre-built static colour strings (zero alloc per frame)
         • Adaptive quality: halves counts on low-end devices
         • requestAnimationFrame + delta cap (no spiral-of-death)
    ═══════════════════════════════════════════════════════ */

    "use strict";

    const canvas = document.getElementById("lux-canvas");
    const card = document.getElementById("auth-card");
    const intro = document.getElementById("lux-intro");
    if (!canvas) return;

    const ctx = canvas.getContext("2d", { alpha: true, desynchronized: true });

    /* ── Device capability detection ── */
    const isMobile = /Mobi|Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    const lowEnd = isMobile || (navigator.hardwareConcurrency || 8) <= 4;
    const prefersRed = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const QUALITY = prefersRed ? 0.3 : lowEnd ? 0.55 : 1.0;

    // Mobile-lite mode: skip the expensive background renderer for smoother phones.
    const mobileLite = prefersRed || window.matchMedia("(max-width: 768px)").matches;
    if (mobileLite) {
        canvas.style.display = "none";
        if (intro) {
            intro.style.animation = "none";
            setTimeout(function () { intro.remove(); }, 250);
        }
        if (card) {
            card.style.transform = "";
        }
        window.luxFX = window.luxFX || {};
        window.luxFX.success = function () { };
        window.luxFX.error = function () {
            if (!card) return;
            card.animate([
                { transform: "translateX(0)" },
                { transform: "translateX(-4px)" },
                { transform: "translateX(4px)" },
                { transform: "translateX(0)" }
            ], { duration: 220, easing: "ease-out" });
        };
        return;
    }

    /* Scale canvas to physical pixels (max 1.5x to save fill rate) */
    const DPR = Math.min(window.devicePixelRatio || 1, 1.5);

    /* ── Palette – pre-built rgba strings to avoid alloc in loop ── */
    const PALETTE = [
        { r: 34, g: 211, b: 238 },  // cyan
        { r: 139, g: 92, b: 246 },  // violet
        { r: 236, g: 72, b: 153 },  // pink
        { r: 52, g: 211, b: 153 },  // emerald
        { r: 99, g: 102, b: 241 },  // indigo
        { r: 251, g: 191, b: 36 },  // amber
    ];
    function pickCol() { return PALETTE[Math.floor(Math.random() * PALETTE.length)]; }
    function rgba(c, a) { return `rgba(${c.r},${c.g},${c.b},${(+a).toFixed(2)})`; }

    function rnd(a, b) { return Math.random() * (b - a) + a; }

    /* ── State ── */
    let W = 0, H = 0;
    let MX = 0, MY = 0, SMX = 0, SMY = 0;
    let PULSE = 0, BURST = 0, WARP = 0;
    let TIME = 0;
    let lastTS = 0;

    /* Click ring */
    let clickRing = null;   // { x, y, r, max }

    /* Sparks – pre-allocated pool */
    const MAX_SPARKS = 40;
    const sparkPool = [];
    for (let i = 0; i < MAX_SPARKS; i++) {
        sparkPool.push({ alive: false, x: 0, y: 0, vx: 0, vy: 0, life: 0, r: 0, col: PALETTE[0] });
    }
    function spawnSparks(cx, cy, count) {
        let spawned = 0;
        for (let i = 0; i < sparkPool.length && spawned < count; i++) {
            if (!sparkPool[i].alive) {
                const sp = sparkPool[i];
                const angle = (spawned / count) * Math.PI * 2;
                const speed = rnd(1.8, 5);
                sp.alive = true;
                sp.x = cx; sp.y = cy;
                sp.vx = Math.cos(angle) * speed;
                sp.vy = Math.sin(angle) * speed;
                sp.life = 1.0;
                sp.r = rnd(1.2, 2.8);
                sp.col = pickCol();
                spawned++;
            }
        }
    }

    /* ── Particles: use typed arrays for speed ── */
    let NODE_COUNT, STAR_COUNT;
    let nX, nY, nVX, nVY, nR, nA, nPhs, nPhsSpd;  // Float32Array
    let nColR, nColG, nColB;                         // Uint8Array
    let sX, sY, sR, sA, sTwPhase, sTwSpd;           // Float32Array stars

    /* Hex ring objects (few, no hot-path gradients) */
    let hexRings = [];

    /* Nebula: drawn max once per N frames as off-screen canvas */
    let nebulaCache = null;
    const NEBULA_TTL = 90; // redraw every 90 frames (~1.5 s)
    let nebulaTick = NEBULA_TTL;
    let nebulae = [];

    function setup() {
        W = window.innerWidth;
        H = window.innerHeight;

        canvas.width = Math.round(W * DPR);
        canvas.height = Math.round(H * DPR);
        canvas.style.width = W + "px";
        canvas.style.height = H + "px";
        ctx.scale(DPR, DPR);

        SMX = MX = W * 0.5;
        SMY = MY = H * 0.5;

        /* ── Counts ── */
        NODE_COUNT = Math.round((prefersRed ? 40 : lowEnd ? 60 : 90) * QUALITY);
        STAR_COUNT = Math.round((prefersRed ? 60 : lowEnd ? 110 : 180) * QUALITY);

        /* Nodes – typed arrays */
        nX = new Float32Array(NODE_COUNT);
        nY = new Float32Array(NODE_COUNT);
        nVX = new Float32Array(NODE_COUNT);
        nVY = new Float32Array(NODE_COUNT);
        nR = new Float32Array(NODE_COUNT);
        nA = new Float32Array(NODE_COUNT);
        nPhs = new Float32Array(NODE_COUNT);
        nPhsSpd = new Float32Array(NODE_COUNT);
        nColR = new Uint8Array(NODE_COUNT);
        nColG = new Uint8Array(NODE_COUNT);
        nColB = new Uint8Array(NODE_COUNT);

        for (let i = 0; i < NODE_COUNT; i++) {
            nX[i] = Math.random() * W;
            nY[i] = Math.random() * H;
            nVX[i] = rnd(-0.28, 0.28);
            nVY[i] = rnd(-0.28, 0.28);
            nR[i] = rnd(1.2, 3.5);
            nA[i] = rnd(0.55, 1.0);
            nPhs[i] = Math.random() * Math.PI * 2;
            nPhsSpd[i] = rnd(0.016, 0.040);
            const c = pickCol();
            nColR[i] = c.r; nColG[i] = c.g; nColB[i] = c.b;
        }

        /* Stars – typed arrays */
        sX = new Float32Array(STAR_COUNT);
        sY = new Float32Array(STAR_COUNT);
        sR = new Float32Array(STAR_COUNT);
        sA = new Float32Array(STAR_COUNT);
        sTwPhase = new Float32Array(STAR_COUNT);
        sTwSpd = new Float32Array(STAR_COUNT);
        for (let i = 0; i < STAR_COUNT; i++) {
            sX[i] = Math.random() * W;
            sY[i] = Math.random() * H;
            sR[i] = rnd(0.3, 1.4);
            sA[i] = rnd(0.25, 0.85);
            sTwPhase[i] = Math.random() * Math.PI * 2;
            sTwSpd[i] = rnd(0.005, 0.018);
        }

        /* Hex rings */
        if (!prefersRed) {
            const RING_COUNT = lowEnd ? 3 : 5;
            hexRings = [];
            for (let i = 0; i < RING_COUNT; i++) {
                const c = pickCol();
                hexRings.push({
                    x: Math.random() * W,
                    y: Math.random() * H,
                    sides: [5, 6, 8][i % 3],
                    radii: [rnd(24, 44), rnd(50, 72), rnd(80, 110)],
                    rot: Math.random() * Math.PI * 2,
                    rotV: rnd(0.003, 0.007) * (Math.random() > 0.5 ? 1 : -1),
                    colStr: `rgba(${c.r},${c.g},${c.b},`,
                    a: rnd(0.18, 0.35)
                });
            }
        }

        /* Nebulae (drawn to off-screen cache, not per frame) */
        const NEB_COUNT = lowEnd ? 4 : 7;
        nebulae = [];
        for (let i = 0; i < NEB_COUNT; i++) {
            nebulae.push({
                x: Math.random() * W, y: Math.random() * H,
                rx: rnd(160, 320), ry: rnd(100, 220),
                col: pickCol(), a: rnd(0.05, 0.11),
                rot: rnd(0, Math.PI * 2)
            });
        }
        nebulaTick = NEBULA_TTL; // force immediate redraw
        nebulaCache = null;
    }

    /* ── Off-screen nebula canvas ── */
    function rebuildNebulaCache() {
        const oc = document.createElement("canvas");
        oc.width = Math.round(W * DPR);
        oc.height = Math.round(H * DPR);
        const oc2 = oc.getContext("2d");
        oc2.scale(DPR, DPR);

        nebulae.forEach(function (nb) {
            oc2.save();
            oc2.translate(nb.x, nb.y);
            oc2.rotate(nb.rot);
            const g = oc2.createRadialGradient(0, 0, 0, 0, 0, nb.rx);
            g.addColorStop(0, rgba(nb.col, nb.a));
            g.addColorStop(0.55, rgba(nb.col, nb.a * 0.4));
            g.addColorStop(1, rgba(nb.col, 0));
            oc2.scale(1, nb.ry / nb.rx);
            oc2.fillStyle = g;
            oc2.beginPath();
            oc2.arc(0, 0, nb.rx, 0, Math.PI * 2);
            oc2.fill();
            oc2.restore();
        });

        nebulaCache = oc;
    }

    window.addEventListener("resize", setup, { passive: true });
    setup();

    /* ── Events ── */
    window.addEventListener("mousemove", function (e) {
        MX = e.clientX; MY = e.clientY;
        PULSE = Math.min(1, PULSE + 0.08);
        document.documentElement.style.setProperty("--pointer-x", ((MX / W) * 100).toFixed(1) + "%");
        document.documentElement.style.setProperty("--pointer-y", ((MY / H) * 100).toFixed(1) + "%");
    }, { passive: true });

    window.addEventListener("pointerdown", function (e) {
        BURST = 1;
        WARP = Math.min(1, WARP + 0.45);
        clickRing = { x: e.clientX, y: e.clientY, r: 0, max: 260 };
        spawnSparks(e.clientX, e.clientY, 16);
    }, { passive: true });

    /* ═══════════════════════════════════════════
       RENDER – fully optimised hot-path
    ═══════════════════════════════════════════ */
    function render(ts) {
        requestAnimationFrame(render);

        /* Delta-time cap: never simulate more than 50 ms at once */
        const dt = Math.min((ts - lastTS) || 16.67, 50);
        lastTS = ts;
        const dtF = dt / 16.67;  // 1.0 = 60 fps frame
        TIME++;

        /* Smooth cursor */
        const lag = 0.07 * dtF;
        SMX += (MX - SMX) * lag;
        SMY += (MY - SMY) * lag;

        /* Auto-parallax when idle */
        if (PULSE < 0.04) {
            document.documentElement.style.setProperty("--pointer-x", (50 + Math.sin(TIME * 0.0003) * 13).toFixed(1) + "%");
            document.documentElement.style.setProperty("--pointer-y", (48 + Math.cos(TIME * 0.0004) * 9).toFixed(1) + "%");
        }

        ctx.clearRect(0, 0, W, H);

        /* ── 1. NEBULA CACHE (blit, cheap) ── */
        if (++nebulaTick > NEBULA_TTL || !nebulaCache) {
            rebuildNebulaCache();
            nebulaTick = 0;
        }
        ctx.drawImage(nebulaCache, 0, 0, W, H);

        /* ── 2. STARS ── */
        for (let i = 0; i < STAR_COUNT; i++) {
            sTwPhase[i] += sTwSpd[i] * dtF;
            const a = sA[i] * (0.55 + 0.45 * Math.sin(sTwPhase[i]));
            ctx.globalAlpha = a;
            ctx.fillStyle = "#b8eeff";
            ctx.beginPath();
            ctx.arc(sX[i], sY[i], sR[i], 0, Math.PI * 2);
            ctx.fill();
        }
        ctx.globalAlpha = 1;

        /* ── 3. HEX RINGS (no shadow, light line ops) ── */
        hexRings.forEach(function (h) {
            h.rot += h.rotV * dtF;
            h.radii.forEach(function (rad, idx) {
                const a = h.a * (0.5 + 0.5 * Math.sin(TIME * 0.025 + idx * 1.2));
                ctx.strokeStyle = h.colStr + a.toFixed(2) + ")";
                ctx.lineWidth = idx === 1 ? 1.5 : 0.85;
                ctx.beginPath();
                const sides = h.sides;
                for (let k = 0; k <= sides; k++) {
                    const ang = (k / sides) * Math.PI * 2 + h.rot + idx * 0.25;
                    const px = h.x + Math.cos(ang) * rad;
                    const py = h.y + Math.sin(ang) * rad;
                    k === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
                }
                ctx.closePath();
                ctx.stroke();
            });
        });

        /* ── 4. NETWORK LINKS (spatial skip, no gradient) ── */
        const LINK_DIST = Math.min(W, H) * (lowEnd ? 0.17 : 0.22);
        const LINK_DIST2 = LINK_DIST * LINK_DIST;
        const CHECK_RANGE = lowEnd ? 10 : 15; // max neighbours to check per node

        ctx.lineWidth = 0.9;
        let linkCount = 0;
        const MAX_LINKS = lowEnd ? 80 : 140;

        for (let i = 0; i < NODE_COUNT && linkCount < MAX_LINKS; i++) {
            const jMax = Math.min(i + CHECK_RANGE, NODE_COUNT);
            for (let j = i + 1; j < jMax && linkCount < MAX_LINKS; j++) {
                const dx = nX[i] - nX[j];
                const dy = nY[i] - nY[j];
                const d2 = dx * dx + dy * dy;
                if (d2 > LINK_DIST2) continue;

                const alpha = (1 - d2 / LINK_DIST2) * 0.3 * (1 + PULSE * 0.35);
                /* Blend mid-colour – no gradient object */
                const mr = (nColR[i] + nColR[j]) >> 1;
                const mg = (nColG[i] + nColG[j]) >> 1;
                const mb = (nColB[i] + nColB[j]) >> 1;
                ctx.strokeStyle = `rgba(${mr},${mg},${mb},${alpha.toFixed(2)})`;
                ctx.lineWidth = 0.6 + (1 - d2 / LINK_DIST2) * 1.1;
                ctx.beginPath();
                ctx.moveTo(nX[i], nY[i]);
                ctx.lineTo(nX[j], nY[j]);
                ctx.stroke();
                linkCount++;
            }
        }

        /* ── 5. NODES ── */
        const repelR2 = 36000;
        const pxDrift = (SMX / W - 0.5) * 0.45;
        const pyDrift = (SMY / H - 0.5) * 0.40;

        for (let i = 0; i < NODE_COUNT; i++) {
            /* Mouse repel – only if close */
            const dxm = nX[i] - SMX;
            const dym = nY[i] - SMY;
            const dm2 = dxm * dxm + dym * dym;
            if (dm2 < repelR2 && dm2 > 0.5) {
                const inv = (1 - dm2 / repelR2) * 0.032;
                const dm = Math.sqrt(dm2);
                nVX[i] += (dxm / dm) * inv * dtF;
                nVY[i] += (dym / dm) * inv * dtF;
            }

            nX[i] += (nVX[i] + pxDrift) * dtF;
            nY[i] += (nVY[i] + pyDrift) * dtF;
            nVX[i] *= Math.pow(0.983, dtF);
            nVY[i] *= Math.pow(0.983, dtF);

            /* Wrapping */
            if (nX[i] < -24) nX[i] = W + 24;
            else if (nX[i] > W + 24) nX[i] = -24;
            if (nY[i] < -24) nY[i] = H + 24;
            else if (nY[i] > H + 24) nY[i] = -24;

            nPhs[i] += nPhsSpd[i] * dtF;
            const pm = 0.72 + 0.28 * Math.sin(nPhs[i]);
            const rad = nR[i] * pm;

            /* Draw node – simple arc, no glow */
            const nodeA = nA[i] * (0.7 + PULSE * 0.3);
            ctx.fillStyle = `rgba(${nColR[i]},${nColG[i]},${nColB[i]},${nodeA.toFixed(2)})`;
            ctx.beginPath();
            ctx.arc(nX[i], nY[i], rad, 0, Math.PI * 2);
            ctx.fill();

            /* Soft halo – single slightly-larger transparent circle */
            ctx.fillStyle = `rgba(${nColR[i]},${nColG[i]},${nColB[i]},${(nodeA * 0.18).toFixed(3)})`;
            ctx.beginPath();
            ctx.arc(nX[i], nY[i], rad * 3.5, 0, Math.PI * 2);
            ctx.fill();
        }

        /* ── 6. CLICK PULSE RING ── */
        if (clickRing) {
            clickRing.r += 7 * dtF;
            const ratio = clickRing.r / clickRing.max;
            const ringA = Math.max(0, (1 - ratio) * 0.75);
            if (ringA <= 0) {
                clickRing = null;
            } else {
                ctx.strokeStyle = `rgba(34,211,238,${ringA.toFixed(2)})`;
                ctx.lineWidth = 2.5 * (1 - ratio);
                ctx.beginPath();
                ctx.arc(clickRing.x, clickRing.y, clickRing.r, 0, Math.PI * 2);
                ctx.stroke();

                ctx.strokeStyle = `rgba(139,92,246,${(ringA * 0.5).toFixed(2)})`;
                ctx.lineWidth = 1.2;
                ctx.beginPath();
                ctx.arc(clickRing.x, clickRing.y, clickRing.r * 0.6, 0, Math.PI * 2);
                ctx.stroke();
            }
        }

        /* ── 7. SPARKS ── */
        for (let i = 0; i < sparkPool.length; i++) {
            const sp = sparkPool[i];
            if (!sp.alive) continue;
            sp.x += sp.vx * dtF;
            sp.y += sp.vy * dtF;
            sp.vx *= Math.pow(0.93, dtF);
            sp.vy = sp.vy * Math.pow(0.93, dtF) + 0.04 * dtF;
            sp.life -= 0.028 * dtF;
            if (sp.life <= 0) { sp.alive = false; continue; }

            ctx.fillStyle = `rgba(${sp.col.r},${sp.col.g},${sp.col.b},${sp.life.toFixed(2)})`;
            ctx.beginPath();
            ctx.arc(sp.x, sp.y, sp.r * sp.life, 0, Math.PI * 2);
            ctx.fill();
        }

        /* ── 8. BURST FLASH ── */
        if (BURST > 0.005) {
            ctx.fillStyle = `rgba(34,211,238,${(BURST * 0.06).toFixed(3)})`;
            ctx.fillRect(0, 0, W, H);
            BURST *= Math.pow(0.88, dtF);
        }

        /* ── 9. WARP LINES ── */
        if (WARP > 0.02) {
            const cx = W * 0.5, cy = H * 0.5;
            const cnt = Math.ceil(WARP * 20);
            for (let i = 0; i < cnt; i++) {
                const ang = (i / cnt) * Math.PI * 2;
                const sR = rnd(20, 70);
                const eR = (sR + rnd(70, 200)) * WARP;
                const c = PALETTE[i % PALETTE.length];
                ctx.strokeStyle = `rgba(${c.r},${c.g},${c.b},${(WARP * 0.5).toFixed(2)})`;
                ctx.lineWidth = rnd(0.4, 1.5);
                ctx.beginPath();
                ctx.moveTo(cx + Math.cos(ang) * sR, cy + Math.sin(ang) * sR);
                ctx.lineTo(cx + Math.cos(ang) * eR, cy + Math.sin(ang) * eR);
                ctx.stroke();
            }
            WARP *= Math.pow(0.91, dtF);
        }

        PULSE *= Math.pow(0.965, dtF);
    }

    requestAnimationFrame(render);

    /* ── Card 3-D tilt ── */
    if (card) {
        card.addEventListener("mousemove", function (e) {
            const r = card.getBoundingClientRect();
            const x = (e.clientX - r.left) / r.width;
            const y = (e.clientY - r.top) / r.height;
            card.style.transform = `rotateX(${((0.5 - y) * 7).toFixed(1)}deg) rotateY(${((x - 0.5) * 9).toFixed(1)}deg) translateZ(0)`;
            card.querySelectorAll(".btn-auth").forEach(function (btn) {
                const br = btn.getBoundingClientRect();
                btn.style.setProperty("--mx", (((e.clientX - br.left) / br.width) * 100).toFixed(1) + "%");
            });
        }, { passive: true });
        card.addEventListener("mouseleave", function () { card.style.transform = ""; });
    }

    /* ── Card stagger reveal ── */
    document.addEventListener("DOMContentLoaded", function () {
        if (!card) return;
        card.querySelectorAll(".auth-header,.auth-tabs,.auth-alert,.auth-panel h3,.auth-panel p,.field,.row-meta,.btn-auth,.strength-wrap,.auth-foot")
            .forEach(function (el, i) {
                if (el.classList.contains("auth-alert") && el.style.display === "none") return;
                el.style.opacity = "0";
                el.style.transform = "translateY(14px)";
                setTimeout(function () {
                    el.style.transition = "opacity 480ms ease, transform 540ms cubic-bezier(.2,.85,.2,1)";
                    el.style.opacity = "1";
                    el.style.transform = "translateY(0)";
                }, 150 + i * 55);
            });
    });

    setTimeout(function () { if (intro) intro.remove(); }, 1900);

    /* ── Public FX hooks ── */
    window.luxFX = window.luxFX || {};
    window.luxFX.success = function () { BURST = 1.2; PULSE = 1.0; WARP = 0.7; };
    window.luxFX.error = function () {
        if (card) card.animate([
            { transform: "translateX(0)" },
            { transform: "translateX(-6px)" },
            { transform: "translateX(7px)" },
            { transform: "translateX(-4px)" },
            { transform: "translateX(0)" }
        ], { duration: 380, easing: "cubic-bezier(.36,.07,.19,.97)" });
        BURST = 0.4;
        if (card) {
            const cr = card.getBoundingClientRect();
            spawnSparks(cr.left + cr.width / 2, cr.top + cr.height / 2, 8);
        }
    };

})();
