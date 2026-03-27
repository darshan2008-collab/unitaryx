(() => {
    "use strict";

    const q = (s, p = document) => p.querySelector(s);
    const qa = (s, p = document) => Array.from(p.querySelectorAll(s));
    const onRaf = (fn) => {
        let queued = false;
        return (...args) => {
            if (queued) return;
            queued = true;
            requestAnimationFrame(() => {
                queued = false;
                fn(...args);
            });
        };
    };

    const state = {
        mx: window.innerWidth / 2,
        my: window.innerHeight / 2,
        tx: window.innerWidth / 2,
        ty: window.innerHeight / 2,
        sliderIndex: 0,
        sliderTimer: null,
        audioCtx: null,
        lerp: (a, b, n) => (1 - n) * a + n * b,
    };

    const mobileLite =
        window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    if (mobileLite && document.body) {
        document.body.classList.add("ux-mobile-lite");
    }

    window.addEventListener("mousemove", (e) => {
        state.mx = e.clientX;
        state.my = e.clientY;
    }, { passive: true });

    const loader = q("#ux-loader");
    const loaderProgress = q("#ux-loader-progress-bar");
    const nav = q("#ux-nav");
    const LOADER_DURATION_MS = 3000;
    const LOADER_SOUND_URL = "https://actions.google.com/sounds/v1/science_fiction/robot_blip_2.ogg";

    const softClick = () => {
        try {
            if (!state.audioCtx) state.audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const ctx = state.audioCtx;
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.type = "sine";
            osc.frequency.value = 620;
            gain.gain.value = 0.0001;
            osc.connect(gain);
            gain.connect(ctx.destination);
            const t = ctx.currentTime;
            gain.gain.exponentialRampToValueAtTime(0.025, t + 0.01);
            gain.gain.exponentialRampToValueAtTime(0.0001, t + 0.07);
            osc.start(t);
            osc.stop(t + 0.08);
        } catch (_e) {
            // Ignore if audio not allowed.
        }
    };

    const initLoader = () => {
        const _ldrStart = performance.now();
        const ldr = q("#ux-loader");
        const bar = q("#ux-ldr-bar");
        const pctEl = q("#ux-ldr-pct");
        const statusEl = q("#ux-ldr-status-text");
        const ptcWrap = q("#ux-ldr-particles");
        const ldrCanvas = q("#ux-ldr-canvas");
        if (!ldr) return;

        if (mobileLite) {
            ldr.classList.add("hide");
            setTimeout(() => {
                if (ldr.parentNode) ldr.remove();
            }, 120);
            return;
        }

        /* ── 0. canvas starfield + nebula ── */
        if (ldrCanvas) {
            const lctx = ldrCanvas.getContext("2d");
            ldrCanvas.width = window.innerWidth;
            ldrCanvas.height = window.innerHeight;
            window.addEventListener("resize", () => {
                ldrCanvas.width = window.innerWidth;
                ldrCanvas.height = window.innerHeight;
            });
            const stars = Array.from({ length: 220 }, () => ({
                x: Math.random() * ldrCanvas.width,
                y: Math.random() * ldrCanvas.height,
                r: Math.random() * 1.4 + 0.2,
                a: Math.random(),
                da: (Math.random() - 0.5) * 0.012,
                vx: (Math.random() - 0.5) * 0.15,
                vy: (Math.random() - 0.5) * 0.15,
                color: ["34,211,238", "139,92,246", "236,72,153", "245,158,11", "96,165,250"][Math.floor(Math.random() * 5)]
            }));
            let ldrRaf;
            const drawCanvas = () => {
                if (!ldrCanvas.isConnected) { cancelAnimationFrame(ldrRaf); return; }
                lctx.clearRect(0, 0, ldrCanvas.width, ldrCanvas.height);
                /* nebula blobs */
                const cx = ldrCanvas.width / 2, cy = ldrCanvas.height / 2;
                const g1 = lctx.createRadialGradient(cx - 120, cy - 80, 0, cx - 120, cy - 80, 340);
                g1.addColorStop(0, "rgba(34,211,238,0.08)");
                g1.addColorStop(1, "transparent");
                lctx.fillStyle = g1; lctx.fillRect(0, 0, ldrCanvas.width, ldrCanvas.height);
                const g2 = lctx.createRadialGradient(cx + 100, cy + 100, 0, cx + 100, cy + 100, 280);
                g2.addColorStop(0, "rgba(139,92,246,0.07)");
                g2.addColorStop(1, "transparent");
                lctx.fillStyle = g2; lctx.fillRect(0, 0, ldrCanvas.width, ldrCanvas.height);
                /* stars */
                stars.forEach(s => {
                    s.x += s.vx; s.y += s.vy; s.a += s.da;
                    if (s.a < 0) s.da = Math.abs(s.da);
                    if (s.a > 1) s.da = -Math.abs(s.da);
                    if (s.x < 0) s.x = ldrCanvas.width;
                    if (s.x > ldrCanvas.width) s.x = 0;
                    if (s.y < 0) s.y = ldrCanvas.height;
                    if (s.y > ldrCanvas.height) s.y = 0;
                    lctx.beginPath();
                    lctx.arc(s.x, s.y, s.r, 0, Math.PI * 2);
                    lctx.fillStyle = `rgba(${s.color},${s.a.toFixed(2)})`;
                    lctx.fill();
                });
                ldrRaf = requestAnimationFrame(drawCanvas);
            };
            ldrRaf = requestAnimationFrame(drawCanvas);
        }

        /* ── 1. seed particle field (more particles, with glow) ── */
        if (ptcWrap) {
            const COLORS = ["#22d3ee", "#8b5cf6", "#ec4899", "#34d399", "#f59e0b", "#60a5fa", "#f472b6"];
            for (let i = 0; i < 90; i++) {
                const s = document.createElement("span");
                const ang = Math.random() * Math.PI * 2;
                const dist = 100 + Math.random() * 260;
                const size = (1 + Math.random() * 3).toFixed(1);
                s.style.cssText = [
                    `--c:${COLORS[i % COLORS.length]}`,
                    `--dur:${(2 + Math.random() * 4).toFixed(1)}s`,
                    `--delay:${(Math.random() * 4).toFixed(1)}s`,
                    `--tx:${(46 + Math.random() * 8).toFixed(1)}%`,
                    `--ty:${(44 + Math.random() * 12).toFixed(1)}%`,
                    `--mx:${(Math.cos(ang) * dist).toFixed(0)}px`,
                    `--my:${(Math.sin(ang) * dist).toFixed(0)}px`,
                    `--glow:${(parseInt(size) * 3)}px`,
                    `width:${size}px`,
                    `height:${size}px`,
                ].join(";");
                ptcWrap.appendChild(s);
            }
        }

        /* ── 2. status ticker ── */
        const STATUSES = [
            "QUANTUM CORE COLD-BOOT...",
            "DECRYPTING SECURITY PROTOCOLS",
            "SYNCING NEURAL NETWORKS",
            "CALIBRATING OPTICAL SENSORS",
            "INITIALIZING UNITARY X ENGINE",
            "ESTABLISHING SECURE PIPELINE",
            "CORE SYSTEMS OPERATIONAL"
        ];
        let si = 0;
        const statusTick = setInterval(() => {
            si = (si + 1) % STATUSES.length;
            if (statusEl) statusEl.textContent = STATUSES[si];
        }, 570);  /* 7 messages × 570ms ≈ 4.0s */

        /* ── 3. animated progress bar ── */
        let pct = 0;
        const TOTAL_MS = 4000;
        const TICK_MS = 28;          /* ~143 ticks across 4 s */
        const increment = () => {
            const remaining = 100 - pct;
            pct += remaining * 0.025 + 0.22;
            if (pct > 99) pct = 99;
            if (bar) bar.style.width = pct.toFixed(1) + "%";
            if (pctEl) pctEl.textContent = Math.floor(pct) + "%";
        };
        const barTick = setInterval(increment, TICK_MS);

        /* ── 4. on load → finish + GPU zoom exit ── */
        const finish = () => {
            clearInterval(statusTick);
            clearInterval(barTick);

            /* Snap bar to 100% */
            if (bar) bar.style.width = "100%";
            if (pctEl) pctEl.textContent = "100%";
            if (statusEl) statusEl.textContent = "SYSTEMS ONLINE ✓";

            setTimeout(() => {
                /*
                 * PERFORMANCE: stop ALL expensive work before zoom starts
                 * so the GPU has a clear runway to hit 60fps.
                 */

                /* 1. Kill canvas starfield RAF */
                const canvas = q("#ux-ldr-canvas");
                if (canvas) canvas.style.display = "none"; /* stops drawCanvas RAF on next tick */

                /* 2. Remove particle DOM nodes (saves render cost) */
                const ptc = q("#ux-ldr-particles");
                if (ptc) ptc.innerHTML = "";

                /* 3. Hide streams + sweep + hud instantly */
                [".ux-ldr-streams", ".ux-ldr-scan-sweep", ".ux-ldr-hud", ".ux-ldr-svg-rings"]
                    .forEach(sel => { const el = q(sel); if (el) el.style.opacity = "0"; });

                /* 4. Wait one frame so browser flushes style changes,
                   then add zoom-exit on a clean GPU frame */
                requestAnimationFrame(() => {
                    requestAnimationFrame(() => {
                        ldr.classList.add("zoom-exit");

                        /* Remove after animation completes (800ms) */
                        setTimeout(() => {
                            ldr.classList.add("hide");
                            setTimeout(() => ldr.remove(), 300);
                        }, 800);
                    });
                });
            }, 400);
        };

        if (document.readyState === "complete") {
            /* Page already loaded — still honour the full 5-second show */
            setTimeout(finish, TOTAL_MS);
        } else {
            /* Wait for page load, but enforce a minimum of 5 s */
            let loadFired = false;
            const onLoaded = () => {
                if (loadFired) return;
                loadFired = true;
                const elapsed = performance.now() - _ldrStart;
                const remaining = Math.max(0, TOTAL_MS - elapsed);
                setTimeout(finish, remaining);
            };
            window.addEventListener("load", onLoaded, { once: true });
            /* Hard fallback at 4.5 s */
            setTimeout(finish, TOTAL_MS + 500);
        }
    };


    const initBackgroundParticles = () => {
        if (mobileLite) return;
        const canvas = q("#ux-bg-canvas");
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        if (!ctx) return;

        const prefersReduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
        if (prefersReduced) return;

        const lowPower = (navigator.hardwareConcurrency || 8) <= 4;
        /* Increased node count for heavy graphics */
        const nodeCount = lowPower ? 55 : 120;
        const repelRadius = lowPower ? 180 : 250;
        const repelRadiusSq = repelRadius * repelRadius;
        const lineDist = lowPower ? 130 : 170;
        const lineDistSq = lineDist * lineDist;
        const maxDpr = Math.min(window.devicePixelRatio || 1, 1.25);
        const nodes = [];
        let rafId = 0;
        let lastTs = 0;
        const frameBudget = 1000 / 58;
        let running = true;

        const resize = () => {
            const w = window.innerWidth;
            const h = window.innerHeight;
            canvas.style.width = `${w}px`;
            canvas.style.height = `${h}px`;
            canvas.width = Math.floor(w * maxDpr);
            canvas.height = Math.floor(h * maxDpr);
            ctx.setTransform(maxDpr, 0, 0, maxDpr, 0, 0);
        };
        resize();
        window.addEventListener("resize", resize);

        for (let i = 0; i < nodeCount; i += 1) {
            nodes.push({
                x: Math.random() * window.innerWidth,
                y: Math.random() * window.innerHeight,
                /* Faster particle speeds */
                vx: (Math.random() - 0.5) * (lowPower ? 0.6 : 1.2),
                vy: (Math.random() - 0.5) * (lowPower ? 0.6 : 1.2),
                r: Math.random() * 2.2 + 0.8,
                /* Assign random vibrant colors to each particle */
                color: Math.random() > 0.5 ? "34, 211, 238" : "139, 92, 246"
            });
        }

        const draw = (ts) => {
            if (!running) return;
            if (ts - lastTs < frameBudget) {
                rafId = requestAnimationFrame(draw);
                return;
            }
            lastTs = ts;

            const w = window.innerWidth;
            const h = window.innerHeight;
            ctx.clearRect(0, 0, w, h);

            /* Add subtle global glow effect */
            ctx.globalCompositeOperation = "lighter";

            nodes.forEach((n, i) => {
                n.x += n.vx;
                n.y += n.vy;
                if (n.x < 0 || n.x > w) n.vx *= -1;
                if (n.y < 0 || n.y > h) n.vy *= -1;

                const dx = state.mx - n.x;
                const dy = state.my - n.y;
                const d2 = dx * dx + dy * dy;
                if (d2 < repelRadiusSq && d2 > 0.001) {
                    const inv = 1 / Math.sqrt(d2);
                    n.x -= dx * inv * 0.8; /* Stronger mouse repel */
                    n.y -= dy * inv * 0.8;
                }

                ctx.beginPath();
                ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
                ctx.fillStyle = `rgba(${n.color}, 0.8)`;
                ctx.fill();

                for (let j = i + 1; j < nodes.length; j += 1) {
                    const m = nodes[j];
                    const lx = n.x - m.x;
                    const ly = n.y - m.y;
                    const ld2 = lx * lx + ly * ly;
                    if (ld2 < lineDistSq) {
                        const ld = Math.sqrt(ld2);
                        ctx.beginPath();
                        ctx.moveTo(n.x, n.y);
                        ctx.lineTo(m.x, m.y);
                        /* Make connection lines glow brightly based on proximity */
                        const opacity = 0.35 - (ld / lineDist) * 0.35;
                        ctx.strokeStyle = `rgba(${n.color}, ${opacity})`;
                        ctx.lineWidth = 1.2;
                        ctx.stroke();
                    }
                }
            });

            ctx.globalCompositeOperation = "source-over";
            rafId = requestAnimationFrame(draw);
        };

        const toggleRunState = () => {
            running = document.visibilityState === "visible";
            if (running && !rafId) {
                rafId = requestAnimationFrame(draw);
            } else if (!running && rafId) {
                cancelAnimationFrame(rafId);
                rafId = 0;
            }
        };

        document.addEventListener("visibilitychange", toggleRunState);
        rafId = requestAnimationFrame(draw);
    };

    const initHeadline = () => {
        const el = q("#ux-headline");
        if (!el) return;
        const text = el.textContent.trim() || "";
        el.textContent = "";

        const words = text.split(" ");
        let totalIdx = 0;

        words.forEach((word, wIdx) => {
            const wordSpan = document.createElement("span");
            wordSpan.style.display = "inline-block";
            wordSpan.style.whiteSpace = "nowrap";

            [...word].forEach((ch) => {
                const span = document.createElement("span");
                span.className = "char";
                span.textContent = ch;
                span.style.opacity = "0";
                span.style.display = "inline-block";
                span.style.transform = "translateY(50px) scale(0.4) rotateX(-70deg)";
                span.style.filter = "blur(8px)";

                /* Transition has NO delay — the setTimeout below controls timing */
                span.style.transition = [
                    "opacity 0.7s cubic-bezier(0.2,1.2,0.3,1)",
                    "transform 0.8s cubic-bezier(0.2,1.2,0.3,1)",
                    "filter 0.6s ease"
                ].join(", ");

                wordSpan.appendChild(span);

                /* Fire each character in staggered sequence after loader */
                const triggerAt = 4500 + totalIdx * 26;
                setTimeout(() => {
                    span.style.opacity = "1";
                    span.style.transform = "translateY(0) scale(1) rotateX(0deg)";
                    span.style.filter = "blur(0)";
                }, triggerAt);

                totalIdx++;
            });

            el.appendChild(wordSpan);

            if (wIdx < words.length - 1) {
                const space = document.createElement("span");
                space.textContent = "\u00A0";
                space.style.display = "inline-block";
                el.appendChild(space);
            }
        });

        setTimeout(() => q("#ux-sub")?.classList.add("show"), 4500 + 600);
        setTimeout(() => {
            const ctaRow = q(".ux-cta-row");
            if (ctaRow) {
                ctaRow.style.opacity = "1";
                ctaRow.style.transform = "translateY(0)";
            }
        }, 4500 + 900);
    };


    const initReveals = () => {
        const revealNodes = qa(".ux-reveal");
        if (!revealNodes.length) return;

        const showAll = () => {
            revealNodes.forEach((node) => node.classList.add("is-visible"));
        };

        if (typeof window.IntersectionObserver !== "function") {
            showAll();
            return;
        }

        let hasIntersected = false;
        const fallbackTimer = setTimeout(() => {
            if (!hasIntersected) showAll();
        }, 1200);

        const obs = new IntersectionObserver((entries) => {
            entries.forEach((e) => {
                if (!e.isIntersecting) return;
                hasIntersected = true;
                e.target.classList.add("is-visible");
                obs.unobserve(e.target);
            });

            if (hasIntersected) {
                clearTimeout(fallbackTimer);
            }
        }, { threshold: 0.14 });

        revealNodes.forEach((node) => obs.observe(node));
    };

    const initNavActive = () => {
        const links = qa(".ux-links a");
        const sections = links
            .map((a) => q(a.getAttribute("href")))
            .filter(Boolean);

        window.addEventListener("scroll", () => {
            const y = window.scrollY + 180;
            let active = 0;
            sections.forEach((s, idx) => {
                if (s.offsetTop <= y) active = idx;
            });
            links.forEach((l, i) => l.classList.toggle("active", i === active));
            if (nav) {
                nav.style.transform = `translateY(${window.scrollY > 40 ? 0 : 0}px)`;
            }
        }, { passive: true });
    };

    const initMagnetic = () => {
        qa(".ux-magnetic").forEach((el) => {
            el.addEventListener("mousemove", (e) => {
                const r = el.getBoundingClientRect();
                const x = e.clientX - (r.left + r.width / 2);
                const y = e.clientY - (r.top + r.height / 2);
                el.style.transform = `translate(${x * 0.08}px, ${y * 0.08}px)`;
            });
            el.addEventListener("mouseleave", () => {
                el.style.transform = "translate(0,0)";
            });
        });
    };

    const initRipples = () => {
        qa(".ux-ripple").forEach((el) => {
            el.addEventListener("click", (e) => {
                softClick();
                const ripple = document.createElement("span");
                const r = el.getBoundingClientRect();
                const size = Math.max(r.width, r.height) * 1.2;
                ripple.style.position = "absolute";
                ripple.style.width = `${size}px`;
                ripple.style.height = `${size}px`;
                ripple.style.left = `${e.clientX - r.left - size / 2}px`;
                ripple.style.top = `${e.clientY - r.top - size / 2}px`;
                ripple.style.borderRadius = "50%";
                ripple.style.background = "rgba(255,255,255,0.28)";
                ripple.style.transform = "scale(0)";
                ripple.style.opacity = "1";
                ripple.style.pointerEvents = "none";
                ripple.style.transition = "transform 0.6s ease, opacity 0.6s ease";
                el.appendChild(ripple);
                requestAnimationFrame(() => {
                    ripple.style.transform = "scale(1)";
                    ripple.style.opacity = "0";
                });
                setTimeout(() => ripple.remove(), 650);
            });
        });
    };

    const initHeroParallax = () => {
        const floats = qa(".ux-float");
        const orbs = qa(".ux-orb");
        const floor = q(".ux-grid-floor");
        if (!floats.length && !orbs.length && !floor) return;

        let tx = 0, ty = 0; // Target
        let cx = 0, cy = 0; // Current
        const lerp = (a, b, n) => (1 - n) * a + n * b;

        const animate = () => {
            cx = lerp(cx, tx, 0.08); // Smooth motion
            cy = lerp(cy, ty, 0.08);

            floats.forEach((f, idx) => {
                const move = (idx + 1) * 25;
                f.style.transform = `translate3d(${cx * move}px, ${cy * move}px, 0)`;
            });

            orbs.forEach((orb, idx) => {
                const move = (idx + 1) * -45;
                orb.style.transform = `translate3d(${cx * move}px, ${cy * move}px, 0) scale(${1 + Math.abs(cx * 0.1)})`;
            });

            if (floor) {
                // Tilt the grid floor in 3D
                floor.style.transform = `rotateX(75deg) rotateY(${cx * 15}deg) translateZ(${cy * -20}px) translateX(${cx * -30}px)`;
            }

            requestAnimationFrame(animate);
        };

        window.addEventListener("mousemove", (e) => {
            tx = (e.clientX / window.innerWidth) - 0.5;
            ty = (e.clientY / window.innerHeight) - 0.5;
        }, { passive: true });

        animate();
    };

    const initSkillTags = () => {
        qa(".ux-tag").forEach((tag, idx) => {
            setTimeout(() => tag.classList.add("show"), 480 + idx * 90);
        });
    };

    const initMeters = () => {
        const obs = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                const bars = qa(".ux-meter-fill", entry.target);
                if (entry.isIntersecting) {
                    bars.forEach((bar) => {
                        const val = bar.getAttribute("data-value") || "0";
                        bar.style.width = `${val}%`;
                    });
                } else {
                    bars.forEach((bar) => {
                        bar.style.width = "0%";
                    });
                }
            });
        }, { threshold: 0.35 });
        const wrap = q("#ux-about");
        if (wrap) obs.observe(wrap);
    };

    const initProjectFilter = () => {
        const btns = qa(".ux-filter");
        const cards = qa(".ux-project-card");
        const search = q("#ux-project-search");
        const count = q("#ux-project-count");
        let activeFilter = "all";

        const refresh = () => {
            const term = (search?.value || "").trim().toLowerCase();
            let shown = 0;
            cards.forEach((c) => {
                const cat = c.getAttribute("data-category") || "";
                const text = (c.textContent || "").toLowerCase();
                const byCategory = activeFilter === "all" || cat === activeFilter;
                const bySearch = !term || text.includes(term);
                const ok = byCategory && bySearch;
                c.style.display = ok ? "block" : "none";
                if (ok) shown += 1;
            });

            if (count) {
                if (!term && activeFilter === "all") {
                    count.textContent = "Showing all projects";
                } else {
                    count.textContent = `Showing ${shown} project${shown === 1 ? "" : "s"}`;
                }
            }
        };

        btns.forEach((b) => {
            b.addEventListener("click", () => {
                const f = b.getAttribute("data-filter") || "all";
                activeFilter = f;
                btns.forEach((x) => x.classList.remove("active"));
                b.classList.add("active");
                refresh();
            });
        });

        search?.addEventListener("input", refresh);
        refresh();
    };

    const initLiveStatus = () => {
        const el = q("#ux-live-status");
        if (!el) return;
        const lines = [
            "Accepting 2 premium projects this week",
            "Next fast-start slot opens in 48 hours",
            "Priority support slots available for urgent builds",
        ];
        let i = 0;
        setInterval(() => {
            i = (i + 1) % lines.length;
            el.style.opacity = "0.45";
            setTimeout(() => {
                el.textContent = lines[i];
                el.style.opacity = "1";
            }, 180);
        }, 4200);
    };

    const initPricingMode = () => {
        const wrap = q("#ux-price-toggle");
        if (!wrap) return;
        const btns = qa("button[data-mode]", wrap);
        const prices = qa(".ux-price-value[data-student][data-pro]");

        const apply = (mode) => {
            prices.forEach((p) => {
                const value = p.getAttribute(mode === "pro" ? "data-pro" : "data-student");
                if (value) p.textContent = value;
            });
            btns.forEach((b) => b.classList.toggle("active", b.getAttribute("data-mode") === mode));
        };

        btns.forEach((btn) => {
            btn.addEventListener("click", () => {
                const mode = btn.getAttribute("data-mode") || "student";
                apply(mode);
            });
        });

        apply("student");
    };

    const initScrollProgress = () => {
        const btn = q("#ux-progress");
        const val = q("#ux-progress-val");
        if (!btn || !val) return;

        const update = () => {
            const top = window.scrollY;
            const max = document.documentElement.scrollHeight - window.innerHeight;
            const pct = max > 0 ? Math.min(100, Math.round((top / max) * 100)) : 0;
            val.textContent = `${pct}%`;
            btn.style.background = `conic-gradient(var(--ux-blue) ${pct * 3.6}deg, rgba(2,6,23,0.9) 0deg)`;
            btn.classList.toggle("show", top > 140);
        };

        window.addEventListener("scroll", update, { passive: true });
        btn.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
        update();
    };

    const initCommandPalette = () => {
        const modal = q("#ux-command");
        if (!modal) return;

        const open = () => {
            modal.classList.add("open");
            modal.setAttribute("aria-hidden", "false");
        };
        const close = () => {
            modal.classList.remove("open");
            modal.setAttribute("aria-hidden", "true");
        };

        window.addEventListener("keydown", (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
                e.preventDefault();
                open();
            }
            if (e.key === "Escape") close();
        });

        modal.addEventListener("click", (e) => {
            if (e.target === modal) close();
        });

        qa("[data-jump]", modal).forEach((btn) => {
            btn.addEventListener("click", () => {
                const sel = btn.getAttribute("data-jump") || "#home";
                const section = q(sel);
                section?.scrollIntoView({ behavior: "smooth", block: "start" });
                close();
            });
        });
    };

    const initTiltAndCounters = () => {
        qa(".ux-service-card, .ux-project-card, .ux-lab-card, .ux-tilt-element").forEach((card) => {
            card.addEventListener("mousemove", (e) => {
                if (window.matchMedia("(max-width: 700px)").matches) return;
                const r = card.getBoundingClientRect();
                const x = (e.clientX - r.left) / r.width - 0.5;
                const y = (e.clientY - r.top) / r.height - 0.5;
                card.style.transform = `rotateY(${x * 14}deg) rotateX(${y * -14}deg) translateY(-4px)`;
            });
            card.addEventListener("mouseleave", () => {
                card.style.transform = "rotateY(0) rotateX(0) translateY(0)";
            });
        });

        const wrap = q(".ux-stats-grid");
        if (wrap) {
            const obs = new IntersectionObserver((entries) => {
                entries.forEach((entry) => {
                    if (entry.isIntersecting) {
                        const counters = qa(".ux-stat-num", entry.target);
                        counters.forEach((c) => {
                            const target = parseInt(c.getAttribute("data-target")) || 0;
                            let current = 0;
                            const hasPlus = c.innerText.includes('+');
                            const hasPct = c.innerText.includes('%');
                            const hasK = c.innerText.includes('k');

                            const stepTime = 16;
                            const steps = 60; // 1s at 60fps
                            let step = 0;

                            const timer = setInterval(() => {
                                step++;
                                current = Math.floor((step / steps) * target);
                                if (step >= steps) {
                                    clearInterval(timer);
                                    current = target;
                                }
                                c.innerText = current + (hasPlus ? '+' : hasPct ? '%' : hasK ? 'k' : '');
                            }, stepTime);
                        });
                        obs.unobserve(entry.target);
                    }
                });
            }, { threshold: 0.1 });
            obs.observe(wrap);
        }
    };

    const initTestimonial = () => {
        const track = q("#ux-testi-track");
        const dots = qa(".ux-dot");
        if (!track || !dots.length) return;

        const go = (i) => {
            state.sliderIndex = i;
            track.style.transform = `translateX(-${i * 100}%)`;
            dots.forEach((d, idx) => d.classList.toggle("active", idx === i));
        };

        dots.forEach((d, idx) => d.addEventListener("click", () => go(idx)));

        const auto = () => {
            state.sliderIndex = (state.sliderIndex + 1) % dots.length;
            go(state.sliderIndex);
        };

        state.sliderTimer = setInterval(auto, 4200);
        track.addEventListener("mouseenter", () => clearInterval(state.sliderTimer));
        track.addEventListener("mouseleave", () => {
            clearInterval(state.sliderTimer);
            state.sliderTimer = setInterval(auto, 4200);
        });
    };

    const initFaq = () => {
        qa(".ux-faq-item").forEach((item) => {
            const btn = q(".ux-faq-btn", item);
            btn?.addEventListener("click", () => {
                const open = item.classList.contains("open");
                qa(".ux-faq-item.open").forEach((x) => x.classList.remove("open"));
                if (!open) item.classList.add("open");
            });
        });
    };

    const initContact = () => {
        const form = q("#ux-contact-form");

        if (!form) return;
        const feedback = q("#ux-feedback");
        const charCount = q("#ux-char-count");
        const messageEl = q("#ux-message");
        const serviceSelect = q("#ux-service");
        const quickWrap = q("#ux-service-quick");
        const draftKey = "ux-contact-draft-v1";

        const updateChars = () => {
            if (!charCount || !messageEl) return;
            charCount.textContent = `${messageEl.value.length} characters`;
        };

        const saveDraft = () => {
            const draft = {
                name: q("#ux-name")?.value || "",
                email: q("#ux-email")?.value || "",
                phone: q("#ux-phone")?.value || "",
                service: q("#ux-service")?.value || "",
                deadline: q("#ux-deadline")?.value || "",
                message: q("#ux-message")?.value || "",
            };
            try {
                localStorage.setItem(draftKey, JSON.stringify(draft));
            } catch (_e) {
                // Ignore localStorage limitations.
            }
        };

        const loadDraft = () => {
            try {
                const raw = localStorage.getItem(draftKey);
                if (!raw) return;
                const d = JSON.parse(raw);
                if (q("#ux-name") && d.name) q("#ux-name").value = d.name;
                if (q("#ux-email") && d.email) q("#ux-email").value = d.email;
                if (q("#ux-phone") && d.phone) q("#ux-phone").value = d.phone;
                if (q("#ux-service") && d.service) q("#ux-service").value = d.service;
                if (q("#ux-deadline") && d.deadline) q("#ux-deadline").value = d.deadline;
                if (q("#ux-message") && d.message) q("#ux-message").value = d.message;
            } catch (_e) {
                // Ignore parse errors.
            }
        };

        loadDraft();
        updateChars();

        qa("button[data-service]", quickWrap || document).forEach((btn) => {
            btn.addEventListener("click", () => {
                const value = btn.getAttribute("data-service") || "";
                if (serviceSelect && value) serviceSelect.value = value;
                qa("button[data-service]", quickWrap || document).forEach((x) => x.classList.toggle("active", x === btn));
                saveDraft();
            });
        });

        qa("input,select,textarea", form).forEach((el) => {
            el.addEventListener("input", () => {
                updateChars();
                saveDraft();
            });
        });

        form.addEventListener("submit", async (e) => {
            e.preventDefault();
            const btn = q("#ux-submit-btn");
            const loggedIn = form.getAttribute("data-logged-in") === "1";
            if (!loggedIn) {
                window.location.href = "/login";
                return;
            }

            const payload = {
                name: q("#ux-name")?.value?.trim() || "",
                email: q("#ux-email")?.value?.trim() || "",
                phone: q("#ux-phone")?.value?.trim() || "",
                service: q("#ux-service")?.value || "",
                deadline: q("#ux-deadline")?.value || "",
                message: q("#ux-message")?.value?.trim() || "",
            };

            btn?.classList.add("loading");
            if (btn) btn.textContent = "Sending...";

            try {
                const res = await fetch("/api/contact", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-Requested-With": "XMLHttpRequest",
                    },
                    body: JSON.stringify(payload),
                });
                let data = {};
                const contentType = (res.headers.get("content-type") || "").toLowerCase();
                if (contentType.includes("application/json")) {
                    data = await res.json();
                } else {
                    const rawText = await res.text();
                    data = { message: rawText || `Request failed (${res.status})` };
                }
                if (!res.ok || !data.success) {
                    const msg = data.message || (data.errors ? Object.values(data.errors)[0] : "Request failed");
                    feedback.className = "ux-feedback err";
                    feedback.textContent = msg;
                    if (res.status === 401 && data.redirect) {
                        setTimeout(() => { window.location.href = data.redirect; }, 800);
                    }
                } else {
                    feedback.className = "ux-feedback ok";
                    feedback.textContent = data.message || "Request sent successfully.";
                    form.reset();
                    updateChars();
                    try {
                        localStorage.removeItem(draftKey);
                    } catch (_e) {
                        // Ignore localStorage limitations.
                    }
                }
            } catch (_err) {
                feedback.className = "ux-feedback err";
                feedback.textContent = "Network error. Please try again.";
            } finally {
                btn?.classList.remove("loading");
                if (btn) btn.textContent = "Work With UNITARY X";
            }
        });
    };

    const initEasterEgg = () => {
        const hint = q("#ux-easter");
        let buf = "";
        window.addEventListener("keydown", (e) => {
            buf = (buf + e.key.toLowerCase()).slice(-2);
            if (buf === "ux") {
                hint?.classList.add("show");
                setTimeout(() => hint?.classList.remove("show"), 1800);
            }
        });
    };

    /* ══════════════════════════════════════════════
       NEW: ANIMATED STAT COUNTERS
    ══════════════════════════════════════════════ */
    const initStatCounters = () => {
        const nums = qa('.ux-stat-num');
        if (!nums.length) return;
        const iob = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const el = entry.target;
                if (!entry.isObserving && entry.isIntersecting) {
                    entry.isObserving = true;
                    const target = +el.dataset.target;
                    const suffix = el.dataset.suffix || '';
                    const dur = 1800;
                    const start = performance.now();
                    const tick = (now) => {
                        if (!entry.isObserving) return; // Halt if out of view
                        const pct = Math.min((now - start) / dur, 1);
                        const ease = 1 - Math.pow(1 - pct, 3);
                        el.textContent = Math.floor(ease * target) + suffix;
                        if (pct < 1) requestAnimationFrame(tick);
                    };
                    requestAnimationFrame(tick);
                } else if (!entry.isIntersecting) {
                    entry.isObserving = false;
                    el.textContent = "0" + (el.dataset.suffix || '');
                }
            });
        }, { threshold: 0.5 });
        nums.forEach(n => { n.isObserving = false; iob.observe(n); });
    };

    /* ══════════════════════════════════════════════
       NEW: SKILL BARS ANIMATED FILL
    ══════════════════════════════════════════════ */
    const initSkillBars = () => {
        const bars = qa('.ux-skill-bar');
        if (!bars.length) return;
        const iob = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                const bar = entry.target;
                const fill = bar.querySelector('.ux-skill-fill');
                const label = bar.querySelector('.ux-skill-pct');

                if (!entry.fired && entry.isIntersecting) {
                    entry.fired = true;
                    const pct = +bar.dataset.pct;
                    if (!fill) return;
                    fill.style.width = pct + '%';
                    let cur = 0;
                    const dur = 1400, start = performance.now();
                    const tick = (now) => {
                        if (!entry.fired) return; // Halt if out of view
                        const t = Math.min((now - start) / dur, 1);
                        cur = Math.floor((1 - Math.pow(1 - t, 3)) * pct);
                        if (label) label.textContent = cur + '%';
                        if (t < 1) requestAnimationFrame(tick);
                    };
                    requestAnimationFrame(tick);
                } else if (!entry.isIntersecting) {
                    entry.fired = false;
                    if (fill) fill.style.width = '0%';
                    if (label) label.textContent = '0%';
                }
            });
        }, { threshold: 0.3 });
        bars.forEach(b => { b.fired = false; iob.observe(b); });
    };

    /* ══════════════════════════════════════════════
       NEW: TESTIMONIALS CAROUSEL
    ══════════════════════════════════════════════ */
    const initTestimonialCarousel = () => {
        const track = q('#ux-testi-track');
        const prev = q('#ux-testi-prev');
        const next = q('#ux-testi-next');
        const dotsEl = q('#ux-testi-dots');
        if (!track) return;

        const cards = Array.from(track.querySelectorAll('.ux-testi-card'));
        if (!cards.length) return;

        /* Figure out cards per slide based on viewport */
        const perSlide = () => window.innerWidth < 600 ? 1 : window.innerWidth < 900 ? 2 : 3;
        let cur = 0;
        let auto;

        const rebuild = () => {
            const ps = perSlide();
            const total = Math.ceil(cards.length / ps);
            if (dotsEl) {
                dotsEl.innerHTML = '';
                for (let i = 0; i < total; i++) {
                    const d = document.createElement('span');
                    if (i === cur) d.classList.add('active');
                    d.addEventListener('click', () => go(i));
                    dotsEl.appendChild(d);
                }
            }
        };

        const go = (idx) => {
            const ps = perSlide();
            const total = Math.ceil(cards.length / ps);
            cur = (idx + total) % total;
            /* card width including gap */
            const gap = 24;
            const outer = q('#ux-testi-outer');
            const tw = outer ? outer.offsetWidth - 88 : track.offsetWidth;
            const cw = (tw + gap) / ps;
            track.style.transform = `translateX(-${cur * cw * ps}px)`;
            rebuild();
        };

        if (prev) prev.addEventListener('click', () => { go(cur - 1); resetAuto(); });
        if (next) next.addEventListener('click', () => { go(cur + 1); resetAuto(); });

        const resetAuto = () => { clearInterval(auto); auto = setInterval(() => go(cur + 1), 5000); };
        resetAuto();
        rebuild();
        window.addEventListener('resize', () => go(cur));
    };

    /* ══════════════════════════════════════════════
       NEW: PRICE ESTIMATOR
    ══════════════════════════════════════════════ */
    const initPriceEstimator = () => {
        const priceEl = q('#est-price');
        const timeline = q('#est-timeline');
        const timeLabel = q('#est-timeline-val');
        if (!priceEl) return;

        const BASE = {
            web: [2500, 5000], app: [5000, 12000], ai: [8000, 20000],
            iot: [4000, 10000], design: [2000, 5000]
        };
        const MULT = { basic: 1, standard: 1.8, advanced: 3.2 };
        const ADDONS = { 'add-seo': 800, 'add-auth': 1200, 'add-admin': 2000, 'add-api': 1500, 'add-deploy': 1000 };

        let selType = 'web', selComplx = 'basic';

        const calc = () => {
            const [lo, hi] = BASE[selType] || [2500, 5000];
            const m = MULT[selComplx] || 1;
            const days = +(timeline ? timeline.value : 14);
            /* urgency: <7 days → +30%, <14 → +15% */
            const urgency = days < 7 ? 1.3 : days < 14 ? 1.15 : 1.0;
            let addon = 0;
            Object.entries(ADDONS).forEach(([id, cost]) => {
                const cb = q('#' + id);
                if (cb && cb.checked) addon += cost;
            });
            const low = Math.round((lo * m + addon) * urgency / 100) * 100;
            const high = Math.round((hi * m + addon) * urgency / 100) * 100;
            const fmt = n => '₹' + n.toLocaleString('en-IN');
            priceEl.textContent = `${fmt(low)} – ${fmt(high)}`;
        };

        /* chip selectors */
        [q('#est-type'), q('#est-complexity')].forEach(group => {
            if (!group) return;
            group.querySelectorAll('.ux-chip').forEach(chip => {
                chip.addEventListener('click', () => {
                    group.querySelectorAll('.ux-chip').forEach(c => c.classList.remove('active'));
                    chip.classList.add('active');
                    if (group.id === 'est-type') selType = chip.dataset.val;
                    else selComplx = chip.dataset.val;
                    calc();
                });
            });
        });

        if (timeline) {
            timeline.addEventListener('input', () => {
                if (timeLabel) timeLabel.textContent = timeline.value + ' days';
                calc();
            });
        }

        ['add-seo', 'add-auth', 'add-admin', 'add-api', 'add-deploy'].forEach(id => {
            const cb = q('#' + id);
            if (cb) cb.addEventListener('change', calc);
        });

        calc();
    };

    const initSpotlightCards = () => {
        qa(".ux-project-card, .ux-service-card, .ux-lab-card, .ux-float, .ux-tilt-element").forEach((card) => {
            card.addEventListener("mousemove", onRaf((e) => {
                const rect = card.getBoundingClientRect();
                const x = e.clientX - rect.left;
                const y = e.clientY - rect.top;
                card.style.setProperty("--mouse-x", `${x}px`);
                card.style.setProperty("--mouse-y", `${y}px`);
            }));
        });
    };


    const initScrambleText = () => {
        const els = qa(".ux-scramble-text");
        const chars = "!<>-_\\/[]{}—=+*^?#_";

        /* Cache the true text FIRST, before any observer fires */
        els.forEach(el => {
            el.dataset.text = el.textContent.trim();
        });

        const obs = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                const el = entry.target;
                const final = el.dataset.text || "";
                if (!final) return;

                if (entry.isIntersecting && !el.dataset.scrambling) {
                    el.dataset.scrambling = "true";
                    let iteration = 0;
                    const len = final.length;

                    const scrambler = setInterval(() => {
                        el.textContent = final.split("").map((letter, index) => {
                            if (index < iteration) return final[index];
                            return chars[Math.floor(Math.random() * chars.length)];
                        }).join("");

                        iteration += 0.5;
                        if (iteration >= len) {
                            clearInterval(scrambler);
                            el.textContent = final; /* restore exact text */
                            el.dataset.scrambling = "";
                        }
                    }, 35);
                } else if (!entry.isIntersecting) {
                    el.dataset.scrambling = "";
                    el.textContent = final; /* reset to real text when out of view */
                }
            });
        }, { threshold: 0.3 });
        els.forEach(el => obs.observe(el));
    };

    const init = () => {
        initLoader();
        initBackgroundParticles();
        initHeadline();
        initReveals();
        initNavActive();
        if (!mobileLite) {
            initMagnetic();
            initRipples();
            initHeroParallax();
        }
        initSkillTags();
        initMeters();
        initProjectFilter();
        initLiveStatus();
        initPricingMode();
        if (!mobileLite) {
            initTiltAndCounters();
        }
        initTestimonial();
        initFaq();
        initContact();
        initScrollProgress();
        if (!mobileLite) {
            initCommandPalette();
            initEasterEgg();
        }
        /* ── NEW FEATURES ── */
        if (!mobileLite) {
            initStatCounters();
        }
        initSkillBars();
        initTestimonialCarousel();
        initPriceEstimator();
        if (!mobileLite) {
            initSpotlightCards();
            initScrambleText();
        }
    };

    init();
})();
