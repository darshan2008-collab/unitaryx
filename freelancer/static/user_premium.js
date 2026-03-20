(() => {
    "use strict";

    const q = (s, p = document) => p.querySelector(s);
    const qa = (s, p = document) => Array.from(p.querySelectorAll(s));

    const state = {
        mx: window.innerWidth / 2,
        my: window.innerHeight / 2,
        tx: window.innerWidth / 2,
        ty: window.innerHeight / 2,
        sliderIndex: 0,
        sliderTimer: null,
        audioCtx: null,
    };

    const loader = q("#ux-loader");
    const cursor = q("#ux-cursor");
    const trail = q("#ux-cursor-trail");
    const nav = q("#ux-nav");

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
        window.addEventListener("load", () => {
            setTimeout(() => loader?.classList.add("hide"), 650);
        });
    };

    const initCursor = () => {
        if (!cursor || !trail || window.matchMedia("(max-width: 700px)").matches) return;
        window.addEventListener("mousemove", (e) => {
            state.mx = e.clientX;
            state.my = e.clientY;
        });

        const tick = () => {
            state.tx += (state.mx - state.tx) * 0.16;
            state.ty += (state.my - state.ty) * 0.16;
            cursor.style.left = `${state.mx}px`;
            cursor.style.top = `${state.my}px`;
            trail.style.left = `${state.tx}px`;
            trail.style.top = `${state.ty}px`;
            requestAnimationFrame(tick);
        };
        tick();
    };

    const initBackgroundParticles = () => {
        const canvas = q("#ux-bg-canvas");
        if (!canvas) return;
        const ctx = canvas.getContext("2d");
        const nodes = [];

        const resize = () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        };
        resize();
        window.addEventListener("resize", resize);

        for (let i = 0; i < 70; i += 1) {
            nodes.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                vx: (Math.random() - 0.5) * 0.32,
                vy: (Math.random() - 0.5) * 0.32,
                r: Math.random() * 1.7 + 0.5,
            });
        }

        const draw = () => {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            nodes.forEach((n, i) => {
                n.x += n.vx;
                n.y += n.vy;
                if (n.x < 0 || n.x > canvas.width) n.vx *= -1;
                if (n.y < 0 || n.y > canvas.height) n.vy *= -1;

                const dx = state.mx - n.x;
                const dy = state.my - n.y;
                const d = Math.sqrt(dx * dx + dy * dy);
                if (d < 140 && d > 0) {
                    n.x -= (dx / d) * 0.35;
                    n.y -= (dy / d) * 0.35;
                }

                ctx.beginPath();
                ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
                ctx.fillStyle = "rgba(148,163,184,0.6)";
                ctx.fill();

                for (let j = i + 1; j < nodes.length; j += 1) {
                    const m = nodes[j];
                    const lx = n.x - m.x;
                    const ly = n.y - m.y;
                    const ld = Math.sqrt(lx * lx + ly * ly);
                    if (ld < 110) {
                        ctx.beginPath();
                        ctx.moveTo(n.x, n.y);
                        ctx.lineTo(m.x, m.y);
                        ctx.strokeStyle = `rgba(34,211,238,${0.12 - ld / 1000})`;
                        ctx.lineWidth = 1;
                        ctx.stroke();
                    }
                }
            });
            requestAnimationFrame(draw);
        };
        draw();
    };

    const initHeadline = () => {
        const el = q("#ux-headline");
        if (!el) return;
        const text = el.textContent || "";
        el.textContent = "";
        [...text].forEach((ch, idx) => {
            const span = document.createElement("span");
            span.className = "char";
            span.textContent = ch === " " ? "\u00A0" : ch;
            span.style.transition = `opacity 0.45s ease ${idx * 22}ms, transform 0.45s ease ${idx * 22}ms, filter 0.45s ease ${idx * 22}ms`;
            el.appendChild(span);
            requestAnimationFrame(() => {
                span.style.opacity = "1";
                span.style.transform = "translateY(0)";
                span.style.filter = "blur(0)";
            });
        });
        setTimeout(() => q("#ux-sub")?.classList.add("show"), 480);
    };

    const initReveals = () => {
        const obs = new IntersectionObserver((entries) => {
            entries.forEach((e) => {
                if (e.isIntersecting) {
                    e.target.classList.add("is-visible");
                    obs.unobserve(e.target);
                }
            });
        }, { threshold: 0.14 });
        qa(".ux-reveal").forEach((n) => obs.observe(n));
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
        if (!floats.length) return;
        window.addEventListener("mousemove", (e) => {
            const nx = e.clientX / window.innerWidth - 0.5;
            const ny = e.clientY / window.innerHeight - 0.5;
            floats.forEach((f, idx) => {
                const d = (idx + 1) * 6;
                f.style.transform = `translate(${nx * d}px, ${ny * d}px)`;
            });
        });
    };

    const initSkillTags = () => {
        qa(".ux-tag").forEach((tag, idx) => {
            setTimeout(() => tag.classList.add("show"), 480 + idx * 90);
        });
    };

    const initMeters = () => {
        const obs = new IntersectionObserver((entries) => {
            entries.forEach((entry) => {
                if (!entry.isIntersecting) return;
                qa(".ux-meter-fill", entry.target).forEach((bar) => {
                    const val = bar.getAttribute("data-value") || "0";
                    bar.style.width = `${val}%`;
                });
                obs.unobserve(entry.target);
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

    const initAccentSwitch = () => {
        const chips = qa(".ux-accent-chip");
        if (!chips.length) return;
        const root = document.documentElement;

        const themes = {
            neon: { blue: "#22d3ee", violet: "#8b5cf6", gold: "#f59e0b" },
            ocean: { blue: "#38bdf8", violet: "#0ea5e9", gold: "#14b8a6" },
            ember: { blue: "#fb7185", violet: "#f43f5e", gold: "#f97316" },
        };

        chips.forEach((chip) => {
            chip.addEventListener("click", () => {
                const key = chip.getAttribute("data-accent") || "neon";
                const t = themes[key] || themes.neon;
                root.style.setProperty("--ux-blue", t.blue);
                root.style.setProperty("--ux-violet", t.violet);
                root.style.setProperty("--ux-gold", t.gold);
                chips.forEach((x) => x.classList.toggle("active", x === chip));
            });
        });
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

    const initServiceTilt = () => {
        qa(".ux-service-card").forEach((card) => {
            card.addEventListener("mousemove", (e) => {
                if (window.matchMedia("(max-width: 700px)").matches) return;
                const r = card.getBoundingClientRect();
                const x = (e.clientX - r.left) / r.width - 0.5;
                const y = (e.clientY - r.top) / r.height - 0.5;
                card.style.transform = `rotateY(${x * 10}deg) rotateX(${y * -10}deg) translateY(-4px)`;
            });
            card.addEventListener("mouseleave", () => {
                card.style.transform = "rotateY(0) rotateX(0) translateY(0)";
            });
        });
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
        const copyBtn = q("#ux-copy-email");
        const emailText = q("#ux-email-text");
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

        copyBtn?.addEventListener("click", async () => {
            const value = (emailText?.textContent || "").trim();
            if (!value) return;
            try {
                await navigator.clipboard.writeText(value);
                copyBtn.textContent = "Copied";
                setTimeout(() => {
                    copyBtn.textContent = "Copy";
                }, 1200);
            } catch (_err) {
                copyBtn.textContent = "Failed";
                setTimeout(() => {
                    copyBtn.textContent = "Copy";
                }, 1200);
            }
        });

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
                const data = await res.json();
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
                if (btn) btn.textContent = "Submit Project Request";
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

    const init = () => {
        initLoader();
        initCursor();
        initBackgroundParticles();
        initHeadline();
        initReveals();
        initNavActive();
        initMagnetic();
        initRipples();
        initHeroParallax();
        initSkillTags();
        initMeters();
        initProjectFilter();
        initLiveStatus();
        initPricingMode();
        initServiceTilt();
        initTestimonial();
        initFaq();
        initContact();
        initAccentSwitch();
        initScrollProgress();
        initCommandPalette();
        initEasterEgg();
    };

    init();
})();
