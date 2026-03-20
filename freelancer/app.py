"""
Unitary X - Premium Tech Freelancer Website
Flask Backend with Authentication System
"""

from flask import (Flask, render_template, request, jsonify, make_response,
                   redirect, url_for, flash, session)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import os, re, urllib.parse, random, smtplib, ssl, csv
from io import StringIO
from email.message import EmailMessage
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# Security & Config
from flask_talisman import Talisman
# from flask_seasurf import SeaSurf # Incompatible with Flask 3.x, CSRF is handled by DummyCSRF below
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"), override=True)

APP_DIR = os.path.abspath(os.path.dirname(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(APP_DIR, "templates"),
    static_folder=os.path.join(APP_DIR, "static"),
)
app.secret_key = os.getenv("SECRET_KEY", "fallback_weak_key_for_dev_only")
PASSWORD_HASH_METHOD = (os.getenv("PASSWORD_HASH_METHOD") or "pbkdf2:sha256:260000").strip()

_default_google_client_id = "1062977400292-gnrhgek38h1jiu30v91r5vkq73avr6ut.apps.googleusercontent.com"
_env_google_client_id = (os.getenv("GOOGLE_CLIENT_ID") or "").strip()
if not _env_google_client_id or "your_google_client_id_here" in _env_google_client_id:
    app.config['GOOGLE_CLIENT_ID'] = _default_google_client_id
else:
    app.config['GOOGLE_CLIENT_ID'] = _env_google_client_id

DEFAULT_GOOGLE_ALLOWED_ORIGINS = {
    "http://localhost:5005",
    "http://127.0.0.1:5005",
}

OAUTH_ADMIN_EMAILS = {
    "harikavi1301@gmail.com",
    "darshankannan2008@gmail.com",
}

SUPERADMIN_EMAIL = "harikavi1301@gmail.com"
SUPERADMIN_PASSWORD = "hari@123"


def normalize_email(value):
    return (value or "").strip().lower()


def normalize_role(value):
    role = (value or "user").strip().lower()
    return role if role in {"user", "admin"} else "user"


def find_user_by_email(email):
    normalized = normalize_email(email)
    if not normalized:
        return None
    return User.query.filter(db.func.lower(User.email) == normalized).first()


def oauth_admin_emails():
    emails = {normalize_email(e) for e in OAUTH_ADMIN_EMAILS if normalize_email(e)}
    configured_admin = normalize_email(os.getenv("ADMIN_EMAIL", "admin@unitaryx.com"))
    if configured_admin:
        emails.add(configured_admin)
    emails.add(normalize_email(SUPERADMIN_EMAIL))
    return emails


def is_admin_identity(email, existing_user=None):
    normalized = normalize_email(email)
    if normalized == normalize_email(SUPERADMIN_EMAIL):
        return True
    if existing_user and normalize_role(existing_user.role) == "admin":
        return True
    return normalized in oauth_admin_emails()


def establish_session_for_user(user, remember=False):
    user_email = normalize_email(user.email)
    role = normalize_role(user.role)
    if user_email == normalize_email(SUPERADMIN_EMAIL):
        role = "admin"
    session.permanent = bool(remember)
    session['user_id'] = user.id
    session['user_name'] = user.name
    session['user_email'] = user_email
    session['role'] = role
    session['is_superadmin'] = user_email == normalize_email(SUPERADMIN_EMAIL)

# ─── Security Configuration ──────────────────────────────────────────────────

# 1. CSRF Protection (PERMANENTLY DISABLED via Mock)
class DummyCSRF:
    def __init__(self, app=None):
        if app is not None:
            self.init_app(app)
    def init_app(self, app):
        @app.context_processor
        def inject_csrf():
            return dict(csrf_token=lambda: "dummy_token")
    def exempt(self, view):
        return view

csrf = DummyCSRF(app)

# 2. Secure Headers (Talisman)
# Force HTTPS only in production, but here we keep it flexible
csp = {
    'default-src': [
        '\'self\'',
        'https://cdnjs.cloudflare.com',
        'https://fonts.googleapis.com',
        'https://fonts.gstatic.com',
        'https://use.fontawesome.com',
        'https://cdn.jsdelivr.net',
    ],
    'img-src': ['\'self\'', 'data:', '*', 'https://www.google.com', 'https://translate.googleapis.com'],
    'media-src': ['\'self\'', 'https://cdn.pixabay.com', 'data:', '*'],
    'script-src': [
        '\'self\'',
        '\'unsafe-inline\'',
        '\'unsafe-eval\'',
        'https://cdnjs.cloudflare.com',
        'https://cdn.jsdelivr.net',
        'https://translate.google.com',
        'https://translate.googleapis.com',
        'https://accounts.google.com'
    ],
    'style-src': [
        '\'self\'',
        '\'unsafe-inline\'',
        'https://cdnjs.cloudflare.com',
        'https://fonts.googleapis.com',
        'https://use.fontawesome.com',
        'https://cdn.jsdelivr.net',
        'https://translate.googleapis.com'
    ],
    'connect-src': [
        '\'self\'',
        'https://translate.googleapis.com',
        'https://accounts.google.com',
        'https://oauth2.googleapis.com',
        'https://www.googleapis.com'
    ],
    'frame-src': [
        '\'self\'',
        'https://translate.google.com',
        'https://accounts.google.com'
    ],
}

talisman = Talisman(
    app,
    content_security_policy=csp,
    force_https=False, # Set to True in production with SSL
    session_cookie_secure=False, # Set to True in production with SSL
    session_cookie_http_only=True,
    session_cookie_samesite='Lax',
    strict_transport_security=True,
    strict_transport_security_max_age=31536000,
    frame_options='DENY', # Blocks clickjacking attacks
    x_xss_protection=True
)

# 3. Rate Limiting (Relaxed for Development)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["10000 per day", "2000 per hour"],
    storage_uri="memory://"
)


@app.after_request
def add_no_cache_headers(response):
    # Prevent stale cached auth pages from serving outdated reset-password JS.
    if response.mimetype == "text/html" or request.path in {"/login", "/send-otp", "/verify-otp", "/reset-password"}:
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# ─── Database ─────────────────────────────────────────────────────────────────
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'unitaryx_v2.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    "connect_args": {"timeout": 5}
}
db = SQLAlchemy(app)


# ─── Models ───────────────────────────────────────────────────────────────────

class User(db.Model):
    """Registered users (students)"""
    __tablename__ = 'users'

    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(100), nullable=False)
    email        = db.Column(db.String(150), unique=True, nullable=False)
    password     = db.Column(db.String(200), nullable=False)
    role         = db.Column(db.String(20), default='user')   # 'user' | 'admin'
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    is_active    = db.Column(db.Boolean, default=True)

    def set_password(self, raw):
        self.password = generate_password_hash(raw, method=PASSWORD_HASH_METHOD)

    def check_password(self, raw):
        return check_password_hash(self.password, raw)


class PasswordResetOTP(db.Model):
    """Stores OTP codes for password reset flow."""
    __tablename__ = 'password_reset_otps'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), nullable=False, index=True)
    otp = db.Column(db.String(6), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    attempts_left = db.Column(db.Integer, nullable=False, default=5)
    is_verified = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class AdminTask(db.Model):
    """Tasks assigned by superadmin to specific admin emails."""
    __tablename__ = 'admin_tasks'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(160), nullable=False)
    details = db.Column(db.Text)
    assigned_to_email = db.Column(db.String(150), nullable=False, index=True)
    assigned_by_email = db.Column(db.String(150), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class AdminAuditLog(db.Model):
    """Tracks sensitive superadmin actions for accountability."""
    __tablename__ = 'admin_audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    actor_email = db.Column(db.String(150), nullable=False, index=True)
    action = db.Column(db.String(80), nullable=False)
    target = db.Column(db.String(180))
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


class ProjectRequest(db.Model):
    """Project enquiries from students"""
    __tablename__ = 'project_requests'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    name       = db.Column(db.String(100), nullable=False)
    email      = db.Column(db.String(150), nullable=False)
    phone      = db.Column(db.String(20))
    service    = db.Column(db.String(80), nullable=False)
    deadline   = db.Column(db.String(30))
    message    = db.Column(db.Text, nullable=False)
    status     = db.Column(db.String(30), default='New')
    is_new_update = db.Column(db.Boolean, default=False)
    priority   = db.Column(db.String(20), default='Medium')
    value      = db.Column(db.Integer, default=0)
    internal_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user       = db.relationship('User', backref='requests', lazy=True)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "email": self.email,
            "phone": self.phone, "service": self.service,
            "deadline": self.deadline, "message": self.message,
            "status": self.status,
            "created_at": self.created_at.strftime("%d %b %Y, %I:%M %p"),
        }


class Project(db.Model):
    """Portfolio projects shown on the website"""
    __tablename__ = 'projects'

    id          = db.Column(db.Integer, primary_key=True)
    title       = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    category    = db.Column(db.String(50), nullable=False)
    tags        = db.Column(db.String(200))
    price       = db.Column(db.String(30))
    duration    = db.Column(db.String(30))
    rating      = db.Column(db.Float, default=5.0)
    icon        = db.Column(db.String(80))
    bg_class    = db.Column(db.String(30))
    featured    = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id, "title": self.title,
            "description": self.description, "category": self.category,
            "tags": self.tags.split(",") if self.tags else [],
            "price": self.price, "duration": self.duration,
            "rating": self.rating, "icon": self.icon,
            "bg_class": self.bg_class, "featured": self.featured,
        }


class Testimonial(db.Model):
    """Student testimonials"""
    __tablename__ = 'testimonials'

    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(100), nullable=False)
    role     = db.Column(db.String(150))
    review   = db.Column(db.Text, nullable=False)
    rating   = db.Column(db.Integer, default=5)
    avatar   = db.Column(db.String(10))
    av_class = db.Column(db.String(20))
    active   = db.Column(db.Boolean, default=True)


# ─── Template Filters ─────────────────────────────────────────────────────────

@app.template_filter('format_id')
def format_id_filter(id_val):
    """Formats ID as 4-digit strings like 0001"""
    return f"{id_val:04d}"


# ─── Auth Decorators ──────────────────────────────────────────────────────────

def login_required(f):
    """Ensures user is logged in (any role)."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    """Ensures user is logged in as admin. (Relaxed for Dev)"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in as Admin.', 'warning')
            return redirect(url_for('login', tab='admin'))
        if session.get('role') != 'admin':
            flash('Admin access only.', 'danger')
            return redirect(url_for('user_dashboard'))
        return f(*args, **kwargs)
    return decorated


# ─── Helpers ──────────────────────────────────────────────────────────────────

def validate_email(email):
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', email))


def _normalize_origin(origin):
    return (origin or "").strip().rstrip("/")


def get_google_origin_settings(current_origin):
    raw = (os.getenv("GOOGLE_ALLOWED_ORIGINS") or "").strip()
    configured = {
        _normalize_origin(x) for x in raw.split(",") if _normalize_origin(x)
    }
    allowed_origins = configured if configured else DEFAULT_GOOGLE_ALLOWED_ORIGINS
    normalized_current = _normalize_origin(current_origin)
    enabled = normalized_current in allowed_origins
    return {
        "enabled": enabled,
        "current_origin": normalized_current,
        "allowed_origins": sorted(allowed_origins),
    }


def current_user():
    uid = session.get('user_id')
    return db.session.get(User, uid) if uid else None


def is_super_admin(user_obj=None):
    user_obj = user_obj or current_user()
    if not user_obj:
        return False
    return normalize_email(user_obj.email) == normalize_email(SUPERADMIN_EMAIL)


def log_superadmin_action(action, target="", details="", actor=None):
    actor = actor or current_user()
    if not actor or not is_super_admin(actor):
        return
    db.session.add(AdminAuditLog(
        actor_email=(actor.email or "").strip().lower(),
        action=(action or "").strip()[:80],
        target=(target or "").strip()[:180],
        details=(details or "").strip()[:2000],
    ))


OTP_TTL_MINUTES = 10
OTP_MAX_ATTEMPTS = 5


def _safe_commit():
    try:
        db.session.commit()
        return True
    except Exception:
        db.session.rollback()
        app.logger.exception("Database commit failed in OTP flow")
        return False


def _cleanup_expired_otps():
    now = datetime.utcnow()
    PasswordResetOTP.query.filter(PasswordResetOTP.expires_at <= now).delete(synchronize_session=False)
    _safe_commit()


def _generate_otp_code():
    return f"{random.randint(0, 999999):06d}"


def _save_otp_for_email(email, otp_code):
    PasswordResetOTP.query.filter_by(email=email).delete(synchronize_session=False)
    row = PasswordResetOTP(
        email=email,
        otp=otp_code,
        expires_at=datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES),
        attempts_left=OTP_MAX_ATTEMPTS,
        is_verified=False,
    )
    db.session.add(row)
    _safe_commit()


def _get_active_otp(email):
    now = datetime.utcnow()
    return PasswordResetOTP.query.filter(
        PasswordResetOTP.email == email,
        PasswordResetOTP.expires_at > now,
    ).order_by(PasswordResetOTP.created_at.desc()).first()


def _send_password_reset_otp(email, otp_code):
    smtp_host = (os.getenv("SMTP_HOST") or "smtp.gmail.com").strip()
    smtp_port = int((os.getenv("SMTP_PORT") or "587").strip())
    smtp_user = (os.getenv("SMTP_USER") or "").strip()
    smtp_pass = (os.getenv("SMTP_PASS") or "").strip()
    smtp_from = (os.getenv("SMTP_FROM") or smtp_user).strip()
    smtp_use_tls = (os.getenv("SMTP_USE_TLS") or "true").strip().lower() in {"1", "true", "yes", "on"}

    if not smtp_user or not smtp_pass:
        raise RuntimeError("SMTP_USER/SMTP_PASS are not configured")

    msg = EmailMessage()
    msg["Subject"] = "Unitary X Password Reset OTP"
    msg["From"] = smtp_from
    msg["To"] = email
    msg.set_content(
        "Your One-Time Password (OTP) for password reset is: "
        f"{otp_code}\n\n"
        f"This OTP expires in {OTP_TTL_MINUTES} minutes.\n"
        "If you did not request this, please ignore this email."
    )

    if smtp_use_tls:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
    else:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15, context=ssl.create_default_context()) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)


# ─── Seed Data ────────────────────────────────────────────────────────────────

def seed_data():
    # Default admin from .env
    admin_email = os.getenv("ADMIN_EMAIL", "admin@unitaryx.com")
    admin_pass = os.getenv("ADMIN_PASS", "Admin@123")
    
    if not User.query.filter_by(email=admin_email).first():
        admin = User(name='Unitary X Admin',
                     email=admin_email, role='admin')
        admin.set_password(admin_pass)
        db.session.add(admin)

    # Ensure superadmin credentials are always available for the fixed email.
    super_admin = User.query.filter(db.func.lower(User.email) == SUPERADMIN_EMAIL).first()
    if not super_admin:
        super_admin = User(name='Super Admin', email=SUPERADMIN_EMAIL, role='admin')
        db.session.add(super_admin)
    super_admin.role = 'admin'
    super_admin.is_active = True
    super_admin.set_password(SUPERADMIN_PASSWORD)

    if Project.query.count() == 0:
        db.session.add_all([
            Project(title="E-Commerce Platform",
                    description="Full-stack shopping platform with product management, cart, payment & admin panel built with Flask and MySQL.",
                    category="web", tags="Web,Flask,MySQL", price="Rs.1,500",
                    duration="7 days", rating=5.0, icon="fas fa-shopping-cart",
                    bg_class="bg-1", featured=True),
            Project(title="Face Recognition System",
                    description="Real-time face detection and recognition attendance system using OpenCV and deep learning.",
                    category="ai", tags="AI,Python,OpenCV", price="Rs.2,200",
                    duration="10 days", rating=5.0, icon="fas fa-eye",
                    bg_class="bg-2", featured=True),
            Project(title="Smart Home Automation",
                    description="Arduino + ESP8266 WiFi-controlled home automation system with mobile app interface.",
                    category="hardware", tags="Hardware,IoT,Arduino", price="Rs.3,500",
                    duration="14 days", rating=4.9, icon="fas fa-home",
                    bg_class="bg-3", featured=True),


            Project(title="Line Follower Robot",
                    description="Autonomous line-following robot with IR sensors and Bluetooth remote override.",
                    category="hardware", tags="Hardware,Arduino,Robotics", price="Rs.1,800",
                    duration="8 days", rating=4.8, icon="fas fa-robot", bg_class="bg-6"),
            Project(title="AI Water Management System",
                    description="Smart IoT-based water monitoring and leak detection system using AI algorithms for predictive maintenance.",
                    category="ai", tags="AI,IoT,Water Management", price="Rs.2,100",
                    duration="10 days", rating=5.0, icon="fas fa-tint", bg_class="bg-7", featured=True),
            Project(title="Vision X - Smart Cap",
                    description="Custom-built wearable hardware with integrated camera and haptic feedback sensors for obstacle detection.",
                    category="hardware", tags="Hardware,IoT,Arduino", price="Rs.2,900",
                    duration="14 days", rating=5.0, icon="fas fa-low-vision", bg_class="bg-3", featured=True),
            Project(title="Smart Classroom Management System",
                    description="Integrated software and hardware platform for automated attendance, smart lighting, and classroom resource management.",
                    category="hardware", tags="Hardware,Software,IoT,Classroom", price="Rs.2,500",
                    duration="12 days", rating=4.9, icon="fas fa-chalkboard-teacher", bg_class="bg-8", featured=True),
        ])

    if Testimonial.query.count() == 0:
        db.session.add_all([
            Testimonial(name="Rahul Kumar", role="B.Tech CSE, Anna University",
                        review="Got my final year project (face recognition attendance system) done in just 10 days! The code was clean, well-commented, and I even got a PPT. Scored distinction!",
                        rating=5, avatar="R", av_class="av-1"),
            Testimonial(name="Priya Sharma", role="Diploma in ECE, PSG Polytechnic",
                        review="My Arduino smart home project was built with actual working hardware and proper circuit diagrams. The instructor was super impressed!",
                        rating=5, avatar="P", av_class="av-2"),
            Testimonial(name="Arun Venkatesan", role="MCA Student, Bharathiar University",
                        review="I was struggling with my DBMS mini-project. Got it done in 3 days with MySQL, Python, and a great UI. Total lifesaver for my exams!",
                        rating=5, avatar="A", av_class="av-3"),
            Testimonial(name="Sneha Rajan", role="12th Standard, KV School Chennai",
                        review="School science expo winning project! The line-follower robot was amazing — real working model, poster, and everything!",
                        rating=5, avatar="S", av_class="av-4"),
        ])

    db.session.commit()


# ─── Public Routes ────────────────────────────────────────────────────────────

@app.route("/")
def index():
    projects     = Project.query.all()
    testimonials = Testimonial.query.filter_by(active=True).all()
    stats = {
        "projects_done":  Project.query.count() + 194,
        "happy_students": 150,
        "years_exp":      5,
        "satisfaction":   99,
    }
    return render_template("index.html", projects=projects,
                           testimonials=testimonials, stats=stats,
                           user=current_user())


@app.route("/cinematic")
def cinematic_portfolio():
    """Next-generation cinematic portfolio experience"""
    projects = Project.query.all()
    return render_template("cinematic.html", projects=projects)


@app.route("/portfolio")
def portfolio():
    """Alias for cinematic portfolio"""
    return redirect(url_for('cinematic_portfolio'))


@app.route('/favicon.ico')
def favicon():
    return redirect(url_for('static', filename='img/logo.png'))


# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
@csrf.exempt
@limiter.limit("100 per minute", methods=["POST"]) # Increased for development/testing
def login():
    if request.method == "GET" and 'user_id' in session:
        return redirect(url_for('admin_panel') if session.get('role') == 'admin'
                        else url_for('user_dashboard'))

    tab   = request.args.get('tab', 'user')  # 'user' or 'admin'
    error = None
    origin_settings = get_google_origin_settings(f"{request.scheme}://{request.host}")

    if request.method == "POST":
        login_type = request.form.get('login_type', 'user')
        email      = normalize_email(request.form.get('email', ''))
        password   = request.form.get('password', '').strip()
        remember   = request.form.get('remember') == 'on'

        # Detection for AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                  request.headers.get('Accept') == 'application/json'

        user = find_user_by_email(email)

        if not user or not user.check_password(password):
            error = "Email or password is incorrect."
            if is_ajax: return jsonify({"success": False, "error": error})
            tab   = login_type
        elif not user.is_active:
            error = "Your account has been deactivated. Contact admin."
            if is_ajax: return jsonify({"success": False, "error": error})
            tab   = login_type
        elif login_type == 'admin' and normalize_role(user.role) != 'admin':
            error = "You don't have admin privileges."
            if is_ajax: return jsonify({"success": False, "error": error})
            tab   = 'admin'
        else:
            normalized_role = normalize_role(user.role)
            if normalize_email(user.email) == normalize_email(SUPERADMIN_EMAIL):
                normalized_role = 'admin'
            if user.role != normalized_role:
                user.role = normalized_role
                db.session.commit()

            establish_session_for_user(user, remember=remember)

            target = url_for('admin_panel') if normalized_role == 'admin' else url_for('user_dashboard')
            
            if is_ajax:
                return jsonify({
                    "success": True,
                    "redirect": target,
                    "email": session.get('user_email', ''),
                    "role": session.get('role', 'user'),
                    "is_superadmin": bool(session.get('is_superadmin')),
                })
            
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(target)

    return render_template(
        "login.html",
        tab=tab,
        error=error,
        google_signin_enabled=origin_settings["enabled"],
        google_current_origin=origin_settings["current_origin"],
        google_allowed_origins=origin_settings["allowed_origins"],
    )


@app.route("/register", methods=["GET", "POST"])
@csrf.exempt
@limiter.limit("50 per hour", methods=["POST"])
def register():
    if 'user_id' in session:
        return redirect(url_for('user_dashboard'))

    error = None

    if request.method == "POST":
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        confirm  = request.form.get('confirm', '').strip()

        # Detection for AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
                  request.headers.get('Accept') == 'application/json'

        if not name or len(name) < 2:
            error = "Name must be at least 2 characters."
        elif not validate_email(email):
            error = "Please enter a valid email address."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."
        elif password != confirm:
            error = "Passwords do not match."
        elif User.query.filter_by(email=email).first():
            error = "An account with this email already exists."
        
        if error:
            if is_ajax: return jsonify({"success": False, "error": error})
        else:
            user = User(name=name, email=email, role='user')
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            session['user_id']   = user.id
            session['user_name'] = user.name
            session['role']      = user.role
            
            target = url_for('user_dashboard')
            if is_ajax:
                return jsonify({"success": True, "redirect": target})
                
            flash(f"Account created! Welcome, {name}!", "success")
            return redirect(target)

    return render_template("login.html", tab='register', error=error)


@app.route("/send-otp", methods=["POST"])
@app.route("/forgot-password/send-otp", methods=["POST"])
@csrf.exempt
@limiter.limit("10 per hour", methods=["POST"])
def forgot_password_send_otp():
    data = request.get_json(silent=True) or request.form
    email = str(data.get("email", "")).strip().lower()
    debug_mode = app.debug or (os.getenv("DEBUG", "False").strip().lower() == "true")

    if not validate_email(email):
        return jsonify({"success": False, "error": "Please enter a valid email address."}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        # Avoid account enumeration by returning the same success message.
        payload = {
            "success": True,
            "message": "If this email is registered, an OTP has been sent."
        }
        if debug_mode:
            payload["debug"] = "DEV: Email not found in users table. OTP was not sent."
        return jsonify(payload)

    _cleanup_expired_otps()
    otp_code = _generate_otp_code()
    _save_otp_for_email(email, otp_code)

    try:
        _send_password_reset_otp(email, otp_code)
    except smtplib.SMTPAuthenticationError:
        app.logger.exception("SMTP authentication failed while sending OTP")
        PasswordResetOTP.query.filter_by(email=email).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({"success": False, "error": "Mail login failed. Set SMTP_PASS to a valid Gmail App Password."}), 500
    except Exception:
        app.logger.exception("Failed to send OTP email")
        PasswordResetOTP.query.filter_by(email=email).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({"success": False, "error": "Unable to send OTP email right now."}), 500

    payload = {"success": True, "message": "OTP sent to your email."}
    if debug_mode:
        payload["debug"] = "DEV: Email exists. OTP generated and email dispatched via SMTP."
    return jsonify(payload)


@app.route("/reset-password", methods=["POST"])
@app.route("/forgot-password/reset", methods=["POST"])
@csrf.exempt
@limiter.limit("20 per hour", methods=["POST"])
def forgot_password_reset():
    data = request.get_json(silent=True) or request.form
    email = str(data.get("email", "")).strip().lower()
    otp_code = str(data.get("otp", "")).strip()
    new_password = str(data.get("new_password") or data.get("newPassword") or "").strip()

    if not validate_email(email):
        return jsonify({"success": False, "error": "Please enter a valid email address."}), 400
    if len(new_password) < 6:
        return jsonify({"success": False, "error": "Password must be at least 6 characters."}), 400

    _cleanup_expired_otps()
    payload = _get_active_otp(email)
    if not payload:
        return jsonify({"success": False, "error": "OTP expired or not found."}), 400

    if payload.otp != otp_code:
        payload.attempts_left = max(int(payload.attempts_left or OTP_MAX_ATTEMPTS) - 1, 0)
        if payload.attempts_left <= 0:
            db.session.delete(payload)
            if not _safe_commit():
                return jsonify({"success": False, "error": "Server busy. Please try again."}), 503
            return jsonify({"success": False, "error": "Too many invalid attempts. Request a new OTP."}), 400
        if not _safe_commit():
            return jsonify({"success": False, "error": "Server busy. Please try again."}), 503
        return jsonify({"success": False, "error": "Invalid OTP."}), 400

    if not payload.is_verified:
        return jsonify({"success": False, "error": "Verify OTP before resetting password."}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        db.session.delete(payload)
        if not _safe_commit():
            return jsonify({"success": False, "error": "Server busy. Please try again."}), 503
        return jsonify({"success": False, "error": "Account not found."}), 404

    user.set_password(new_password)
    db.session.delete(payload)
    if not _safe_commit():
        return jsonify({"success": False, "error": "Server busy. Please try again."}), 503

    return jsonify({"success": True, "message": "Password reset successful. Please sign in."})


@app.route("/verify-otp", methods=["POST"])
@csrf.exempt
@limiter.limit("30 per hour", methods=["POST"])
def verify_otp():
    data = request.get_json(silent=True) or request.form
    email = str(data.get("email", "")).strip().lower()
    otp_code = str(data.get("otp", "")).strip()

    if not validate_email(email):
        return jsonify({"success": False, "error": "Please enter a valid email address."}), 400

    _cleanup_expired_otps()
    payload = _get_active_otp(email)
    if not payload:
        return jsonify({"success": False, "error": "OTP expired or not found."}), 400

    if payload.otp != otp_code:
        payload.attempts_left = max(int(payload.attempts_left or OTP_MAX_ATTEMPTS) - 1, 0)
        if payload.attempts_left <= 0:
            db.session.delete(payload)
            if not _safe_commit():
                return jsonify({"success": False, "error": "Server busy. Please try again."}), 503
            return jsonify({"success": False, "error": "Too many invalid attempts. Request a new OTP."}), 400
        if not _safe_commit():
            return jsonify({"success": False, "error": "Server busy. Please try again."}), 503
        return jsonify({"success": False, "error": "Invalid OTP."}), 400

    payload.is_verified = True
    if not _safe_commit():
        return jsonify({"success": False, "error": "Server busy. Please try again."}), 503

    return jsonify({"success": True, "message": "OTP verified."})


@app.route("/google-login", methods=["POST"])
@csrf.exempt
def google_login():
    token = request.json.get("credential") if request.is_json else request.form.get("credential")
    if not token:
        return jsonify({"success": False, "error": "Missing token"}), 400
        
    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), app.config['GOOGLE_CLIENT_ID'])
        if not idinfo.get("email_verified", False):
            return jsonify({"success": False, "error": "Google account email is not verified."}), 400

        email = normalize_email(idinfo.get('email', ''))
        if not email:
            return jsonify({"success": False, "error": "Google did not provide an email address."}), 400

        name = idinfo.get('name', email.split("@")[0])
        is_oauth_admin = is_admin_identity(email)
        
        user = find_user_by_email(email)
        if not user:
            user = User(name=name, email=email, role='admin' if is_oauth_admin else 'user')
            user.set_password(os.urandom(24).hex())
            db.session.add(user)
            db.session.commit()
        else:
            normalized_role = normalize_role(user.role)

            if user.role != normalized_role:
                user.role = normalized_role

            if is_admin_identity(email, existing_user=user) and user.role != 'admin':
                user.role = 'admin'

            if normalize_email(user.email) != email:
                user.email = email

            if name and user.name != name:
                user.name = name

            db.session.commit()
            
        establish_session_for_user(user, remember=True)
        flash(f"Signed in via Google! Welcome, {user.name}!", "success")
        
        target = url_for('admin_panel') if session['role'] == 'admin' else url_for('user_dashboard')
        return jsonify({
            "success": True,
            "redirect": target,
            "email": session.get('user_email', ''),
            "role": session.get('role', 'user'),
            "is_superadmin": bool(session.get('is_superadmin')),
        })
        
    except Exception as e:
        app.logger.exception("Google login verification failed")
        if app.debug:
            return jsonify({"success": False, "error": f"Google token verification failed: {str(e)}"}), 400
        return jsonify({"success": False, "error": "Invalid token"}), 400


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for('login'))


# ─── User Dashboard ───────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def user_dashboard():
    user = current_user()
    normalized_email = (user.email or "").strip().lower()
    my_requests = ProjectRequest.query.filter(
        db.or_(
            ProjectRequest.user_id == user.id,
            db.func.lower(ProjectRequest.email) == normalized_email,
        )
    ).order_by(ProjectRequest.created_at.desc()).all()

    active_updates = [r.id for r in my_requests if r.is_new_update]

    if active_updates:
        preview = [r for r in my_requests if r.id in active_updates][:3]
        for req in preview:
            flash(f"Mission Update: Project #{req.id:04d} has been updated to '{req.status}'!", "success")
        if len(active_updates) > len(preview):
            flash(f"{len(active_updates) - len(preview)} more project update(s) available.", "success")

    for req in my_requests:
        if req.is_new_update:
            req.is_new_update = False
    db.session.commit()

    total_value = sum((r.value or 0) for r in my_requests)
    done_count = sum(1 for r in my_requests if r.status == "Done")
    completion_pct = int((done_count / len(my_requests)) * 100) if my_requests else 0

    return render_template(
        "dashboard.html",
        user=user,
        my_requests=my_requests,
        active_updates=active_updates,
        total_value=total_value,
        completion_pct=completion_pct,
    )


# ─── API — Contact Form ───────────────────────────────────────────────────────

@app.route("/api/contact", methods=["POST"])
@csrf.exempt
@limiter.limit("10 per hour", methods=["POST"])  # Prevent contact spam
def api_contact():
    if 'user_id' not in session:
        return jsonify({
            "success": False, 
            "message": "Login required", 
            "redirect": url_for('login')
        }), 401

    data = request.get_json(silent=True) or request.form

    name    = str(data.get("name",    "")).strip()
    email   = str(data.get("email",   "")).strip()
    phone   = str(data.get("phone",   "")).strip()
    service = str(data.get("service", "")).strip()
    deadline= str(data.get("deadline","")).strip()
    message = str(data.get("message", "")).strip()

    errors = {}
    if not name:                             errors["name"]    = "Name is required."
    if not email or not validate_email(email): errors["email"] = "Valid email is required."
    if not service:                          errors["service"] = "Please select a service."
    if not message or len(message) < 20:     errors["message"] = "Please describe your project (min 20 chars)."

    if errors:
        return jsonify({"success": False, "errors": errors}), 400

    uid = session.get('user_id')
    req = ProjectRequest(user_id=uid, name=name, email=email, phone=phone,
                         service=service, deadline=deadline, message=message)
    db.session.add(req)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Thanks {name}! Your request has been received. Redirecting you to your dashboard...",
        "id": req.id
    }), 201


@app.route("/api/projects")
def api_projects():
    category = request.args.get("category", "all")
    projects = Project.query.all() if category == "all" \
               else Project.query.filter_by(category=category).all()
    return jsonify([p.to_dict() for p in projects])


# ─── Admin Routes ─────────────────────────────────────────────────────────────

@app.route("/admin")
@admin_required
def admin_panel():
    requests_list = ProjectRequest.query.order_by(
        ProjectRequest.created_at.desc()
    ).all()
    
    # Calculate more advanced stats
    total_req = len(requests_list)
    pending_req = sum(1 for r in requests_list if r.status != 'Done')
    done_req = sum(1 for r in requests_list if r.status == 'Done')
    
    total_value = sum((r.value or 0) for r in requests_list)
    avg_value = int(total_value / total_req) if total_req else 0
    completion_rate = round((done_req / total_req) * 100, 1) if total_req else 0.0
    high_priority_count = sum(1 for r in requests_list if (r.priority or "").lower() == "high")
    today_utc = datetime.utcnow().date()
    todays_inquiries = sum(1 for r in requests_list if r.created_at and r.created_at.date() == today_utc)

    stats = {
        'total_requests': ProjectRequest.query.count(),
        'pending_requests': ProjectRequest.query.filter(ProjectRequest.status != 'Done').count(),
        'done_requests': ProjectRequest.query.filter_by(status='Done').count(),
        'projected_revenue': db.session.query(db.func.sum(ProjectRequest.value)).scalar() or 0
    }

    admin_metrics = {
        'completion_rate': completion_rate,
        'high_priority_count': high_priority_count,
        'avg_value': avg_value,
        'todays_inquiries': todays_inquiries,
    }
    
    # Distribution Analysis (Service counts)
    services = ['Web Development', 'Software Projects', 'Hardware & IoT', 'AI & Machine Learning', 'Mobile Apps', 'Reports & Documentation']
    dist_data = [ProjectRequest.query.filter_by(service=s).count() for s in services]

    admin_user = current_user()
    admin_email = (admin_user.email or "").strip().lower() if admin_user else ""
    my_tasks = AdminTask.query.filter(
        db.func.lower(AdminTask.assigned_to_email) == admin_email
    ).order_by(AdminTask.created_at.desc()).all()
    admin_users = User.query.filter_by(role='admin', is_active=True).order_by(User.email.asc()).all()
    managed_admins = User.query.filter_by(role='admin').order_by(User.created_at.desc()).all()
    assignment_feed = AdminTask.query.order_by(AdminTask.created_at.desc()).limit(25).all()
    all_admin_tasks = AdminTask.query.order_by(AdminTask.created_at.desc()).limit(120).all()
    admin_task_leaderboard = []
    superadmin_audit_feed = []
    superadmin_summary = {}
    risk_admins = []
    critical_pending_tasks = []

    if is_super_admin(admin_user):
        now_utc = datetime.utcnow()
        task_perf = {}
        pending_count = 0
        in_progress_count = 0
        done_count = 0
        for task in all_admin_tasks:
            email = (task.assigned_to_email or "").strip().lower()
            if not email:
                continue
            row = task_perf.setdefault(email, {"email": email, "total": 0, "done": 0, "in_progress": 0, "pending": 0})
            row["total"] += 1
            status = (task.status or "").strip()
            if status == "Done":
                row["done"] += 1
                done_count += 1
            elif status == "In Progress":
                row["in_progress"] += 1
                in_progress_count += 1
            else:
                row["pending"] += 1
                pending_count += 1

                # Pending tasks older than 2 days are marked as critical queue.
                if task.created_at and (now_utc - task.created_at).days >= 2:
                    critical_pending_tasks.append(task)

        admin_task_leaderboard = sorted(
            task_perf.values(),
            key=lambda x: (x["done"], x["in_progress"], x["total"]),
            reverse=True,
        )[:12]
        superadmin_audit_feed = AdminAuditLog.query.order_by(AdminAuditLog.created_at.desc()).limit(40).all()

        total_admin_accounts = len(managed_admins)
        active_admin_accounts = sum(1 for u in managed_admins if bool(u.is_active))
        inactive_admin_accounts = max(total_admin_accounts - active_admin_accounts, 0)
        total_task_count = len(all_admin_tasks)
        completion_ratio = round((done_count / total_task_count) * 100, 1) if total_task_count else 0.0

        today_actions = sum(
            1 for ev in superadmin_audit_feed
            if ev.created_at and ev.created_at.date() == now_utc.date()
        )

        risk_admins = [
            row for row in admin_task_leaderboard
            if row["pending"] > row["done"] + 1
        ][:6]

        critical_pending_tasks = sorted(
            critical_pending_tasks,
            key=lambda t: t.created_at or now_utc,
        )[:8]

        superadmin_summary = {
            "total_admin_accounts": total_admin_accounts,
            "active_admin_accounts": active_admin_accounts,
            "inactive_admin_accounts": inactive_admin_accounts,
            "total_task_count": total_task_count,
            "pending_task_count": pending_count,
            "in_progress_task_count": in_progress_count,
            "done_task_count": done_count,
            "completion_ratio": completion_ratio,
            "today_actions": today_actions,
            "critical_pending_count": len(critical_pending_tasks),
        }

    return render_template("admin.html", 
                           requests=requests_list, 
                           stats=stats,
                           admin_metrics=admin_metrics,
                           dist_data=dist_data,
                           admin=admin_user,
                           is_superadmin=is_super_admin(admin_user),
                           my_tasks=my_tasks,
                           admin_users=admin_users,
                           managed_admins=managed_admins,
                           assignment_feed=assignment_feed,
                           all_admin_tasks=all_admin_tasks,
                           admin_task_leaderboard=admin_task_leaderboard,
                           superadmin_audit_feed=superadmin_audit_feed,
                           superadmin_summary=superadmin_summary,
                           risk_admins=risk_admins,
                           critical_pending_tasks=critical_pending_tasks)


@app.route("/admin/tasks/assign", methods=["POST"])
@csrf.exempt
@admin_required
def assign_admin_task():
    creator = current_user()
    if not is_super_admin(creator):
        flash("Only the superadmin can assign admin tasks.", "danger")
        return redirect(url_for("admin_panel"))

    title = str(request.form.get("title", "")).strip()
    details = str(request.form.get("details", "")).strip()
    assigned_to_email = str(request.form.get("assigned_to_email", "")).strip().lower()

    if len(title) < 3 or len(title) > 160:
        flash("Task title must be between 3 and 160 characters.", "danger")
        return redirect(url_for("admin_panel"))

    if not validate_email(assigned_to_email):
        flash("Please choose a valid admin email.", "danger")
        return redirect(url_for("admin_panel"))

    assignee = User.query.filter(
        db.func.lower(User.email) == assigned_to_email,
        User.role == 'admin',
        User.is_active.is_(True)
    ).first()
    if not assignee:
        flash("Selected email is not an active admin account.", "danger")
        return redirect(url_for("admin_panel"))

    task = AdminTask(
        title=title,
        details=details,
        assigned_to_email=assigned_to_email,
        assigned_by_email=(creator.email or "").strip().lower(),
        status='Pending'
    )
    db.session.add(task)
    log_superadmin_action(
        action="TASK_ASSIGNED",
        target=assigned_to_email,
        details=f"title={title}",
        actor=creator,
    )
    db.session.commit()

    flash(f"Task assigned to {assigned_to_email}.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/tasks/<int:task_id>/status", methods=["POST"])
@csrf.exempt
@admin_required
def update_admin_task_status(task_id):
    actor = current_user()
    actor_email = (actor.email or "").strip().lower() if actor else ""
    next_status = str(request.form.get("status", "")).strip()
    allowed_statuses = {"Pending", "In Progress", "Done"}

    if next_status not in allowed_statuses:
        flash("Invalid task status selected.", "danger")
        return redirect(url_for("admin_panel"))

    task = AdminTask.query.get_or_404(task_id)
    task_owner_email = (task.assigned_to_email or "").strip().lower()
    if task_owner_email != actor_email and not is_super_admin(actor):
        flash("You can only update tasks assigned to your admin account.", "danger")
        return redirect(url_for("admin_panel"))

    task.status = next_status
    task.updated_at = datetime.utcnow()
    if is_super_admin(actor):
        log_superadmin_action(
            action="TASK_STATUS_UPDATED",
            target=(task.assigned_to_email or "").strip().lower(),
            details=f"task_id={task.id},status={next_status}",
            actor=actor,
        )
    db.session.commit()
    flash("Task status updated.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/tasks/assign-bulk", methods=["POST"])
@csrf.exempt
@admin_required
def assign_admin_task_bulk():
    creator = current_user()
    if not is_super_admin(creator):
        flash("Only the superadmin can assign bulk tasks.", "danger")
        return redirect(url_for("admin_panel"))

    title = str(request.form.get("title", "")).strip()
    details = str(request.form.get("details", "")).strip()
    raw_emails = str(request.form.get("admin_emails", "")).strip()

    if len(title) < 3 or len(title) > 160:
        flash("Task title must be between 3 and 160 characters.", "danger")
        return redirect(url_for("admin_panel"))
    if not raw_emails:
        flash("Provide at least one admin email.", "danger")
        return redirect(url_for("admin_panel"))

    cleaned = raw_emails.replace("\n", ",").replace(";", ",")
    email_list = []
    seen = set()
    for part in cleaned.split(","):
        email = part.strip().lower()
        if not email or email in seen:
            continue
        if validate_email(email):
            email_list.append(email)
            seen.add(email)

    if not email_list:
        flash("No valid admin emails provided.", "danger")
        return redirect(url_for("admin_panel"))

    admins = User.query.filter(User.role == 'admin', User.is_active.is_(True)).all()
    active_admin_emails = {(u.email or "").strip().lower() for u in admins}

    valid_targets = [e for e in email_list if e in active_admin_emails]
    skipped = [e for e in email_list if e not in active_admin_emails]

    if not valid_targets:
        flash("None of the provided emails belong to active admin accounts.", "danger")
        return redirect(url_for("admin_panel"))

    for email in valid_targets:
        db.session.add(AdminTask(
            title=title,
            details=details,
            assigned_to_email=email,
            assigned_by_email=(creator.email or "").strip().lower(),
            status='Pending'
        ))

    log_superadmin_action(
        action="TASK_BULK_ASSIGNED",
        target=",".join(valid_targets)[:180],
        details=f"title={title},assigned={len(valid_targets)},skipped={len(skipped)}",
        actor=creator,
    )
    db.session.commit()

    if skipped:
        flash(f"Assigned to {len(valid_targets)} admins. Skipped {len(skipped)} invalid/inactive emails.", "warning")
    else:
        flash(f"Assigned task to {len(valid_targets)} admins.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/admins/create", methods=["POST"])
@csrf.exempt
@admin_required
def superadmin_create_admin():
    actor = current_user()
    if not is_super_admin(actor):
        flash("Only the superadmin can create admin accounts.", "danger")
        return redirect(url_for("admin_panel"))

    name = str(request.form.get("name", "")).strip()
    email = str(request.form.get("email", "")).strip().lower()
    password = str(request.form.get("password", "")).strip()

    if len(name) < 2:
        flash("Name must be at least 2 characters.", "danger")
        return redirect(url_for("admin_panel"))
    if not validate_email(email):
        flash("Please enter a valid email address.", "danger")
        return redirect(url_for("admin_panel"))
    if len(password) < 6:
        flash("Password must be at least 6 characters.", "danger")
        return redirect(url_for("admin_panel"))
    if User.query.filter(db.func.lower(User.email) == email).first():
        flash("An account with this email already exists.", "warning")
        return redirect(url_for("admin_panel"))

    user = User(name=name, email=email, role='admin', is_active=True)
    user.set_password(password)
    db.session.add(user)
    log_superadmin_action(
        action="ADMIN_CREATED",
        target=email,
        details=f"name={name}",
        actor=actor,
    )
    db.session.commit()

    flash(f"Admin account created for {email}.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/admins/<int:uid>/update", methods=["POST"])
@csrf.exempt
@admin_required
def superadmin_update_admin(uid):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
              request.headers.get('Accept') == 'application/json'

    actor = current_user()
    if not is_super_admin(actor):
        if is_ajax:
            return jsonify({"success": False, "message": "Only the superadmin can update admin accounts."}), 403
        flash("Only the superadmin can update admin accounts.", "danger")
        return redirect(url_for("admin_panel"))

    target = User.query.get_or_404(uid)
    if target.role != 'admin':
        if is_ajax:
            return jsonify({"success": False, "message": "Selected account is not an admin."}), 400
        flash("Selected account is not an admin.", "danger")
        return redirect(url_for("admin_panel"))

    name = str(request.form.get("name", "")).strip()
    email = str(request.form.get("email", "")).strip().lower()
    new_password = str(request.form.get("password", "")).strip()
    is_active = str(request.form.get("is_active", "")).strip() == "1"

    if len(name) < 2:
        if is_ajax:
            return jsonify({"success": False, "message": "Name must be at least 2 characters."}), 400
        flash("Name must be at least 2 characters.", "danger")
        return redirect(url_for("admin_panel"))
    if not validate_email(email):
        if is_ajax:
            return jsonify({"success": False, "message": "Please enter a valid email address."}), 400
        flash("Please enter a valid email address.", "danger")
        return redirect(url_for("admin_panel"))
    if new_password and len(new_password) < 6:
        if is_ajax:
            return jsonify({"success": False, "message": "New password must be at least 6 characters."}), 400
        flash("New password must be at least 6 characters.", "danger")
        return redirect(url_for("admin_panel"))

    target_email_before = (target.email or "").strip().lower()
    target_is_superadmin = target_email_before == SUPERADMIN_EMAIL

    existing = User.query.filter(
        db.func.lower(User.email) == email,
        User.id != target.id
    ).first()
    if existing:
        if is_ajax:
            return jsonify({"success": False, "message": "Email already used by another account."}), 400
        flash("Email already used by another account.", "danger")
        return redirect(url_for("admin_panel"))

    if target_is_superadmin and email != SUPERADMIN_EMAIL:
        if is_ajax:
            return jsonify({"success": False, "message": "Superadmin email cannot be changed."}), 400
        flash("Superadmin email cannot be changed.", "danger")
        return redirect(url_for("admin_panel"))

    target.name = name
    target.email = email
    target.is_active = True if target_is_superadmin else is_active
    if new_password:
        target.set_password(new_password)

    # Keep task ownership references in sync if non-superadmin email changes.
    if target_email_before != email and not target_is_superadmin:
        AdminTask.query.filter(
            db.func.lower(AdminTask.assigned_to_email) == target_email_before
        ).update({"assigned_to_email": email}, synchronize_session=False)
        AdminTask.query.filter(
            db.func.lower(AdminTask.assigned_by_email) == target_email_before
        ).update({"assigned_by_email": email}, synchronize_session=False)

    log_superadmin_action(
        action="ADMIN_UPDATED",
        target=email,
        details=f"uid={target.id},active={target.is_active},password_changed={bool(new_password)}",
        actor=actor,
    )
    db.session.commit()
    flash(f"Admin account updated for {target.email}.", "success")

    if is_ajax:
        return jsonify({
            "success": True,
            "message": "",
            "id": target.id,
            "name": target.name,
            "email": target.email,
            "is_active": bool(target.is_active),
        })

    return redirect(url_for("admin_panel"))


@app.route("/admin/admins/<int:uid>/delete", methods=["POST"])
@csrf.exempt
@admin_required
def superadmin_delete_admin(uid):
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
              request.headers.get('Accept') == 'application/json'

    actor = current_user()
    if not is_super_admin(actor):
        if is_ajax:
            return jsonify({"success": False, "message": "Only the superadmin can delete admin accounts."}), 403
        flash("Only the superadmin can delete admin accounts.", "danger")
        return redirect(url_for("admin_panel"))

    target = User.query.get_or_404(uid)
    target_email = (target.email or "").strip().lower()
    if target.role != 'admin':
        if is_ajax:
            return jsonify({"success": False, "message": "Selected account is not an admin."}), 400
        flash("Selected account is not an admin.", "danger")
        return redirect(url_for("admin_panel"))
    if target_email == SUPERADMIN_EMAIL:
        if is_ajax:
            return jsonify({"success": False, "message": "Superadmin account cannot be deleted."}), 400
        flash("Superadmin account cannot be deleted.", "danger")
        return redirect(url_for("admin_panel"))

    AdminTask.query.filter(
        (db.func.lower(AdminTask.assigned_to_email) == target_email) |
        (db.func.lower(AdminTask.assigned_by_email) == target_email)
    ).delete(synchronize_session=False)

    log_superadmin_action(
        action="ADMIN_DELETED",
        target=target_email,
        details=f"uid={target.id}",
        actor=actor,
    )
    db.session.delete(target)
    db.session.commit()

    if is_ajax:
        return jsonify({
            "success": True,
            "message": "",
            "id": uid,
            "email": target_email,
        })

    flash(f"Admin account {target_email} deleted.", "success")

    return redirect(url_for("admin_panel"))


@app.route("/admin/admins/<int:uid>/reset-password", methods=["POST"])
@csrf.exempt
@admin_required
def superadmin_reset_admin_password(uid):
    actor = current_user()
    if not is_super_admin(actor):
        flash("Only the superadmin can reset admin passwords.", "danger")
        return redirect(url_for("admin_panel"))

    target = User.query.get_or_404(uid)
    if target.role != 'admin':
        flash("Selected account is not an admin.", "danger")
        return redirect(url_for("admin_panel"))

    temp_password = os.urandom(6).hex()
    target.set_password(temp_password)
    log_superadmin_action(
        action="ADMIN_PASSWORD_RESET",
        target=(target.email or "").strip().lower(),
        details=f"uid={target.id}",
        actor=actor,
    )
    db.session.commit()
    flash(f"Temporary password for {target.email}: {temp_password}", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/tasks/<int:task_id>/reassign", methods=["POST"])
@csrf.exempt
@admin_required
def superadmin_reassign_task(task_id):
    actor = current_user()
    if not is_super_admin(actor):
        flash("Only the superadmin can reassign admin tasks.", "danger")
        return redirect(url_for("admin_panel"))

    next_email = str(request.form.get("assigned_to_email", "")).strip().lower()
    if not validate_email(next_email):
        flash("Please choose a valid admin email for reassignment.", "danger")
        return redirect(url_for("admin_panel"))

    assignee = User.query.filter(
        db.func.lower(User.email) == next_email,
        User.role == 'admin',
        User.is_active.is_(True)
    ).first()
    if not assignee:
        flash("Target reassignment email is not an active admin account.", "danger")
        return redirect(url_for("admin_panel"))

    task = AdminTask.query.get_or_404(task_id)
    previous = (task.assigned_to_email or "").strip().lower()
    task.assigned_to_email = next_email
    task.status = 'Pending'
    task.updated_at = datetime.utcnow()
    log_superadmin_action(
        action="TASK_REASSIGNED",
        target=next_email,
        details=f"task_id={task.id},from={previous},to={next_email}",
        actor=actor,
    )
    db.session.commit()
    flash(f"Task #{task.id:04d} reassigned to {next_email}.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/tasks/<int:task_id>/delete", methods=["POST"])
@csrf.exempt
@admin_required
def superadmin_delete_task(task_id):
    actor = current_user()
    if not is_super_admin(actor):
        flash("Only the superadmin can delete admin tasks.", "danger")
        return redirect(url_for("admin_panel"))

    task = AdminTask.query.get_or_404(task_id)
    log_superadmin_action(
        action="TASK_DELETED",
        target=(task.assigned_to_email or "").strip().lower(),
        details=f"task_id={task.id},title={task.title}",
        actor=actor,
    )
    db.session.delete(task)
    db.session.commit()
    flash(f"Task #{task_id:04d} removed.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/bulk-update", methods=["POST"])
@csrf.exempt
@admin_required
def admin_bulk_update():
    data = request.get_json(silent=True) or request.form
    ids = data.get("ids", [])
    action = str(data.get("action", "")).strip().lower()

    if isinstance(ids, str):
        ids = [x.strip() for x in ids.split(",") if x.strip()]

    try:
        parsed_ids = [int(x) for x in ids]
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "Invalid request ids."}), 400

    if not parsed_ids:
        return jsonify({"success": False, "message": "Select at least one inquiry."}), 400

    rows = ProjectRequest.query.filter(ProjectRequest.id.in_(parsed_ids)).all()
    if not rows:
        return jsonify({"success": False, "message": "No matching inquiries found."}), 404

    try:
        if action == "mark_done":
            for row in rows:
                row.status = "Done"
                row.is_new_update = True
        elif action == "mark_progress":
            for row in rows:
                row.status = "In Progress"
                row.is_new_update = True
        elif action == "priority_high":
            for row in rows:
                row.priority = "High"
                row.is_new_update = True
        elif action == "priority_medium":
            for row in rows:
                row.priority = "Medium"
                row.is_new_update = True
        elif action == "priority_low":
            for row in rows:
                row.priority = "Low"
                row.is_new_update = True
        elif action == "delete":
            for row in rows:
                db.session.delete(row)
        else:
            return jsonify({"success": False, "message": "Unsupported bulk action."}), 400

        db.session.commit()
    except Exception:
        db.session.rollback()
        app.logger.exception("Bulk admin action failed")
        return jsonify({"success": False, "message": "Bulk action failed. Try again."}), 500

    return jsonify({
        "success": True,
        "count": len(rows),
        "message": f"Bulk action '{action}' applied to {len(rows)} inquiries."
    })


@app.route("/admin/create-user", methods=["POST"])
@csrf.exempt
@admin_required
def admin_create_user():
    creator = current_user()

    name = str(request.form.get("name", "")).strip()
    email = str(request.form.get("email", "")).strip().lower()
    password = str(request.form.get("password", "")).strip()
    role = str(request.form.get("role", "user")).strip().lower()

    if role not in {"user", "admin"}:
        flash("Invalid role selected.", "danger")
        return redirect(url_for("admin_panel"))

    # Only explicit super-admin emails can grant admin role to others.
    if role == "admin" and not is_super_admin(creator):
        flash("Only authorized super admins can create admin accounts.", "danger")
        return redirect(url_for("admin_panel"))

    if len(name) < 2:
        flash("Name must be at least 2 characters.", "danger")
        return redirect(url_for("admin_panel"))
    if not validate_email(email):
        flash("Please enter a valid email address.", "danger")
        return redirect(url_for("admin_panel"))
    if len(password) < 6:
        flash("Password must be at least 6 characters.", "danger")
        return redirect(url_for("admin_panel"))
    if User.query.filter_by(email=email).first():
        flash("A user with this email already exists.", "warning")
        return redirect(url_for("admin_panel"))

    user = User(name=name, email=email, role=role)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    flash(f"Created {role} account for {name} ({email}).", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/update-project", methods=["POST"])
@csrf.exempt
@admin_required
def update_project():
    # Support both JSON and Form Data for testing/compatibility
    if request.is_json:
        data = request.get_json()
        req_id = data.get("req_id")
        status = data.get("status")
        priority = data.get("priority")
        value = int(data.get("value", 0))
        message = data.get("message")
    else:
        req_id = request.form.get("req_id")
        status = request.form.get("status")
        priority = request.form.get("priority")
        value = int(request.form.get("value", 0))
        message = request.form.get("message")

    req = ProjectRequest.query.get_or_404(req_id)
    
    req.status = status
    req.priority = priority
    req.value = value
    if message is not None:
        req.message = message
    req.is_new_update = True  # Notify student via dashboard sync too
    
    db.session.commit()
    
    if request.is_json or request.headers.get("Accept") == "application/json":
        return jsonify({
            "success": True, 
            "message": f"Project #{req.id:04d} updated to {status} successfully.",
            "id": req.id
        })
        
    # Fallback to standard redirect if not AJAX
    flash(f"Project #{req.id:04d} updated successfully.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/delete/<int:req_id>", methods=["POST"])
@csrf.exempt
@admin_required
def delete_request(req_id):
    req = ProjectRequest.query.get_or_404(req_id)
    db.session.delete(req)
    db.session.commit()
    
    msg = f"Inquiry #{req_id:04d} removed permanently."
    
    if request.is_json or request.headers.get("Accept") == "application/json":
        return jsonify({"success": True, "message": msg, "id": req_id})
        
    flash(msg, "success")
    return redirect(url_for("admin_panel"))

@app.route("/admin/api/latest-updates")
@admin_required
def api_latest_updates():
    last_check_str = request.args.get('last_check')
    if not last_check_str:
        return jsonify({"new_count": 0, "latest": []})
    
    try:
        last_check = datetime.fromtimestamp(float(last_check_str) / 1000.0)
    except ValueError:
        return jsonify({"new_count": 0, "latest": []})
        
    new_reqs = ProjectRequest.query.filter(ProjectRequest.created_at > last_check).all()
    return jsonify({
        "new_count": len(new_reqs),
        "latest": [{"id": r.id, "name": r.name, "service": r.service} for r in new_reqs]
    })


@app.route("/admin/export/pdf")
@admin_required
def export_pdf():
    from fpdf import FPDF
    
    class PDF(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 20)
            self.set_text_color(0, 82, 204) # Unitary X Blue
            self.cell(0, 15, 'Unitary X - Project Inquiry Report', 0, 1, 'C')
            self.set_font('Helvetica', 'I', 10)
            self.set_text_color(100, 100, 100)
            self.cell(0, 10, f'Generated on: {datetime.now().strftime("%d %b %Y, %I:%M %p")}', 0, 1, 'C')
            self.ln(10)

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    # Use landscape for more columns
    pdf = PDF(orientation='L', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 10)
    
    # Table Header
    pdf.set_fill_color(0, 82, 204)
    pdf.set_text_color(255, 255, 255)
    headers = ["ID", "Client Name", "Email", "Service", "Status", "Date"]
    col_widths = [15, 50, 70, 60, 40, 40]
    
    for i, h in enumerate(headers):
        pdf.cell(col_widths[i], 12, h, 1, 0, 'C', True)
    pdf.ln()

    # Table Data
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(23, 43, 77)
    requests_list = ProjectRequest.query.order_by(ProjectRequest.created_at.desc()).all()
    
    fill = False
    for r in requests_list:
        pdf.set_fill_color(244, 247, 250)
        pdf.cell(col_widths[0], 10, f"#{r.id:04d}", 1, 0, 'C', fill)
        pdf.cell(col_widths[1], 10, f" {r.name[:25]}", 1, 0, 'L', fill)
        pdf.cell(col_widths[2], 10, f" {r.email[:35]}", 1, 0, 'L', fill)
        pdf.cell(col_widths[3], 10, f" {r.service[:30]}", 1, 0, 'L', fill)
        pdf.cell(col_widths[4], 10, f" {r.status}", 1, 0, 'C', fill)
        pdf.cell(col_widths[5], 10, f" {r.created_at.strftime('%d.%m.%y')}", 1, 0, 'C', fill)
        pdf.ln()
        fill = not fill

    from io import BytesIO
    from flask import send_file
    
    response = send_file(
        BytesIO(pdf.output()),
        mimetype='application/pdf',
        as_attachment=True,
        download_name='unitaryx_leads.pdf'
    )
    return response


@app.route("/admin/export/csv")
@admin_required
def export_csv():
    requests_list = ProjectRequest.query.order_by(ProjectRequest.created_at.desc()).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Name", "Email", "Phone", "Service", "Deadline", "Status",
        "Priority", "Value", "Created At"
    ])

    for r in requests_list:
        writer.writerow([
            f"#{r.id:04d}",
            r.name,
            r.email,
            r.phone or "",
            r.service,
            r.deadline or "",
            r.status,
            r.priority,
            r.value or 0,
            r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=unitaryx_leads.csv"
    return response

@app.route("/admin/chart-data")
@admin_required
def chart_data():
    requests_list = ProjectRequest.query.all()
    services_count = {}
    for r in requests_list:
        services_count[r.service] = services_count.get(r.service, 0) + 1
    return jsonify({
        "labels": list(services_count.keys()),
        "data": list(services_count.values())
    })

@app.route("/admin/toggle-user/<int:uid>", methods=["POST"])
@admin_required
def toggle_user(uid):
    user = User.query.get_or_404(uid)
    user.is_active = not user.is_active
    db.session.commit()
    return redirect(url_for("admin_panel"))


# ─── Entry Point ──────────────────────────────────────────────────────────────

with app.app_context():
    db.create_all()
    seed_data()

if __name__ == "__main__":
    with app.app_context():
        print("\n" + "="*58)
        print("  [*]  Unitary X Freelancer Website")
        print("  [*]  Main Site : http://127.0.0.1:5005")
        print("  [*]  Login     : http://127.0.0.1:5005/login")
        print("  [*]  Admin     : http://127.0.0.1:5005/admin")
        print("  [*]  Admin creds: admin@unitaryx.com / Admin@123")
        print("  [*]  Superadmin: harikavi1301@gmail.com / hari@123")
        print("="*58 + "\n")
    app.run(
        host='0.0.0.0',
        debug=os.getenv("DEBUG", "True") == "True",
        port=int(os.getenv("PORT", 5005))
    )
