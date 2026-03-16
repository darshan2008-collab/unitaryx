/* ============================================================
   Unitary X — script.js
   Premium Freelancer Website — All Interactivity
   ============================================================ */

(() => {
  'use strict';



  // ── Particle Canvas ────────────────────────────────────────
  const canvas = document.getElementById('particle-canvas');
  if (canvas) {
    const ctx = canvas.getContext('2d');
    let particles = [];

    const mouse = { x: -1000, y: -1000 };
    window.addEventListener('mousemove', e => {
      mouse.x = e.clientX;
      mouse.y = e.clientY;
    });

    function resizeCanvas() {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    }
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    class Particle {
      constructor() { this.reset(true); }
      reset(initial = false) {
        this.x = initial ? Math.random() * canvas.width : canvas.width / 2;
        this.y = initial ? Math.random() * canvas.height : canvas.height / 2;

        // Burst outward from center or random drift if initial
        const angle = Math.random() * Math.PI * 2;
        const speed = Math.random() * 0.4 + 0.1; // Slower speed
        this.vx = Math.cos(angle) * speed;
        this.vy = Math.sin(angle) * speed;

        this.r = Math.random() * 1.5 + 0.5; // Smaller dots
        this.alpha = Math.random() * 0.4 + 0.1; // Lower opacity

        // Google-style colors: Blue, Purple, Pink, Cyan
        const colors = ['66, 133, 244', '142, 36, 170', '233, 30, 99', '0, 188, 212', '103, 58, 183'];
        this.color = colors[Math.floor(Math.random() * colors.length)];

        // Add a slight elongation factor for "pill" look 
        this.elongation = Math.random() * 1.5 + 1; // Less elongated
        this.rotation = angle;
      }
      update() {
        // Antigravity: Push away from mouse strongly
        let dx = this.x - mouse.x;
        let dy = this.y - mouse.y;
        let dist = Math.sqrt(dx * dx + dy * dy);

        if (dist < 150) { // Reduced interaction radius
          const force = (150 - dist) / 150;
          this.vx += (dx / dist) * force * 0.3; // Softer push
          this.vy += (dy / dist) * force * 0.3;
        }

        // Apply friction to max speed
        this.vx *= 0.98;
        this.vy *= 0.98;

        // Base outward movement
        this.x += this.vx;
        this.y += this.vy;
        this.rotation = Math.atan2(this.vy, this.vx);

        if (this.x < 0 || this.x > canvas.width || this.y < 0 || this.y > canvas.height) this.reset();
      }
      draw() {
        ctx.save();
        ctx.translate(this.x, this.y);
        ctx.rotate(this.rotation);
        ctx.beginPath();
        // Draw elongated pill shape
        ctx.roundRect(-this.r * this.elongation / 2, -this.r / 2, this.r * this.elongation, this.r, this.r);
        ctx.fillStyle = `rgba(${this.color}, ${this.alpha})`;
        ctx.fill();
        ctx.restore();
      }
    }

    // Decrease particle count for a milder look
    const COUNT = Math.min(150, Math.floor(window.innerWidth / 8));
    for (let i = 0; i < COUNT; i++) particles.push(new Particle());

    function animateParticles() {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      particles.forEach(p => { p.update(); p.draw(); });
      requestAnimationFrame(animateParticles);
    }
    animateParticles();
  }

  // ── Navbar Scroll Effect ───────────────────────────────────
  const navbar = document.getElementById('navbar');
  window.addEventListener('scroll', () => {
    if (navbar) navbar.classList.toggle('scrolled', window.scrollY > 60);
    updateActiveLink();
    toggleScrollTop();
  });

  // ── Mobile Menu ────────────────────────────────────────────
  const hamburger = document.getElementById('hamburger');
  const navLinks = document.getElementById('nav-links');
  if (hamburger && navLinks) {
    hamburger.addEventListener('click', () => {
      hamburger.classList.toggle('open');
      navLinks.classList.toggle('open');
    });
    navLinks.querySelectorAll('a').forEach(a => {
      a.addEventListener('click', () => {
        hamburger.classList.remove('open');
        navLinks.classList.remove('open');
      });
    });
  }

  // ── Active Nav Link on Scroll ──────────────────────────────
  function updateActiveLink() {
    const sections = document.querySelectorAll('section[id]');
    const scrollY = window.scrollY + 100;
    sections.forEach(s => {
      const top = s.offsetTop;
      const h = s.offsetHeight;
      const link = document.querySelector(`.nav-link[href="#${s.id}"]`);
      if (link) link.classList.toggle('active', scrollY >= top && scrollY < top + h);
    });
  }

  // ── Counter Animation ──────────────────────────────────────
  function animateCounters() {
    document.querySelectorAll('.stat-number').forEach(el => {
      const target = parseInt(el.dataset.count);
      const dur = 1800;
      const step = 16;
      const inc = target / (dur / step);
      let current = 0;
      const timer = setInterval(() => {
        current += inc;
        if (current >= target) { el.textContent = target; clearInterval(timer); }
        else { el.textContent = Math.floor(current); }
      }, step);
    });
  }

  // ── Scroll Reveal ──────────────────────────────────────────
  const reveals = document.querySelectorAll(
    '.service-card, .project-card, .process-step, .why-card, .contact-wrapper, .section-header'
  );
  reveals.forEach(el => el.classList.add('reveal'));

  let countersStarted = false;
  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('animate');
        revealObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.1 });
  reveals.forEach(el => revealObserver.observe(el));

  // Start counters when hero stats are visible
  const statsObserver = new IntersectionObserver(entries => {
    if (entries[0].isIntersecting && !countersStarted) {
      countersStarted = true;
      animateCounters();
    }
  }, { threshold: 0.5 });
  const heroStats = document.querySelector('.hero-stats');
  if (heroStats) statsObserver.observe(heroStats);

  // ── Projects Filter ────────────────────────────────────────
  const filterBtns = document.querySelectorAll('.filter-btn');
  const projCards = document.querySelectorAll('.project-card');

  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      const filter = btn.dataset.filter;

      projCards.forEach(card => {
        const match = filter === 'all' || card.dataset.category === filter;
        card.style.opacity = '0';
        card.style.transform = 'scale(0.9)';
        setTimeout(() => {
          card.style.display = match ? '' : 'none';
          if (match) {
            requestAnimationFrame(() => {
              card.style.opacity = '1';
              card.style.transform = 'scale(1)';
              card.style.transition = 'opacity 0.4s, transform 0.4s';
            });
          }
        }, 150);
      });
    });
  });

  // ── Contact Form (AJAX to Flask) ───────────────────────────
  const form = document.getElementById('contact-form');
  const submitBtn = document.getElementById('form-submit-btn');
  const successBox = document.getElementById('form-success');
  const errorBox = document.getElementById('form-error-msg');
  const successMsg = document.getElementById('success-msg');
  const errorMsg = document.getElementById('error-msg');

  // Field errors
  const fieldErrors = {
    name: document.getElementById('err-name'),
    email: document.getElementById('err-email'),
    service: document.getElementById('err-service'),
    message: document.getElementById('err-message'),
  };

  function clearErrors() {
    Object.values(fieldErrors).forEach(el => { if (el) el.textContent = ''; });
    if (successBox) successBox.style.display = 'none';
    if (errorBox) errorBox.style.display = 'none';
  }

  if (form) {
    form.addEventListener('submit', async e => {
      e.preventDefault();
      clearErrors();

      const data = {
        name: document.getElementById('cf-name')?.value.trim(),
        email: document.getElementById('cf-email')?.value.trim(),
        phone: document.getElementById('cf-phone')?.value.trim(),
        service: document.getElementById('cf-service')?.value,
        deadline: document.getElementById('cf-deadline')?.value,
        message: document.getElementById('cf-message')?.value.trim(),
      };

      if (submitBtn) { submitBtn.disabled = true; submitBtn.querySelector('span').textContent = 'Sending…'; }

      try {
        const res = await fetch('/api/contact', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content')
          },
          body: JSON.stringify(data),
        });
        const json = await res.json();

        if (res.status === 401 && json.redirect) {
          window.location.href = json.redirect;
          return;
        }

        if (res.ok && json.success) {
          if (successBox) { successBox.style.display = 'flex'; successMsg.textContent = json.message; }
          form.reset();
          if (json.whatsapp_url) {
            window.open(json.whatsapp_url, '_blank');
          }
        } else {
          if (json.errors) {
            Object.entries(json.errors).forEach(([k, v]) => {
              if (fieldErrors[k]) fieldErrors[k].textContent = v;
            });
          } else {
            if (errorBox) { errorBox.style.display = 'flex'; errorMsg.textContent = json.message || 'Something went wrong.'; }
          }
        }
      } catch {
        if (errorBox) { errorBox.style.display = 'flex'; errorMsg.textContent = 'Network error. Please try again.'; }
      } finally {
        if (submitBtn) { submitBtn.disabled = false; submitBtn.querySelector('span').textContent = 'Send Project Request'; }
      }
    });
  }

  // ── Scroll to Top ──────────────────────────────────────────
  const scrollTopBtn = document.getElementById('scroll-top');
  function toggleScrollTop() {
    if (scrollTopBtn) scrollTopBtn.classList.toggle('visible', window.scrollY > 400);
  }
  scrollTopBtn?.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));

  // ── Smooth Anchor Scroll ───────────────────────────────────
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', e => {
      const target = document.querySelector(a.getAttribute('href'));
      if (target) { e.preventDefault(); target.scrollIntoView({ behavior: 'smooth' }); }
    });
  });

  // ── Admin Gate Modal ───────────────────────────────────────
  const adminTrigger = document.getElementById('admin-trigger');
  const adminModal = document.getElementById('admin-modal');
  const adminClose = document.getElementById('admin-modal-close');
  const adminForm = document.getElementById('admin-gate-form');
  const adminPassInput = document.getElementById('admin-pass-input');
  const adminError = document.getElementById('admin-modal-error');
  const adminSubmit = document.getElementById('admin-modal-submit');

  const openAdminModal = () => {
    if (adminModal) {
      adminModal.classList.add('active');
      document.body.style.overflow = 'hidden';
      setTimeout(() => adminPassInput?.focus(), 100);
    }
  };

  const closeAdminModal = () => {
    if (adminModal) {
      adminModal.classList.remove('active');
      document.body.style.overflow = '';
      if (adminError) adminError.textContent = '';
      if (adminForm) adminForm.reset();
    }
  };

  adminTrigger?.addEventListener('click', e => {
    e.preventDefault();
    openAdminModal();
  });

  adminClose?.addEventListener('click', closeAdminModal);

  adminModal?.addEventListener('click', e => {
    if (e.target === adminModal) closeAdminModal();
  });

  if (adminForm) {
    adminForm.addEventListener('submit', async e => {
      e.preventDefault();
      const password = adminPassInput.value;
      if (!password) return;

      if (adminSubmit) {
        adminSubmit.disabled = true;
        adminSubmit.querySelector('span').textContent = 'Verifying…';
      }

      try {
        // Use the actual login route via FormData to satisfy Flask
        const formData = new FormData();
        formData.append('login_type', 'admin');
        formData.append('email', 'admin@unitaryx.com');
        formData.append('password', password);

        const res = await fetch('/login', {
          method: 'POST',
          headers: {
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.getAttribute('content')
          },
          body: formData
        });

        // If redirect happened, it means login was successful (usually)
        // In Flask, a successful login redirects. If we get a response with the login page content, it failed.
        const text = await res.text();

        if (res.url.includes('/admin')) {
          // Success! Redirect
          window.location.href = '/admin';
        } else if (text.includes('Invalid email or password') || text.includes('error')) {
          if (adminError) adminError.textContent = 'Incorrect admin password.';
          if (adminSubmit) {
            adminSubmit.disabled = false;
            adminSubmit.querySelector('span').textContent = 'Unlock Dashboard';
          }
        } else {
          // Fallback redirect
          window.location.href = '/admin';
        }
      } catch (err) {
        if (adminError) adminError.textContent = 'Connection error. Try again.';
        if (adminSubmit) {
          adminSubmit.disabled = false;
          adminSubmit.querySelector('span').textContent = 'Unlock Dashboard';
        }
      }
    });
  }

  // ── Password Toggle ──────────────────────────────────────────
  const togglePassBtn = document.getElementById('toggle-admin-pass');
  if (togglePassBtn && adminPassInput) {
    togglePassBtn.addEventListener('click', () => {
      const type = adminPassInput.getAttribute('type') === 'password' ? 'text' : 'password';
      adminPassInput.setAttribute('type', type);
      const icon = togglePassBtn.querySelector('i');
      if (icon) {
        icon.classList.toggle('fa-eye');
        icon.classList.toggle('fa-eye-slash');
      }
    });
  }
})();
