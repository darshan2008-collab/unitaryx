/* ============================================================
   FUTURISTIC DIGITAL UNIVERSE ENGINE — Unitary X
   Spatial 3D depth, Magnetic Buttons, Custom Cursor
   ============================================================ */

(() => {
    'use strict';

    /* ── Cinematic Loader ──────────────────────────────────────── */
    const loader = document.createElement('div');
    loader.id = 'fx-loader';
    loader.innerHTML = `
        <div class="fx-loader-logo">UNITARY X</div>
        <div class="fx-loader-bar-bg"><div class="fx-loader-bar"></div></div>
    `;
    document.body.appendChild(loader);

    window.addEventListener('load', () => {
        const bar = loader.querySelector('.fx-loader-bar');
        if(bar) {
            bar.style.transition = 'width 1s cubic-bezier(0.16, 1, 0.3, 1)';
            bar.style.width = '100%';
            setTimeout(() => {
                document.body.classList.add('fx-loaded');
                setTimeout(() => loader.remove(), 1000);
            }, 1000);
        }
    });

    /* ── Nebula Background ─────────────────────────────────────── */
    const nebula = document.createElement('div');
    nebula.className = 'fx-nebula';
    document.body.prepend(nebula);

    /* ── Custom Cursor System ──────────────────────────────────── */
    const dot = document.createElement('div');
    dot.id = 'fx-cursor-dot';
    const ring = document.createElement('div');
    ring.id = 'fx-cursor-ring';
    
    document.body.appendChild(dot);
    document.body.appendChild(ring);

    let mouseX = window.innerWidth / 2;
    let mouseY = window.innerHeight / 2;
    let ringX = mouseX;
    let ringY = mouseY;

    document.addEventListener('mousemove', (e) => {
        mouseX = e.clientX;
        mouseY = e.clientY;
        // Dot follows instantly
        dot.style.transform = `translate(${mouseX}px, ${mouseY}px) translate(-50%, -50%)`;
    });

    // Ring follows with lerp (easing)
    function animateRing() {
        const speed = 0.15;
        ringX += (mouseX - ringX) * speed;
        ringY += (mouseY - ringY) * speed;
        ring.style.transform = `translate(${ringX}px, ${ringY}px) translate(-50%, -50%)`;
        requestAnimationFrame(animateRing);
    }
    requestAnimationFrame(animateRing);

    // Hover effect on interactables
    const interactables = document.querySelectorAll('a, button, input, select, textarea, .service-card, .project-card, .why-card');
    interactables.forEach(el => {
        el.addEventListener('mouseenter', () => document.body.classList.add('fx-hovering'));
        el.addEventListener('mouseleave', () => document.body.classList.remove('fx-hovering'));
    });

    /* ── Advanced 3D Spatial Tilt (Cards) ──────────────────────── */
    const tiltCards = document.querySelectorAll('.service-card, .project-card, .why-card');
    tiltCards.forEach(card => {
        card.classList.add('fx-tilt');
        
        // Wrap children to create depth
        const inner = document.createElement('div');
        inner.className = 'fx-tilt-inner';
        while (card.firstChild) {
            inner.appendChild(card.firstChild);
        }
        card.appendChild(inner);

        card.addEventListener('mousemove', (e) => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left; // x position within the element
            const y = e.clientY - rect.top;  // y position within the element
            
            // Calculate rotation (-10 to 10 deg)
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            const rotateX = ((y - centerY) / centerY) * -10;
            const rotateY = ((x - centerX) / centerX) * 10;
            
            inner.style.transform = `rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
        });

        card.addEventListener('mouseleave', () => {
            inner.style.transform = `rotateX(0deg) rotateY(0deg)`;
        });
    });

    /* ── Magnetic Physics Buttons ──────────────────────────────── */
    const magneticBtns = document.querySelectorAll('.btn-primary, .btn-secondary, .btn-hire');
    magneticBtns.forEach(btn => {
        btn.classList.add('fx-magnetic');
        
        btn.addEventListener('mousemove', (e) => {
            const rect = btn.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            
            // Pull the button towards cursor slightly (Max 15px)
            const pullX = ((x - centerX) / centerX) * 15;
            const pullY = ((y - centerY) / centerY) * 15;
            
            btn.style.transform = `translate(${pullX}px, ${pullY}px)`;
        });

        btn.addEventListener('mouseleave', () => {
            btn.style.transform = `translate(0px, 0px)`;
        });
    });

    /* ── Enhance Existing Particle Engine ──────────────────────── */
    // Since script.js already initializes a canvas, we grab it and add cursor repulsion
    // By simulating a new mouse event structure or overriding the script's arrays if exposed.
    // Instead of fighting script.js, we add an overlay spatial dust effect
    const dustCanvas = document.createElement('canvas');
    dustCanvas.style.cssText = 'position:fixed;top:0;left:0;width:100vw;height:100vh;z-index:-1;pointer-events:none;opacity:0.6;mix-blend-mode:screen;';
    document.body.prepend(dustCanvas);
    
    const ctx = dustCanvas.getContext('2d');
    let width, height;
    
    function resize() {
        width = dustCanvas.width = window.innerWidth;
        height = dustCanvas.height = window.innerHeight;
    }
    window.addEventListener('resize', resize);
    resize();

    const particles = [];
    for(let i=0; i<80; i++) {
        particles.push({
            x: Math.random() * width,
            y: Math.random() * height,
            vx: (Math.random() - 0.5) * 0.5,
            vy: (Math.random() - 0.5) * 0.5,
            size: Math.random() * 2 + 0.5,
            baseX: 0, baseY: 0
        });
    }

    function animateDust() {
        ctx.clearRect(0, 0, width, height);
        
        particles.forEach(p => {
            // Repulsion from cursor
            const dx = p.x - mouseX;
            const dy = p.y - mouseY;
            const dist = Math.sqrt(dx*dx + dy*dy);
            
            if (dist < 150) {
                const force = (150 - dist) / 150;
                p.vx += (dx / dist) * force * 0.1;
                p.vy += (dy / dist) * force * 0.1;
                
                // Draw connecting line to cursor for "magnetic" feel
                ctx.beginPath();
                ctx.moveTo(p.x, p.y);
                ctx.lineTo(mouseX, mouseY);
                ctx.strokeStyle = `rgba(59, 130, 246, ${0.15 * force})`;
                ctx.lineWidth = 1;
                ctx.stroke();
            }

            // Friction
            p.vx *= 0.98;
            p.vy *= 0.98;

            // Base movement
            p.x += p.vx + (Math.sin(Date.now() * 0.001 + p.size) * 0.2);
            p.y += p.vy + (Math.cos(Date.now() * 0.001 + p.size) * 0.2);

            // Bounds
            if (p.x < 0) p.x = width;
            if (p.x > width) p.x = 0;
            if (p.y < 0) p.y = height;
            if (p.y > height) p.y = 0;

            // Draw particle
            ctx.beginPath();
            ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
            ctx.fillStyle = `rgba(139, 92, 246, ${p.size/3})`;
            ctx.fill();
        });

        requestAnimationFrame(animateDust);
    }
    animateDust();

    console.log('[Futuristic Universe Engine] ✨ Loaded. 3D Spatial interactions active.');

})();
