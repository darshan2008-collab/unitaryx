/**
 * UNITARY X - CINEMATIC PORTFOLIO
 * Next-Generation Interactive Experience
 * Powered by Three.js, GSAP, and WebGL
 */

// ============================================
// INITIALIZATION & SETUP
// ============================================

class CinematicPortfolio {
    constructor() {
        this.canvas = document.getElementById('canvas-3d');
        this.scene = null;
        this.camera = null;
        this.renderer = null;
        this.particles = [];
        this.neuralNetwork = null;
        this.animationFrameId = null;
        this.scrollProgress = 0;
        this.mouseX = 0;
        this.mouseY = 0;
        this.cursorElement = document.querySelector('.custom-cursor');
        this.cursorGlow = document.querySelector('.cursor-glow');

        this.init();
    }

    init() {
        // Setup Three.js scene
        this.setupThreeJS();

        // Initialize animations
        this.initAnimations();

        // Setup event listeners
        this.setupEventListeners();

        // Start render loop
        this.animate();

        // Hide loading screen
        this.hideLoadingScreen();
    }

    /**
     * Initialize Three.js Scene
     */
    setupThreeJS() {
        // Scene
        this.scene = new THREE.Scene();
        this.scene.background = new THREE.Color(0x050810);

        // Camera
        const width = window.innerWidth;
        const height = window.innerHeight;
        this.camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 10000);
        this.camera.position.z = 10;

        // Renderer
        this.renderer = new THREE.WebGLRenderer({
            canvas: this.canvas,
            antialias: true,
            alpha: true,
            precision: 'highp'
        });
        this.renderer.setSize(width, height);
        this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        this.renderer.setAnimationLoop(() => { });

        // Lighting
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
        this.scene.add(ambientLight);

        const pointLight = new THREE.PointLight(0x667eea, 100);
        pointLight.position.set(10, 10, 10);
        this.scene.add(pointLight);

        // Create particle field
        this.createParticleField();

        // Create neural network
        this.createNeuralNetwork();
    }

    /**
     * Create Dynamic Particle Field
     */
    createParticleField() {
        const geometry = new THREE.BufferGeometry();
        const count = 200;
        const positions = new Float32Array(count * 3);
        const colors = new Float32Array(count * 3);

        for (let i = 0; i < count; i++) {
            positions[i * 3] = (Math.random() - 0.5) * 100;
            positions[i * 3 + 1] = (Math.random() - 0.5) * 100;
            positions[i * 3 + 2] = (Math.random() - 0.5) * 100;

            // Color gradient from blue to purple
            colors[i * 3] = 0.4 + Math.random() * 0.3;
            colors[i * 3 + 1] = 0.49 + Math.random() * 0.2;
            colors[i * 3 + 2] = 0.92 + Math.random() * 0.08;
        }

        geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
        geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

        const material = new THREE.PointsMaterial({
            size: 0.3,
            vertexColors: true,
            sizeAttenuation: true,
            transparent: true,
            opacity: 0.7
        });

        this.particles = new THREE.Points(geometry, material);
        this.scene.add(this.particles);
    }

    /**
     * Create Neural Network Lines
     */
    createNeuralNetwork() {
        const geometry = new THREE.BufferGeometry();
        const material = new THREE.LineBasicMaterial({
            color: 0x667eea,
            transparent: true,
            opacity: 0.2,
            linewidth: 1
        });

        const positions = [];
        const nodeCount = 30;
        const nodes = [];

        // Create nodal positions
        for (let i = 0; i < nodeCount; i++) {
            nodes.push({
                x: (Math.random() - 0.5) * 80,
                y: (Math.random() - 0.5) * 80,
                z: (Math.random() - 0.5) * 80,
                vx: (Math.random() - 0.5) * 0.1,
                vy: (Math.random() - 0.5) * 0.1,
                vz: (Math.random() - 0.5) * 0.1
            });
        }

        // Connect nodes with threshold distance
        const threshold = 30;
        for (let i = 0; i < nodes.length; i++) {
            for (let j = i + 1; j < nodes.length; j++) {
                const dx = nodes[i].x - nodes[j].x;
                const dy = nodes[i].y - nodes[j].y;
                const dz = nodes[i].z - nodes[j].z;
                const distance = Math.sqrt(dx * dx + dy * dy + dz * dz);

                if (distance < threshold) {
                    positions.push(nodes[i].x, nodes[i].y, nodes[i].z);
                    positions.push(nodes[j].x, nodes[j].y, nodes[j].z);
                }
            }
        }

        if (positions.length > 0) {
            geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(positions), 3));
            this.neuralNetwork = new THREE.LineSegments(geometry, material);
            this.scene.add(this.neuralNetwork);

            // Store nodes for animation
            this.neuralNetwork.nodes = nodes;
        }
    }

    /**
     * Initialize GSAP Animations
     */
    initAnimations() {
        // Register ScrollTrigger
        gsap.registerPlugin(ScrollTrigger);

        // Hero Title Animation
        const titleChars = document.querySelector('.hero-title');
        if (titleChars) {
            gsap.from(titleChars, {
                duration: 1,
                opacity: 0,
                y: 30,
                ease: 'power2.out'
            });
        }

        // Section titles reveal on scroll
        gsap.utils.toArray('.section-title').forEach((element) => {
            gsap.from(element, {
                scrollTrigger: {
                    trigger: element,
                    start: 'top 80%'
                },
                duration: 0.8,
                opacity: 0,
                y: 30,
                ease: 'power2.out'
            });
        });

        // Project cards scroll animation
        gsap.utils.toArray('.project-card').forEach((card, index) => {
            gsap.from(card, {
                scrollTrigger: {
                    trigger: card,
                    start: 'top 85%'
                },
                duration: 0.8,
                opacity: 0,
                y: 40,
                ease: 'power2.out',
                delay: index * 0.1
            });
        });

        // Service cards
        gsap.utils.toArray('.service-card').forEach((card, index) => {
            gsap.from(card, {
                scrollTrigger: {
                    trigger: card,
                    start: 'top 85%'
                },
                duration: 0.8,
                opacity: 0,
                scale: 0.95,
                ease: 'back.out',
                delay: index * 0.1
            });
        });

        // Stats counter animation
        gsap.utils.toArray('[data-target]').forEach((element) => {
            gsap.from(element, {
                scrollTrigger: {
                    trigger: element,
                    start: 'top 80%'
                },
                duration: 2,
                innerText: 0,
                snap: { innerText: 1 },
                ease: 'power1.out',
                onUpdate: function () {
                    const target = parseInt(element.getAttribute('data-target'));
                    const current = parseInt(element.innerText);
                    if (current !== target) {
                        element.innerText = current;
                    }
                }
            });
        });

        // Timeline items
        gsap.utils.toArray('.timeline-item').forEach((item, index) => {
            gsap.from(item, {
                scrollTrigger: {
                    trigger: item,
                    start: 'top 85%'
                },
                duration: 0.6,
                opacity: 0,
                x: index % 2 === 0 ? -30 : 30,
                ease: 'power2.out'
            });
        });
    }

    /**
     * Setup Event Listeners
     */
    setupEventListeners() {
        // Window events
        window.addEventListener('resize', () => this.onWindowResize());
        window.addEventListener('mousemove', (e) => this.onMouseMove(e));
        window.addEventListener('scroll', () => this.onScroll());

        // Magnetic buttons
        this.setupMagneticButtons();

        // Interactive elements
        this.setupInteractiveElements();

        // Form handling
        this.setupFormHandling();

        // Case study modal
        this.setupCaseStudyModal();

        // Testimonials carousel
        this.setupTestimonialsCarousel();

        // Service card expansion
        this.setupServiceCards();
    }

    /**
     * Magnetic Button Effect
     */
    setupMagneticButtons() {
        const buttons = document.querySelectorAll('[data-magnetic]');

        buttons.forEach(button => {
            button.addEventListener('mousemove', (e) => {
                const rect = button.getBoundingClientRect();
                const x = e.clientX - rect.left - rect.width / 2;
                const y = e.clientY - rect.top - rect.height / 2;

                const distance = Math.sqrt(x * x + y * y);
                const maxDistance = 60;

                if (distance < maxDistance) {
                    const strength = 1 - distance / maxDistance;
                    const moveX = x * strength * 0.3;
                    const moveY = y * strength * 0.3;

                    button.style.transform = `translate(${moveX}px, ${moveY}px)`;
                }
            });

            button.addEventListener('mouseleave', () => {
                button.style.transform = 'translate(0, 0)';
            });
        });
    }

    /**
     * Interactive Elements Setup
     */
    setupInteractiveElements() {
        // Skill nodes interaction
        const skillNodes = document.querySelectorAll('.skill-node');

        skillNodes.forEach(node => {
            node.addEventListener('mouseenter', () => {
                node.style.transform = 'scale(1.2)';

                // Animate lines to center (pseudo-effect)
                gsap.to(node, {
                    duration: 0.3,
                    ease: 'back.out'
                });
            });

            node.addEventListener('mouseleave', () => {
                node.style.transform = 'scale(1)';
            });
        });

        // Parallax effect on elements
        const parallaxElements = document.querySelectorAll('[data-parallax]');
        window.addEventListener('scroll', () => {
            parallaxElements.forEach(el => {
                const scrollY = window.scrollY;
                const parallaxValue = el.getAttribute('data-parallax');
                el.style.transform = `translateY(${scrollY * parallaxValue}px)`;
            });
        });
    }

    /**
     * Form Handling
     */
    setupFormHandling() {
        const form = document.getElementById('contact-form');

        if (form) {
            form.addEventListener('submit', async (e) => {
                e.preventDefault();

                // Typing animation effect
                const submitBtn = form.querySelector('.btn-submit');
                const originalText = submitBtn.querySelector('.btn-text').innerText;

                submitBtn.disabled = true;
                submitBtn.querySelector('.btn-text').innerText = 'PROCESSING...';

                // Simulate processing
                await new Promise(resolve => setTimeout(resolve, 2000));

                submitBtn.querySelector('.btn-text').innerText = 'MESSAGE SENT ✓';

                // Reset after 3 seconds
                setTimeout(() => {
                    submitBtn.querySelector('.btn-text').innerText = originalText;
                    submitBtn.disabled = false;
                    form.reset();
                }, 3000);
            });
        }
    }

    /**
     * Case Study Modal
     */
    setupCaseStudyModal() {
        const modal = document.getElementById('case-study-modal');
        const closeBtn = document.querySelector('.case-study-close');
        const triggers = document.querySelectorAll('[data-case-study-trigger]');

        const caseStudies = {
            1: {
                title: 'Modern Business Website Concept',
                content: `
                    <h3>Goal</h3>
                    <p>Create a premium digital presence for a service brand that needed immediate clarity and stronger trust at first glance.</p>

                    <h3>Approach</h3>
                    <p>Designed a clean, conversion-focused layout with focused sections, modern typography, and strategic CTA placement to guide action naturally.</p>

                    <h3>Outcome</h3>
                    <ul>
                        <li>Sharper brand credibility within seconds</li>
                        <li>Better content hierarchy and user flow</li>
                        <li>Stronger lead-generation readiness</li>
                    </ul>
                `
            },
            2: {
                title: 'Premium SaaS Landing Experience',
                content: `
                    <h3>Goal</h3>
                    <p>Build a high-impact landing concept that communicates product value fast and feels premium across desktop and mobile.</p>

                    <h3>Approach</h3>
                    <p>Used startup-style visual rhythm, concise messaging, and trust-building content blocks designed to increase engagement and action.</p>

                    <h3>Outcome</h3>
                    <ul>
                        <li>Clearer positioning and value communication</li>
                        <li>Improved scroll depth and section interaction</li>
                        <li>Conversion-oriented structure for campaigns</li>
                    </ul>
                `
            },
            3: {
                title: 'Creative Portfolio UI Concept',
                content: `
                    <h3>Goal</h3>
                    <p>Present creative work with cinematic depth while keeping navigation simple, readable, and conversion-friendly.</p>

                    <h3>Approach</h3>
                    <p>Combined immersive visual layers with clean content blocks so the experience feels artistic without sacrificing usability.</p>

                    <h3>Outcome</h3>
                    <ul>
                        <li>Premium presentation of concept projects</li>
                        <li>Balanced style and clarity across sections</li>
                        <li>Stronger storytelling through modern UI</li>
                    </ul>
                `
            },
            4: {
                title: 'High-Conversion Service Page Demo',
                content: `
                    <h3>Goal</h3>
                    <p>Design a service page demo that helps visitors understand offerings quickly and take action with confidence.</p>

                    <h3>Approach</h3>
                    <p>Structured concise service messaging, high-contrast calls-to-action, and trust-focused sections for stronger conversion intent.</p>

                    <h3>Outcome</h3>
                    <ul>
                        <li>Clean, persuasive service communication</li>
                        <li>Improved inquiry-focused page flow</li>
                        <li>Ready template for real client deployment</li>
                    </ul>
                `
            },
            5: {
                title: 'E-Commerce Product Showcase Concept',
                content: `
                    <h3>Goal</h3>
                    <p>Design a polished e-commerce concept that simplifies buying decisions and improves checkout intent.</p>

                    <h3>Approach</h3>
                    <p>Built a clean product-first layout with strong category hierarchy, trust cues, and conversion-focused call-to-action flow.</p>

                    <h3>Outcome</h3>
                    <ul>
                        <li>Sharper product discovery experience</li>
                        <li>Cleaner decision path to purchase</li>
                        <li>Premium visual brand consistency</li>
                    </ul>
                `
            },
            6: {
                title: 'Analytics Dashboard UI Demo',
                content: `
                    <h3>Goal</h3>
                    <p>Present complex metrics in a way that allows teams to identify insights quickly and act with confidence.</p>

                    <h3>Approach</h3>
                    <p>Designed a structured dashboard system with visual prioritization, readable chart zones, and compact high-value summaries.</p>

                    <h3>Outcome</h3>
                    <ul>
                        <li>Better readability for key metrics</li>
                        <li>Fast scan and action-oriented UX</li>
                        <li>Scalable module-based layout</li>
                    </ul>
                `
            },
            7: {
                title: 'Mobile App Landing Concept',
                content: `
                    <h3>Goal</h3>
                    <p>Create an app launch page that communicates value instantly and improves install intent.</p>

                    <h3>Approach</h3>
                    <p>Used concise benefit-led copy, high-contrast CTA structure, and premium mobile-first design language.</p>

                    <h3>Outcome</h3>
                    <ul>
                        <li>Stronger first-impression messaging</li>
                        <li>Clearer feature communication flow</li>
                        <li>Higher campaign-ready conversion potential</li>
                    </ul>
                `
            },
            8: {
                title: 'Brand Identity Microsite Concept',
                content: `
                    <h3>Goal</h3>
                    <p>Build a focused microsite experience that presents brand personality and services with clarity.</p>

                    <h3>Approach</h3>
                    <p>Developed a compact storytelling layout with visual consistency, strategic content order, and premium interactions.</p>

                    <h3>Outcome</h3>
                    <ul>
                        <li>Cohesive digital brand presentation</li>
                        <li>Improved service understanding</li>
                        <li>Stronger trust and authority impression</li>
                    </ul>
                `
            }
        };

        triggers.forEach((trigger, index) => {
            trigger.addEventListener('click', () => {
                modal.classList.add('active');
                document.body.style.overflow = 'hidden';

                const caseStudy = caseStudies[index + 1] || caseStudies[1];
                document.getElementById('case-study-title').innerText = caseStudy.title;
                document.getElementById('case-study-body').innerHTML = caseStudy.content;
            });
        });

        closeBtn.addEventListener('click', () => {
            modal.classList.remove('active');
            document.body.style.overflow = 'auto';
        });

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
                document.body.style.overflow = 'auto';
            }
        });
    }

    /**
     * Testimonials Carousel
     */
    setupTestimonialsCarousel() {
        const cards = document.querySelectorAll('.testimonial-card');
        const prevBtn = document.querySelector('.carousel-btn.prev');
        const nextBtn = document.querySelector('.carousel-btn.next');

        if (!cards.length) {
            return;
        }

        let currentIndex = 0;

        const updateCarousel = () => {
            cards.forEach((card, index) => {
                card.classList.remove('active');
                if (index === currentIndex) {
                    card.classList.add('active');
                }
            });
        };

        prevBtn?.addEventListener('click', () => {
            currentIndex = (currentIndex - 1 + cards.length) % cards.length;
            updateCarousel();
        });

        nextBtn?.addEventListener('click', () => {
            currentIndex = (currentIndex + 1) % cards.length;
            updateCarousel();
        });

        // Auto-rotate
        setInterval(() => {
            currentIndex = (currentIndex + 1) % cards.length;
            updateCarousel();
        }, 5000);

        updateCarousel();
    }

    /**
     * Service Cards Hover Effect
     */
    setupServiceCards() {
        const cards = document.querySelectorAll('.service-card');

        cards.forEach(card => {
            card.addEventListener('mouseenter', () => {
                gsap.to(card, {
                    duration: 0.3,
                    y: -10,
                    ease: 'power2.out'
                });
            });

            card.addEventListener('mouseleave', () => {
                gsap.to(card, {
                    duration: 0.3,
                    y: 0,
                    ease: 'power2.out'
                });
            });
        });
    }

    /**
     * Mouse Move - Custom Cursor & 3D Interaction
     */
    onMouseMove(e) {
        this.mouseX = e.clientX;
        this.mouseY = e.clientY;

        // Update custom cursor
        gsap.to(this.cursorElement, {
            duration: 0.1,
            left: e.clientX,
            top: e.clientY,
            ease: 'power1.out'
        });

        gsap.to(this.cursorGlow, {
            duration: 0.2,
            left: e.clientX,
            top: e.clientY,
            ease: 'power1.out'
        });

        // Update camera based on mouse position
        const centerX = window.innerWidth / 2;
        const centerY = window.innerHeight / 2;
        const rotationX = (e.clientY - centerY) * 0.0005;
        const rotationY = (e.clientX - centerX) * 0.0005;

        gsap.to(this.camera.rotation, {
            duration: 0.5,
            x: rotationX,
            y: rotationY,
            ease: 'power1.out'
        });
    }

    /**
     * Scroll Handling
     */
    onScroll() {
        const scrollHeight = document.documentElement.scrollHeight - window.innerHeight;
        this.scrollProgress = window.scrollY / scrollHeight;

        // Rotate particles
        if (this.particles) {
            this.particles.rotation.x += 0.0001;
            this.particles.rotation.y += 0.0002;
        }
    }

    /**
     * Window Resize Handler
     */
    onWindowResize() {
        const width = window.innerWidth;
        const height = window.innerHeight;

        this.camera.aspect = width / height;
        this.camera.updateProjectionMatrix();

        this.renderer.setSize(width, height);
    }

    /**
     * Animation Loop
     */
    animate() {
        this.animationFrameId = requestAnimationFrame(() => this.animate());

        // Update particle field
        if (this.particles) {
            this.particles.rotation.x += 0.0001;
            this.particles.rotation.y += 0.0003;

            // Particle interaction with mouse
            const positions = this.particles.geometry.attributes.position.array;
            for (let i = 0; i < positions.length; i += 3) {
                const x = positions[i];
                const y = positions[i + 1];

                const dx = this.mouseX - window.innerWidth / 2;
                const dy = this.mouseY - window.innerHeight / 2;

                const distance = Math.sqrt(dx * dx + dy * dy);
                if (distance < 200) {
                    positions[i] += (dx / distance) * 0.1;
                    positions[i + 1] += (dy / distance) * 0.1;
                }
            }
            this.particles.geometry.attributes.position.needsUpdate = true;
        }

        // Update neural network
        if (this.neuralNetwork && this.neuralNetwork.nodes) {
            this.neuralNetwork.nodes.forEach(node => {
                node.x += node.vx;
                node.y += node.vy;
                node.z += node.vz;

                // Bounce off boundaries
                if (Math.abs(node.x) > 50) node.vx *= -1;
                if (Math.abs(node.y) > 50) node.vy *= -1;
                if (Math.abs(node.z) > 50) node.vz *= -1;
            });
        }

        // Render scene
        this.renderer.render(this.scene, this.camera);
    }

    /**
     * Hide Loading Screen
     */
    hideLoadingScreen() {
        setTimeout(() => {
            const loadingScreen = document.querySelector('.loading-screen');
            if (loadingScreen) {
                gsap.to(loadingScreen, {
                    duration: 0.8,
                    opacity: 0,
                    pointerEvents: 'none'
                });
            }
        }, 2000);
    }
}

// ============================================
// ENHANCED SCROLL ANIMATIONS
// ============================================

function initScrollAnimations() {
    // Smooth scroll for navigation links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const href = this.getAttribute('href');
            if (href !== '#') {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'nearest'
                    });
                }
            }
        });
    });

    // Parallax layer animations
    gsap.registerPlugin(ScrollTrigger);

    gsap.utils.toArray('.about-hologram').forEach((element) => {
        gsap.from(element, {
            scrollTrigger: {
                trigger: element,
                start: 'top 80%'
            },
            duration: 1,
            opacity: 0,
            x: -50,
            ease: 'power2.out'
        });
    });

    gsap.utils.toArray('.about-content').forEach((element) => {
        gsap.from(element, {
            scrollTrigger: {
                trigger: element,
                start: 'top 80%'
            },
            duration: 1,
            opacity: 0,
            x: 50,
            delay: 0.2,
            ease: 'power2.out'
        });
    });
}

// ============================================
// AUDIO FEEDBACK SYSTEM
// ============================================

class AudioFeedback {
    constructor() {
        this.audioContext = null;
        this.isEnabled = true;
    }

    init() {
        // Create Web Audio API context
        const audioContextClass = window.AudioContext || window.webkitAudioContext;
        if (audioContextClass) {
            this.audioContext = new audioContextClass();
        }
    }

    playClickSound() {
        if (!this.audioContext || !this.isEnabled) return;

        const now = this.audioContext.currentTime;
        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();

        oscillator.connect(gainNode);
        gainNode.connect(this.audioContext.destination);

        oscillator.frequency.setValueAtTime(800, now);
        oscillator.frequency.exponentialRampToValueAtTime(100, now + 0.1);

        gainNode.gain.setValueAtTime(0.1, now);
        gainNode.gain.exponentialRampToValueAtTime(0.01, now + 0.1);

        oscillator.start(now);
        oscillator.stop(now + 0.1);
    }

    playSuccessSound() {
        if (!this.audioContext || !this.isEnabled) return;

        const now = this.audioContext.currentTime;
        const frequencies = [523.25, 659.25, 783.99]; // C, E, G notes

        frequencies.forEach((freq, index) => {
            const oscillator = this.audioContext.createOscillator();
            const gainNode = this.audioContext.createGain();

            oscillator.connect(gainNode);
            gainNode.connect(this.audioContext.destination);

            oscillator.frequency.setValueAtTime(freq, now);
            gainNode.gain.setValueAtTime(0.1, now + index * 0.05);
            gainNode.gain.exponentialRampToValueAtTime(0.01, now + index * 0.05 + 0.2);

            oscillator.start(now + index * 0.05);
            oscillator.stop(now + index * 0.05 + 0.2);
        });
    }
}

// ============================================
// PERFORMANCE MONITORING
// ============================================

class PerformanceMonitor {
    constructor() {
        this.fps = 60;
        this.frameCount = 0;
        this.lastTime = Date.now();
    }

    update() {
        this.frameCount++;
        const currentTime = Date.now();

        if (currentTime - this.lastTime >= 1000) {
            this.fps = this.frameCount;
            this.frameCount = 0;
            this.lastTime = currentTime;

            // Adjust quality based on performance
            if (this.fps < 30) {
                document.body.classList.add('low-performance');
            } else {
                document.body.classList.remove('low-performance');
            }
        }
    }
}

// ============================================
// INITIALIZATION
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Initialize portfolio
    const portfolio = new CinematicPortfolio();

    // Initialize scroll animations
    initScrollAnimations();

    // Initialize audio feedback
    const audioFeedback = new AudioFeedback();
    audioFeedback.init();

    // Add event listeners for audio
    document.querySelectorAll('.btn').forEach(btn => {
        btn.addEventListener('click', () => audioFeedback.playClickSound());
    });

    document.getElementById('contact-form')?.addEventListener('submit', () => {
        audioFeedback.playSuccessSound();
    });

    // Initialize performance monitor
    const perfMonitor = new PerformanceMonitor();
    setInterval(() => perfMonitor.update(), 100);

    // Easter egg 🎮
    let easterEggCode = '';
    const easterEggSequence = 'UNITARYX';

    document.addEventListener('keydown', (e) => {
        easterEggCode += e.key.toUpperCase();
        easterEggCode = easterEggCode.slice(-easterEggSequence.length);

        if (easterEggCode === easterEggSequence) {
            activateEasterEgg();
            easterEggCode = '';
        }
    });

    function activateEasterEgg() {
        // Create matrix effect
        const matrix = document.createElement('div');
        matrix.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 200, 100, 0.1);
            z-index: 5000;
            pointer-events: none;
            animation: matrixFlicker 0.2s;
        `;
        document.body.appendChild(matrix);

        gsap.to(matrix, {
            duration: 0.2,
            opacity: 0,
            onComplete: () => matrix.remove()
        });

        // Play sound
        audioFeedback.playSuccessSound();
    }
});

// ============================================
// CSS FOR EASTER EGG
// ============================================

const style = document.createElement('style');
style.textContent = `
    @keyframes matrixFlicker {
        0%, 100% { opacity: 0; }
        50% { opacity: 1; }
    }
    
    body.low-performance .geometric-shape {
        animation: none;
    }
`;
document.head.appendChild(style);

// ============================================
// EXPORT FOR TESTING
// ============================================

window.CinematicPortfolio = CinematicPortfolio;
window.AudioFeedback = AudioFeedback;
