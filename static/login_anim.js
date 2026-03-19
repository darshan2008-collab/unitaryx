// Cinematic AI login enhancement engine
(function () {
    const body = document.body;
    if (!body) return;

    body.classList.add("preload");
    const reveal = document.createElement("div");
    reveal.className = "screen-reveal";
    body.appendChild(reveal);
    setTimeout(() => body.classList.remove("preload"), 180);
    setTimeout(() => reveal.remove(), 1600);

    const state = {
        mouseX: window.innerWidth * 0.5,
        mouseY: window.innerHeight * 0.5,
        mx: 0.5,
        my: 0.5,
        smoothMx: 0.5,
        smoothMy: 0.5,
        pressure: 0,
        boost: 0,
        errorPulse: 0,
        corePulse: 0
    };

    const reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const hw = navigator.hardwareConcurrency || 4;
    const mem = navigator.deviceMemory || 4;
    const perfTier = Math.min(1.45, Math.max(0.72, (hw / 8) * 0.65 + (mem / 8) * 0.35));

    // Keep native cursor behavior (no custom cursor halo).
    const halo = null;

    const corePulseLayer = document.createElement("div");
    corePulseLayer.className = "ai-core-pulse";
    body.appendChild(corePulseLayer);

    window.addEventListener("mousemove", (e) => {
        state.mouseX = e.clientX;
        state.mouseY = e.clientY;
        state.mx = e.clientX / Math.max(window.innerWidth, 1);
        state.my = e.clientY / Math.max(window.innerHeight, 1);
        state.pressure = Math.min(1, state.pressure + 0.06);
        state.corePulse = Math.min(1, state.corePulse + 0.05);
        body.style.setProperty("--mx", String(state.mx));
        body.style.setProperty("--my", String(state.my));
        body.style.setProperty("--depth-x", ((state.mx - 0.5) * 15).toFixed(2) + "px");
        body.style.setProperty("--depth-y", ((state.my - 0.5) * 15).toFixed(2) + "px");
        if (halo) {
            halo.style.left = e.clientX + "px";
            halo.style.top = e.clientY + "px";
            halo.classList.add("active");
        }
    });

    window.addEventListener("mouseout", () => {
        if (halo) halo.classList.remove("active");
    });

    // Holographic card depth and parallax
    const card = document.querySelector(".card-panel");
    if (card) {
        card.classList.add("holo");
        card.addEventListener("mousemove", () => {
            state.boost = Math.min(1, state.boost + 0.12);
        });
    }

    // Neural particle system with layered depth + dynamic lines
    const canvas = document.getElementById("login-particles");
    if (canvas) {
        const ctx = canvas.getContext("2d", { alpha: true });
        let w = 0;
        let h = 0;
        const cellSize = 100;
        const particles = [];

        const layers = [
            { countScale: 0.52, speed: 0.14, size: [0.35, 1.15], alpha: [0.10, 0.24], depth: 0.3 },
            { countScale: 0.32, speed: 0.22, size: [0.65, 1.6], alpha: [0.14, 0.30], depth: 0.58 },
            { countScale: 0.16, speed: 0.34, size: [0.95, 2.25], alpha: [0.18, 0.38], depth: 0.95 }
        ];

        function rand(min, max) {
            return Math.random() * (max - min) + min;
        }

        function resize() {
            w = canvas.width = window.innerWidth;
            h = canvas.height = window.innerHeight;
            particles.length = 0;
            const baseRaw = Math.floor((w * h) / 2550);
            const base = Math.min(2200, Math.max(520, Math.floor(baseRaw * perfTier * (reduceMotion ? 0.6 : 1))));
            layers.forEach((layer, layerIdx) => {
                const count = Math.floor(base * layer.countScale);
                for (let i = 0; i < count; i += 1) {
                    particles.push({
                        x: Math.random() * w,
                        y: Math.random() * h,
                        vx: rand(-layer.speed, layer.speed),
                        vy: rand(-layer.speed, layer.speed),
                        ax: 0,
                        ay: 0,
                        size: rand(layer.size[0], layer.size[1]),
                        alpha: rand(layer.alpha[0], layer.alpha[1]),
                        hue: rand(204, 218),
                        depth: layer.depth,
                        layer: layerIdx
                    });
                }
            });
        }

        resize();
        window.addEventListener("resize", resize);

        function draw(t) {
            ctx.clearRect(0, 0, w, h);
            state.smoothMx += (state.mx - state.smoothMx) * 0.08;
            state.smoothMy += (state.my - state.smoothMy) * 0.08;
            body.style.setProperty("--smx", String(state.smoothMx));
            body.style.setProperty("--smy", String(state.smoothMy));

            corePulseLayer.style.opacity = (0.58 + state.corePulse * 0.35).toFixed(3);
            const grid = new Map();
            const repelR = 190;
            const attractR = 360;
            const repelR2 = repelR * repelR;
            const attractR2 = attractR * attractR;

            // update pass
            for (let i = 0; i < particles.length; i += 1) {
                const p = particles[i];
                p.ax = 0;
                p.ay = 0;

                const dx = p.x - state.mouseX;
                const dy = p.y - state.mouseY;
                const d2 = dx * dx + dy * dy;

                if (d2 < repelR2 && d2 > 8) {
                    const f = (1 - d2 / repelR2) * 0.45;
                    p.ax += (dx / Math.sqrt(d2)) * f;
                    p.ay += (dy / Math.sqrt(d2)) * f;
                } else if (d2 < attractR2 && d2 > repelR2) {
                    const f = (1 - d2 / attractR2) * 0.02;
                    p.ax -= (dx / Math.sqrt(d2)) * f;
                    p.ay -= (dy / Math.sqrt(d2)) * f;
                }

                const breathing = Math.sin((t * 0.0003) + p.layer + state.corePulse) * 0.024;
                p.vx = (p.vx + p.ax) * (0.975 + breathing);
                p.vy = (p.vy + p.ay) * (0.975 + breathing);
                p.x += p.vx + (state.smoothMx - 0.5) * p.depth * 0.46;
                p.y += p.vy + (state.smoothMy - 0.5) * p.depth * 0.40;

                if (p.x < -20) p.x = w + 20;
                if (p.x > w + 20) p.x = -20;
                if (p.y < -20) p.y = h + 20;
                if (p.y > h + 20) p.y = -20;

                const gx = Math.floor(p.x / cellSize);
                const gy = Math.floor(p.y / cellSize);
                const key = gx + ":" + gy;
                if (!grid.has(key)) grid.set(key, []);
                grid.get(key).push(i);
            }

            // line pass
            const maxDist = 152;
            const maxDist2 = maxDist * maxDist;
            for (let i = 0; i < particles.length; i += 1) {
                const p = particles[i];
                const gx = Math.floor(p.x / cellSize);
                const gy = Math.floor(p.y / cellSize);
                let links = 0;
                for (let ox = -1; ox <= 1; ox += 1) {
                    for (let oy = -1; oy <= 1; oy += 1) {
                        const key = (gx + ox) + ":" + (gy + oy);
                        const cell = grid.get(key);
                        if (!cell) continue;
                        for (let ci = 0; ci < cell.length; ci += 1) {
                            const j = cell[ci];
                            if (j <= i) continue;
                            if (links > (reduceMotion ? 4 : 8)) break;
                            const q = particles[j];
                            const dx = p.x - q.x;
                            const dy = p.y - q.y;
                            const d2 = dx * dx + dy * dy;
                            if (d2 > maxDist2) continue;
                            const intensity = 1 - (d2 / maxDist2);
                            const hover = Math.max(0, 1 - (((p.x - state.mouseX) ** 2 + (p.y - state.mouseY) ** 2) / (220 * 220)));
                            const a = intensity * (0.10 + hover * 0.34 + state.errorPulse * 0.28 + state.corePulse * 0.22);
                            ctx.strokeStyle = "rgba(52,130,246," + a.toFixed(3) + ")";
                            ctx.lineWidth = 0.45 + intensity * 0.75;
                            ctx.beginPath();
                            ctx.moveTo(p.x, p.y);
                            ctx.lineTo(q.x, q.y);
                            ctx.stroke();
                            links += 1;
                        }
                    }
                }
            }

            // particle pass
            for (let i = 0; i < particles.length; i += 1) {
                const p = particles[i];
                const glow = Math.max(0, 1 - (((p.x - state.mouseX) ** 2 + (p.y - state.mouseY) ** 2) / (260 * 260)));
                const alpha = Math.min(1, p.alpha + glow * 0.50 + state.boost * 0.12 + state.errorPulse * 0.18 + state.corePulse * 0.15);
                ctx.fillStyle = "hsla(" + p.hue.toFixed(0) + ", 88%, 64%, " + alpha.toFixed(3) + ")";
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.size + glow * 0.9 + state.corePulse * 0.2, 0, Math.PI * 2);
                ctx.fill();
            }

            state.pressure *= 0.97;
            state.boost *= 0.94;
            state.errorPulse *= 0.92;
            state.corePulse *= 0.985;
            requestAnimationFrame(draw);
        }

        requestAnimationFrame(draw);

        // expose feedback hooks for form success/error
        window.loginFX = window.loginFX || {};
        window.loginFX.onError = function onError() {
            state.errorPulse = 1;
            state.corePulse = Math.min(1, state.corePulse + 0.25);
        };
        window.loginFX.onSuccess = function onSuccess() {
            state.boost = 1;
            state.corePulse = 1;
        };
    }

    // Staggered reveal sequence
    function stagedReveal() {
        const items = document.querySelectorAll(".panel-title, .panel-sub, .auth-form .field, .submit-btn");
        items.forEach((el, index) => {
            el.style.opacity = "0";
            el.style.transform = "translateY(16px)";
            el.style.filter = "blur(8px)";
            setTimeout(() => {
                el.style.transition = "opacity 480ms ease, transform 520ms cubic-bezier(0.2,0.85,0.2,1), filter 520ms ease";
                el.style.opacity = "1";
                el.style.transform = "translateY(0)";
                el.style.filter = "blur(0)";
            }, 520 + index * 85);
        });
    }

    // Input floating behavior + error vibration
    function initInputs() {
        const fields = document.querySelectorAll(".field");
        fields.forEach((field) => {
            const input = field.querySelector("input");
            if (!input) return;
            field.setAttribute("data-float", input.getAttribute("placeholder") || "");
            const sync = () => {
                const active = document.activeElement === input || input.value.trim() !== "";
                field.classList.toggle("floating", active);
            };
            input.addEventListener("focus", sync);
            input.addEventListener("blur", sync);
            input.addEventListener("input", sync);
            sync();
        });
    }

    // Magnetic button + ripple interactions
    function initButtons() {
        const buttons = document.querySelectorAll(".submit-btn");
        buttons.forEach((btn) => {
            btn.addEventListener("mousemove", (e) => {
                const rect = btn.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                const nx = (x / rect.width) - 0.5;
                const ny = (y / rect.height) - 0.5;
                btn.style.transform = "translate3d(" + (nx * 4.2).toFixed(2) + "px, " + (ny * 3.1).toFixed(2) + "px, 0)";
                btn.style.setProperty("--mx", String(x / rect.width));
            });
            btn.addEventListener("mouseleave", () => {
                btn.style.transform = "";
            });
            btn.addEventListener("click", (e) => {
                const rect = btn.getBoundingClientRect();
                const ripple = document.createElement("span");
                ripple.className = "ripple";
                ripple.style.left = (e.clientX - rect.left) + "px";
                ripple.style.top = (e.clientY - rect.top) + "px";
                btn.appendChild(ripple);
                setTimeout(() => ripple.remove(), 560);
            });
        });

    }

    function initErrorDetection() {
        const err = document.getElementById("form-alert");
        const cardEl = document.querySelector(".card-panel");
        if (!err || !cardEl) return;
        const observer = new MutationObserver(() => {
            const shown = err.style.display !== "none" && err.textContent.trim() !== "";
            if (!shown) return;
            err.classList.remove("show-animated");
            // force reflow for replay
            void err.offsetWidth;
            err.classList.add("show-animated");
            cardEl.classList.remove("shake");
            void cardEl.offsetWidth;
            cardEl.classList.add("shake");
            if (window.loginFX && typeof window.loginFX.onError === "function") {
                window.loginFX.onError();
            }
            cardEl.querySelectorAll(".auth-form input").forEach((input) => {
                if (!input.value) {
                    input.classList.add("input-error");
                    setTimeout(() => input.classList.remove("input-error"), 520);
                }
            });
        });
        observer.observe(err, { attributes: true, childList: true, subtree: true });
    }

    document.addEventListener("DOMContentLoaded", () => {
        stagedReveal();
        initInputs();
        initButtons();
        initErrorDetection();
    });
})();
