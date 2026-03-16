/**
 * Global Translation Engine - Unitary X
 * Hybrid Approach: Native Map + Google Translate Fallback
 */

const UNITARY_X_LOCALE_MAP = {
    'hi': {
        'Web Development': 'वेब विकास',
        'Software Projects': 'सॉफ्टवेयर प्रोजेक्ट्स',
        'Hardware & IoT': 'हार्डवेयर और आईओटी',
        'Mobile Apps': 'मोबाइल ऐप्स',
        'AI & Machine Learning': 'एआई और मशीन लर्निंग',
        'Reports & Documentation': 'रिपोर्ट और दस्तावेज़ीकरण',
        'Get Quote': 'कोटेशन प्राप्त करें',
        'Back to Site': 'साइट पर वापस जाएं',
        'Dashboard': 'डैशबोर्ड',
        'Logout': 'लॉगआउट',
        'Services': 'सेवाएं',
        'Contact': 'संपर्क करें',
        'Admin Command Center': 'एडमिन कमांड सेंटर',
        'Operational': 'परिचालन',
        'Welcome': 'स्वागत है'
    },
    'es': {
        'Web Development': 'Desarrollo Web',
        'Software Projects': 'Proyectos de Software',
        'Hardware & IoT': 'Hardware e IoT',
        'Mobile Apps': 'Apps Móviles',
        'AI & Machine Learning': 'IA y ML',
        'Get Quote': 'Obtener Cotización',
        'Back to Site': 'Volver al Sitio'
    },
    'fr': {
        'Web Development': 'Développement Web',
        'Software Projects': 'Projets Logiciels',
        'Hardware & IoT': 'Matériel et IoT',
        'Get Quote': 'Obtenir un devis',
        'Back to Site': 'Retour au site'
    },
    'de': {
        'Web Development': 'Webentwicklung',
        'Software Projects': 'Softwareprojekte',
        'Hardware & IoT': 'Hardware & IoT',
        'Get Quote': 'Angebot anfordern',
        'Back to Site': 'Zurück zur Seite'
    }
};

function applyNativeTranslations(lang) {
    if (!lang || lang === 'en' || !UNITARY_X_LOCALE_MAP[lang]) return;
    const map = UNITARY_X_LOCALE_MAP[lang];
    
    // Recursive walker to find and replace text nodes
    const walk = (node) => {
        if (node.nodeType === 3) { // Text node
            const text = node.nodeValue.trim();
            if (map[text]) {
                node.nodeValue = node.nodeValue.replace(text, map[text]);
            }
        } else if (node.nodeType === 1 && node.tagName !== 'SCRIPT' && node.tagName !== 'STYLE') {
            node.childNodes.forEach(walk);
        }
    };
    walk(document.body);
    
    // Also handle specific attributes like titles or placeholders
    document.querySelectorAll('[placeholder]').forEach(el => {
        if (map[el.placeholder]) el.placeholder = map[el.placeholder];
    });
}

function googleTranslateElementInit() {
    new google.translate.TranslateElement({
        pageLanguage: 'en',
        includedLanguages: 'en,fr,es,de,it,pl,hi,ja,zh-CN,ar,th,ko',
        autoDisplay: false
    }, 'google_translate_element');
}

(function() {
    'use strict';

    // 1. Inject Google Translate Library
    const gtScript = document.createElement('script');
    gtScript.type = 'text/javascript';
    gtScript.async = true;
    gtScript.src = 'https://translate.google.com/translate_a/element.js?cb=googleTranslateElementInit';
    document.head.appendChild(gtScript);

    // 2. Inject Hidden Translate Element
    const gtEl = document.createElement('div');
    gtEl.id = 'google_translate_element';
    gtEl.style.display = 'none';
    document.body.appendChild(gtEl);

    // 3. Inject Language Modal HTML if not already there
    const modalHTML = `
    <div class="lang-modal-overlay" id="lang-modal">
        <div class="lang-modal-box">
            <div class="lang-modal-header">
                <h2>Choose Your Country or Region</h2>
                <button class="lang-close" id="lang-close"><i class="fas fa-times"></i></button>
            </div>
            <div class="lang-modal-content">
                <div class="region-group">
                    <h3>Americas / International</h3>
                    <div class="country-grid">
                        <a href="#" class="lang-select" data-lang="en"><i class="flag-icon">🇺🇸</i> English (US)</a>
                        <a href="#" class="lang-select" data-lang="fr"><i class="flag-icon">🇨🇦</i> French (CA)</a>
                        <a href="#" class="lang-select" data-lang="es"><i class="flag-icon">🇲🇽</i> Spanish (MX)</a>
                    </div>
                </div>
                <div class="region-group">
                    <h3>Europe</h3>
                    <div class="country-grid">
                        <a href="#" class="lang-select" data-lang="en"><i class="flag-icon">🇬🇧</i> English (UK)</a>
                        <a href="#" class="lang-select" data-lang="fr"><i class="flag-icon">🇫🇷</i> French</a>
                        <a href="#" class="lang-select" data-lang="de"><i class="flag-icon">🇩🇪</i> German</a>
                        <a href="#" class="lang-select" data-lang="it"><i class="flag-icon">🇮🇹</i> Italian</a>
                        <a href="#" class="lang-select" data-lang="es"><i class="flag-icon">🇪🇸</i> Spanish</a>
                        <a href="#" class="lang-select" data-lang="pl"><i class="flag-icon">🇵🇱</i> Polish</a>
                    </div>
                </div>
                <div class="region-group">
                    <h3>Asia Pacific & Middle East</h3>
                    <div class="country-grid">
                        <a href="#" class="lang-select" data-lang="hi"><i class="flag-icon">🇮🇳</i> Hindi (India)</a>
                        <a href="#" class="lang-select" data-lang="ja"><i class="flag-icon">🇯🇵</i> Japanese</a>
                        <a href="#" class="lang-select" data-lang="zh-CN"><i class="flag-icon">🇨🇳</i> Chinese</a>
                        <a href="#" class="lang-select" data-lang="ar"><i class="flag-icon">🇦🇪</i> Arabic</a>
                        <a href="#" class="lang-select" data-lang="th"><i class="flag-icon">🇹🇭</i> Thai</a>
                        <a href="#" class="lang-select" data-lang="ko"><i class="flag-icon">🇰🇷</i> Korean</a>
                    </div>
                </div>
            </div>
        </div>
    </div>`;

    if (!document.getElementById('lang-modal')) {
        document.body.insertAdjacentHTML('beforeend', modalHTML);
    }

    // 4. Shared Logic
    document.addEventListener('DOMContentLoaded', () => {
        const savedLang = localStorage.getItem('unitaryx_lang');
        
        // Immediate native translation for key elements
        if (savedLang && savedLang !== 'en') {
            applyNativeTranslations(savedLang);
        }

        console.log('Unitary X Translation Engine: Initializing...');
        
        const setTransCookie = (lang) => {
            const cookieValue = `/en/${lang}`;
            const domain = window.location.hostname;
            
            // Set for current path
            document.cookie = `googtrans=${cookieValue}; path=/; SameSite=Lax`;
            
            // Set for domain (only if not an IP address like 127.0.0.1)
            if (!/^[0-9.]+$/.test(domain) && domain !== 'localhost') {
                document.cookie = `googtrans=${cookieValue}; path=/; domain=.${domain}; SameSite=Lax`;
            }
            
            console.log(`Unitary X Translation Engine: Cookie set to ${cookieValue} for domain ${domain}`);
        };

        // Apply saved language from localStorage if cookie is missing or wrong
        const match = document.cookie.match(/googtrans=([^;]+)/);
        const currentCookie = match ? match[1] : null;
        
        if (savedLang && savedLang !== 'en') {
            const expectedCookie = `/en/${savedLang}`;
            if (currentCookie !== expectedCookie) {
                setTransCookie(savedLang);
                window.location.reload();
                return;
            }
        }

        const triggers = document.querySelectorAll('#lang-trigger, .lang-trigger');
        const modal = document.getElementById('lang-modal');
        const closeBtn = document.getElementById('lang-close');

        if (modal) {
            triggers.forEach(t => {
                t.addEventListener('click', (e) => {
                    e.preventDefault();
                    modal.classList.add('active');
                });
            });

            closeBtn.addEventListener('click', () => modal.classList.remove('active'));
            modal.addEventListener('click', (e) => {
                if (e.target === modal) modal.classList.remove('active');
            });

            const langLinks = modal.querySelectorAll('.lang-select');
            langLinks.forEach(link => {
                link.addEventListener('click', function(e) {
                    e.preventDefault();
                    const lang = this.getAttribute('data-lang');
                    console.log(`Unitary X Translation Engine: Selection - ${lang}`);
                    
                    if (lang === 'en') {
                        localStorage.removeItem('unitaryx_lang');
                        document.cookie = 'googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
                        const domain = window.location.hostname;
                        if (!/^[0-9.]+$/.test(domain) && domain !== 'localhost') {
                            document.cookie = 'googtrans=; expires=Thu, 01 Jan 1970 00:00:00 UTC; domain=.' + domain + '; path=/;';
                        }
                        window.location.reload();
                        return;
                    }

                    // Save to local storage
                    localStorage.setItem('unitaryx_lang', lang);
                    
                    // Set cookie
                    setTransCookie(lang);
                    
                    // Force reload
                    window.location.reload();
                });
            });
        }
    });
})();
