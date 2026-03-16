/* ============================================================
   CINEMATIC SCROLL ENGINE — Unitary X
   Apple-style cinematic scroll system.
   Works purely as an additive layer — doesn't touch existing JS.
   ============================================================ */

(() => {
  'use strict';

  /* ── Scroll Progress Bar ──────────────────────────────────── */
  const progressBar = document.createElement('div');
  progressBar.id = 'cx-progress-bar';
  document.body.prepend(progressBar);

  function updateProgressBar() {
    const scrolled = window.scrollY;
    const total = document.documentElement.scrollHeight - window.innerHeight;
    progressBar.style.width = (total > 0 ? (scrolled / total) * 100 : 0) + '%';
  }

  /* ── Utilities ────────────────────────────────────────────── */
  function qs(sel, ctx = document)  { return ctx.querySelector(sel); }
  function qsa(sel, ctx = document) { return [...ctx.querySelectorAll(sel)]; }

  /* ── IntersectionObserver Factory ────────────────────────── */
  function createObserver(callback, options = {}) {
    return new IntersectionObserver(callback, {
      threshold: options.threshold || 0.12,
      rootMargin: options.rootMargin || '0px 0px -60px 0px',
    });
  }

  /* ── 1. Marquee Strip ────────────────────────────────────── */
  const marqueeStrip = qs('.marquee-strip');
  if (marqueeStrip) {
    const mObs = createObserver(([entry]) => {
      if (entry.isIntersecting) {
        entry.target.classList.add('cx-visible');
        mObs.unobserve(entry.target);
      }
    });
    mObs.observe(marqueeStrip);
  }

  /* ── 2. Section Headers — tag + title + desc stagger ─────── */
  qsa('.section-header').forEach(header => {
    const tag   = qs('.section-tag',   header);
    const title = qs('.section-title', header);
    const desc  = qs('.section-desc',  header);

    // Apply cinematic classes
    if (tag)   { tag.classList.add('cx-tag-reveal'); }
    if (title) { title.classList.add('cx-reveal');   title.classList.add('cx-delay-2'); }
    if (desc)  { desc.classList.add('cx-reveal');    desc.classList.add('cx-delay-3'); }

    const obs = createObserver(([entry]) => {
      if (entry.isIntersecting) {
        if (tag)   { setTimeout(() => tag.classList.add('cx-visible'),   50);  }
        if (title) { setTimeout(() => title.classList.add('cx-visible'), 150); }
        if (desc)  { setTimeout(() => desc.classList.add('cx-visible'),  280); }
        obs.unobserve(entry.target);
      }
    }, { threshold: 0.15 });
    obs.observe(header);
  });

  /* ── 3. Service Cards — staggered cinematic entry ─────────── */
  qsa('.service-card').forEach((card, i) => {
    card.classList.add('cx-card');
    const obs = createObserver(([entry]) => {
      if (entry.isIntersecting) {
        setTimeout(() => card.classList.add('cx-visible'), i * 80);
        obs.unobserve(card);
      }
    }, { threshold: 0.08 });
    obs.observe(card);
  });

  /* ── 4. Project Cards ─────────────────────────────────────── */
  qsa('.project-card').forEach((card, i) => {
    card.classList.add('cx-card');
    const obs = createObserver(([entry]) => {
      if (entry.isIntersecting) {
        setTimeout(() => card.classList.add('cx-visible'), i * 75);
        obs.unobserve(card);
      }
    }, { threshold: 0.08 });
    obs.observe(card);
  });

  /* ── 5. Process Steps ─────────────────────────────────────── */
  qsa('.process-step').forEach((step, i) => {
    step.classList.add('cx-reveal');
    const stepIcon = qs('.step-icon', step);
    if (stepIcon) stepIcon.classList.add('cx-icon-animate');

    const obs = createObserver(([entry]) => {
      if (entry.isIntersecting) {
        setTimeout(() => {
          step.classList.add('cx-visible');
          if (stepIcon) setTimeout(() => stepIcon.classList.add('cx-visible'), 200);
        }, i * 130);
        obs.unobserve(step);
      }
    }, { threshold: 0.1 });
    obs.observe(step);
  });

  /* ── 6. Why Cards ─────────────────────────────────────────── */
  qsa('.why-card').forEach((card, i) => {
    card.classList.add('cx-card');
    const icon = qs('.why-icon', card);
    if (icon) icon.classList.add('cx-icon-animate');

    const obs = createObserver(([entry]) => {
      if (entry.isIntersecting) {
        setTimeout(() => {
          card.classList.add('cx-visible');
          if (icon) setTimeout(() => icon.classList.add('cx-visible'), 250);
        }, i * 90);
        obs.unobserve(card);
      }
    }, { threshold: 0.08 });
    obs.observe(card);
  });

  /* ── 7. Contact Wrapper ───────────────────────────────────── */
  const contactWrapper = qs('.contact-wrapper');
  if (contactWrapper) {
    const contactInfo = qs('.contact-info', contactWrapper);
    const contactForm = qs('.contact-form-container', contactWrapper);
    if (contactInfo) contactInfo.classList.add('cx-reveal-left');
    if (contactForm) contactForm.classList.add('cx-reveal-right');

    const obs = createObserver(([entry]) => {
      if (entry.isIntersecting) {
        setTimeout(() => {
          if (contactInfo) contactInfo.classList.add('cx-visible');
          if (contactForm) setTimeout(() => contactForm.classList.add('cx-visible'), 160);
        }, 50);
        obs.unobserve(entry.target);
      }
    }, { threshold: 0.1 });
    obs.observe(contactWrapper);
  }

  /* ── 8. Contact Items — stagger ──────────────────────────── */
  qsa('.contact-item').forEach((item, i) => {
    item.classList.add('cx-reveal');
    const obs = createObserver(([entry]) => {
      if (entry.isIntersecting) {
        setTimeout(() => item.classList.add('cx-visible'), i * 100 + 300);
        obs.unobserve(item);
      }
    }, { threshold: 0.1 });
    obs.observe(item);
  });

  /* ── 9. Availability Badge ────────────────────────────────── */
  const availBadge = qs('.availability-badge');
  if (availBadge) {
    availBadge.classList.add('cx-reveal');
    const obs = createObserver(([entry]) => {
      if (entry.isIntersecting) {
        setTimeout(() => availBadge.classList.add('cx-visible'), 500);
        obs.unobserve(availBadge);
      }
    });
    obs.observe(availBadge);
  }

  /* ── 10. Parallax — subtle Y-drift for depth ─────────────── */
  const parallaxTargets = [];

  // Floating orbs (existing decorative elements) get subtle parallax
  qsa('.glass-orb, .proj-orb').forEach(orb => {
    const speed = parseFloat(orb.dataset.parallax) || (Math.random() * 0.08 + 0.03);
    parallaxTargets.push({ el: orb, speed, baseY: 0 });
  });

  // Service icon wraps get very slight parallax
  qsa('.service-icon-wrap').forEach(icon => {
    parallaxTargets.push({ el: icon, speed: 0.015, baseY: 0 });
  });

  // Step numbers get subtle parallax
  qsa('.step-number').forEach(num => {
    parallaxTargets.push({ el: num, speed: 0.04, baseY: 0 });
  });

  let ticking = false;
  let lastScrollY = 0;

  function runParallax() {
    const scrollY = window.scrollY;
    parallaxTargets.forEach(({ el, speed }) => {
      const rect = el.getBoundingClientRect();
      const centerOffset = rect.top + rect.height / 2 - window.innerHeight / 2;
      el.style.transform = el.style.transform.replace(/translateY\([^)]*\)/, '') +
        ` translateY(${centerOffset * speed * -1}px)`;
    });
    ticking = false;
  }

  /* ── 11. Filter Buttons — stagger on load ────────────────── */
  qsa('.filter-btn').forEach((btn, i) => {
    btn.classList.add('cx-reveal');
    const obs = createObserver(([entry]) => {
      if (entry.isIntersecting) {
        setTimeout(() => btn.classList.add('cx-visible'), i * 70 + 200);
        obs.unobserve(btn);
      }
    });
    obs.observe(btn);
  });

  /* ── 12. Projects Filter Reveal ──────────────────────────── */
  const projectsFilter = qs('.projects-filter');
  if (projectsFilter) {
    projectsFilter.classList.add('cx-reveal');
    const obs = createObserver(([entry]) => {
      if (entry.isIntersecting) {
        setTimeout(() => projectsFilter.classList.add('cx-visible'), 100);
        obs.unobserve(projectsFilter);
      }
    });
    obs.observe(projectsFilter);
  }

  /* ── 13. Button Ripple Effect ────────────────────────────── */
  const rippleSelectors = [
    '.btn-primary', '.btn-secondary', '.btn-hire',
    '.service-cta', '.proj-view-btn', '.form-submit',
    '.btn-login-cta', '.plan-cta', '.filter-btn'
  ].join(',');

  document.addEventListener('click', e => {
    const btn = e.target.closest(rippleSelectors);
    if (!btn) return;

    const ripple = document.createElement('span');
    ripple.classList.add('cx-ripple');
    const rect = btn.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height) * 2;
    ripple.style.cssText = `
      width: ${size}px;
      height: ${size}px;
      left: ${e.clientX - rect.left - size / 2}px;
      top: ${e.clientY - rect.top - size / 2}px;
    `;
    btn.appendChild(ripple);
    setTimeout(() => ripple.remove(), 700);
  });

  /* ── 14. Line Dividers ────────────────────────────────────── */
  qsa('.service-footer').forEach(footer => {
    // Service card footer borders reveal as animated lines
    const obs = createObserver(([entry]) => {
      if (entry.isIntersecting) {
        entry.target.style.borderTopWidth = '1px';
        obs.unobserve(entry.target);
      }
    });
    obs.observe(footer);
  });

  /* ── 15. Step Connector Lines Animate ────────────────────── */
  qsa('.step-connector').forEach((connector, i) => {
    connector.style.transform = 'scaleX(0)';
    connector.style.transformOrigin = 'left';
    connector.style.transition = 'transform 0.8s cubic-bezier(0.16, 1, 0.3, 1)';
    const obs = createObserver(([entry]) => {
      if (entry.isIntersecting) {
        setTimeout(() => {
          connector.style.transform = 'scaleX(1)';
        }, i * 200 + 400);
        obs.unobserve(connector);
      }
    }, { threshold: 0.5 });
    obs.observe(connector);
  });

  /* ── 16. Scroll-ahead Smooth Glow on Navbar ──────────────── */
  const navbar = document.getElementById('navbar');
  let lastNavBg = '';

  function updateNavCinematic() {
    if (!navbar) return;
    const scrolled = window.scrollY;
    // Subtle shadow intensity based on scroll depth
    const shadowOpacity = Math.min(scrolled / 400, 0.12);
    if (scrolled > 60) {
      navbar.style.boxShadow = `0 4px 30px rgba(15, 23, 42, ${shadowOpacity})`;
    } else {
      navbar.style.boxShadow = '';
    }
  }

  /* ── 17. Why Card Number Pop ─────────────────────────────── */
  // Step numbers bloom in when parent section is visible
  qsa('.step-number').forEach((num, i) => {
    num.classList.add('cx-reveal');
    const obs = createObserver(([entry]) => {
      if (entry.isIntersecting) {
        setTimeout(() => num.classList.add('cx-visible'), i * 130);
        obs.unobserve(num);
      }
    }, { threshold: 0.2 });
    obs.observe(num);
  });

  /* ── 18. Hero Subtitle Parallax Drift ────────────────────── */
  const heroSubtitle  = qs('.hero-subtitle');
  const heroCta       = qs('.hero-cta');
  const techStackRow  = qs('.tech-stack-row');
  const heroScrollHint = qs('.hero-scroll-hint');

  /* ── 19. Scroll-based Depth for Project Thumbnails ────────── */
  qsa('.proj-thumb-bg').forEach(thumb => {
    parallaxTargets.push({ el: thumb, speed: 0.025, baseY: 0 });
  });

  /* ── 20. Cinematic Section transition glow ───────────────── */
  // Subtle shimmer line that appears at top of each section as you scroll in
  qsa('section').forEach(section => {
    const shimmer = document.createElement('div');
    shimmer.style.cssText = `
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 1px;
      background: linear-gradient(90deg, transparent, rgba(99,102,241,0.15), rgba(37,99,235,0.2), rgba(6,182,212,0.15), transparent);
      opacity: 0;
      z-index: 5;
      pointer-events: none;
      transition: opacity 0.8s ease;
    `;
    section.style.position = 'relative';
    section.appendChild(shimmer);

    const obs = createObserver(([entry]) => {
      shimmer.style.opacity = entry.isIntersecting ? '1' : '0';
    }, { threshold: 0.05 });
    obs.observe(section);
  });

  /* ── RAF-based scroll handler ────────────────────────────── */
  window.addEventListener('scroll', () => {
    updateProgressBar();
    updateNavCinematic();

    if (!ticking) {
      requestAnimationFrame(runParallax);
      ticking = true;
    }
  }, { passive: true });

  /* ── Initial calls ───────────────────────────────────────── */
  updateProgressBar();
  updateNavCinematic();

  /* ── Page Load entrance ────────────────────────────────────── */
  // Hero section elements animate on first load
  window.addEventListener('load', () => {
    // Marquee strip check on load
    if (marqueeStrip) {
      const rect = marqueeStrip.getBoundingClientRect();
      if (rect.top < window.innerHeight) {
        setTimeout(() => marqueeStrip.classList.add('cx-visible'), 600);
      }
    }
  });

  /* ── Lenis-style eased scrolling via CSS scroll-behavior ─── */
  // Already set via html { scroll-behavior: smooth } in cinematic.css
  // For anchor clicks, enhance with custom easing
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', e => {
      const target = document.querySelector(anchor.getAttribute('href'));
      if (!target) return;
      e.preventDefault();
      const targetY = target.getBoundingClientRect().top + window.scrollY - 72;
      smoothScrollTo(targetY, 900);
    });
  });

  function smoothScrollTo(targetY, duration) {
    const startY = window.scrollY;
    const diff   = targetY - startY;
    let startTime = null;

    function easeInOutQuart(t) {
      return t < 0.5 ? 8 * t * t * t * t : 1 - Math.pow(-2 * t + 2, 4) / 2;
    }

    function step(ts) {
      if (!startTime) startTime = ts;
      const elapsed = ts - startTime;
      const progress = Math.min(elapsed / duration, 1);
      window.scrollTo(0, startY + diff * easeInOutQuart(progress));
      if (progress < 1) requestAnimationFrame(step);
    }

    requestAnimationFrame(step);
  }

  console.log('[Cinematic Engine] ✨ Loaded — Apple-style scroll animations active.');
})();
