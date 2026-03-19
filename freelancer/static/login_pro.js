(function () {
    const canvas = document.getElementById("lux-canvas");
    const card = document.getElementById("auth-card");
    const intro = document.getElementById("lux-intro");
    const root = document.documentElement;
    if (!canvas || !card) return;

    const ctx = canvas.getContext("2d", { alpha: true });
    const state = {
        w: 0,
        h: 0,
        mx: window.innerWidth * 0.5,
        my: window.innerHeight * 0.5,
        smx: window.innerWidth * 0.5,
        smy: window.innerHeight * 0.5,
        pulse: 0,
        burst: 0
    };

    const points = [];
    const prefersReduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    function rand(min, max) {
        return Math.random() * (max - min) + min;
    }

    function setup() {
        state.w = canvas.width = window.innerWidth;
        state.h = canvas.height = window.innerHeight;
        points.length = 0;

        const densityBase = Math.floor((state.w * state.h) / (prefersReduced ? 6400 : 3200));
        const count = Math.max(180, Math.min(1100, densityBase));

        for (let i = 0; i < count; i += 1) {
            points.push({
                x: Math.random() * state.w,
                y: Math.random() * state.h,
                vx: rand(-0.22, 0.22),
                vy: rand(-0.22, 0.22),
                r: rand(0.35, 1.8),
                a: rand(0.16, 0.78),
                z: rand(0.4, 1.35)
            });
        }
    }

    window.addEventListener("resize", setup);
    setup();

    window.addEventListener("mousemove", function (e) {
        state.mx = e.clientX;
        state.my = e.clientY;
        state.pulse = Math.min(1, state.pulse + 0.07);
        root.style.setProperty("--pointer-x", ((state.mx / Math.max(state.w, 1)) * 100).toFixed(2) + "%");
        root.style.setProperty("--pointer-y", ((state.my / Math.max(state.h, 1)) * 100).toFixed(2) + "%");
    });

    window.addEventListener("pointerdown", function () {
        state.burst = 1;
    });

    function render() {
        const t = performance.now() * 0.00018;
        if (state.pulse < 0.03) {
            const autoX = 50 + Math.sin(t) * 12;
            const autoY = 48 + Math.cos(t * 1.4) * 9;
            root.style.setProperty("--pointer-x", autoX.toFixed(2) + "%");
            root.style.setProperty("--pointer-y", autoY.toFixed(2) + "%");
        }

        state.smx += (state.mx - state.smx) * 0.08;
        state.smy += (state.my - state.smy) * 0.08;

        ctx.clearRect(0, 0, state.w, state.h);
        let links = 0;

        for (let i = 0; i < points.length; i += 1) {
            const p = points[i];
            const dxm = p.x - state.smx;
            const dym = p.y - state.smy;
            const d2m = dxm * dxm + dym * dym;

            if (d2m < 30000 && d2m > 0.2) {
                const f = (1 - d2m / 30000) * 0.028;
                p.vx += (dxm / Math.sqrt(d2m)) * f;
                p.vy += (dym / Math.sqrt(d2m)) * f;
            }

            p.x += p.vx + ((state.smx / state.w) - 0.5) * 0.42 * p.z;
            p.y += p.vy + ((state.smy / state.h) - 0.5) * 0.38 * p.z;
            p.vx *= 0.986;
            p.vy *= 0.986;

            if (p.x < -20) p.x = state.w + 20;
            if (p.x > state.w + 20) p.x = -20;
            if (p.y < -20) p.y = state.h + 20;
            if (p.y > state.h + 20) p.y = -20;

            const glow = Math.max(0, 1 - d2m / 52000);
            const twinkle = 0.7 + Math.sin((i * 13.7) + performance.now() * 0.0011) * 0.3;
            ctx.fillStyle = "rgba(123, 226, 255," + (p.a * (0.36 + glow * 0.66 + state.pulse * 0.25) * twinkle).toFixed(3) + ")";
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.r + glow * 0.9, 0, Math.PI * 2);
            ctx.fill();

            if (links > 150) continue;
            for (let j = i + 1; j < Math.min(i + 15, points.length); j += 1) {
                const q = points[j];
                const dx = p.x - q.x;
                const dy = p.y - q.y;
                const d2 = dx * dx + dy * dy;
                if (d2 > 13000) continue;

                const alpha = (1 - d2 / 13000) * 0.22 * (1 + state.pulse * 0.25);
                ctx.strokeStyle = "rgba(111, 137, 255," + alpha.toFixed(3) + ")";
                ctx.lineWidth = 0.6 + (1 - d2 / 13000) * 0.35;
                ctx.beginPath();
                ctx.moveTo(p.x, p.y);
                ctx.lineTo(q.x, q.y);
                ctx.stroke();
                links += 1;
                if (links > 150) break;
            }
        }

        if (state.burst > 0.001) {
            ctx.fillStyle = "rgba(115,226,255," + (state.burst * 0.08).toFixed(3) + ")";
            ctx.fillRect(0, 0, state.w, state.h);
            state.burst *= 0.9;
        }

        state.pulse *= 0.97;
        requestAnimationFrame(render);
    }

    render();

    card.addEventListener("mousemove", function (e) {
        const r = card.getBoundingClientRect();
        const x = (e.clientX - r.left) / r.width;
        const y = (e.clientY - r.top) / r.height;
        const rx = (0.5 - y) * 6;
        const ry = (x - 0.5) * 8;
        card.style.transform = "rotateX(" + rx.toFixed(2) + "deg) rotateY(" + ry.toFixed(2) + "deg) translateZ(0)";

        card.querySelectorAll(".btn-auth").forEach(function (btn) {
            const br = btn.getBoundingClientRect();
            const bx = ((e.clientX - br.left) / br.width) * 100;
            btn.style.setProperty("--mx", bx.toFixed(2) + "%");
        });
    });

    card.addEventListener("mouseleave", function () {
        card.style.transform = "";
    });

    document.addEventListener("DOMContentLoaded", function () {
        const seq = card.querySelectorAll(".auth-header, .auth-tabs, .auth-alert, .auth-panel h3, .auth-panel p, .field, .row-meta, .btn-auth, .strength-wrap, .auth-foot");
        seq.forEach(function (el, i) {
            if (el.classList && el.classList.contains("auth-alert") && el.style.display === "none") return;
            el.style.opacity = "0";
            el.style.transform = "translateY(12px)";
            setTimeout(function () {
                el.style.transition = "opacity 460ms ease, transform 520ms cubic-bezier(.2,.85,.2,1)";
                el.style.opacity = "1";
                el.style.transform = "translateY(0)";
            }, 140 + i * 52);
        });
    });

    setTimeout(function () {
        if (intro) intro.remove();
    }, 1900);

    window.luxFX = window.luxFX || {};
    window.luxFX.success = function () {
        state.burst = 1;
        state.pulse = 1;
    };
    window.luxFX.error = function () {
        card.animate([
            { transform: "translateX(0)" },
            { transform: "translateX(-4px)" },
            { transform: "translateX(5px)" },
            { transform: "translateX(-3px)" },
            { transform: "translateX(0)" }
        ], { duration: 340, easing: "cubic-bezier(.36,.07,.19,.97)" });
        state.burst = 0.45;
    };
})();
