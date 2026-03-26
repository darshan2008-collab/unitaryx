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
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy import inspect, text
from werkzeug.middleware.proxy_fix import ProxyFix

# Security & Config
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

# Keep container/host env vars authoritative while still supporting local .env defaults.
APP_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(APP_DIR, ".env"), override=False)
# Also support launching from workspace root where SMTP/OAuth vars are often stored.
load_dotenv(os.path.join(os.path.dirname(APP_DIR), ".env"), override=False)

app = Flask(
    __name__,
    template_folder=os.path.join(APP_DIR, "templates"),
    static_folder=os.path.join(APP_DIR, "static"),
)
# Respect original scheme/host when running behind reverse proxies (NPM/Traefik).
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1, x_port=1)
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0
app.config["TEMPLATES_AUTO_RELOAD"] = True
app.jinja_env.auto_reload = True
app.secret_key = os.getenv("SECRET_KEY", "fallback_weak_key_for_dev_only")
PASSWORD_HASH_METHOD = (os.getenv("PASSWORD_HASH_METHOD") or "pbkdf2:sha256:260000").strip()

_default_google_client_id = "your_google_client_id_here.apps.googleusercontent.com"
_env_google_client_id = (os.getenv("GOOGLE_CLIENT_ID") or "").strip()
if not _env_google_client_id or "your_google_client_id_here" in _env_google_client_id:
    app.config['GOOGLE_CLIENT_ID'] = _default_google_client_id
else:
    app.config['GOOGLE_CLIENT_ID'] = _env_google_client_id

DEFAULT_GOOGLE_ALLOWED_ORIGINS = {
    "https://unitaryx.org",
    "http://localhost:5005",
    "http://127.0.0.1:5005",
    "http://unitaryx.org",
    
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


def normalize_admin_scope(value):
    scope = (value or "ops").strip().lower()
    return scope if scope in {"superadmin", "ops", "finance", "support"} else "ops"


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
    admin_user = User.query.filter(
        db.func.lower(User.email) == normalized,
        db.func.lower(User.role) == 'admin'
    ).first()
    if admin_user:
        return True

    cred_record = AdminCredentialRecord.query.filter(
        db.func.lower(AdminCredentialRecord.admin_email) == normalized
    ).first()
    if cred_record:
        return True

    return normalized in oauth_admin_emails()


def establish_session_for_user(user, remember=False, profile_photo=None, auth_provider="password"):
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
    session['admin_scope'] = normalize_admin_scope(
        'superadmin' if session['is_superadmin'] else getattr(user, 'admin_scope', 'ops')
    ) if role == 'admin' else ''
    session['user_profile_photo'] = (profile_photo or "").strip()
    session['auth_provider'] = (auth_provider or "password").strip().lower()

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
    # Prevent stale cache so local template/CSS/JS changes are visible immediately.
    path = (request.path or "").lower()
    if (
        path.startswith("/static/")
        or response.mimetype in {"text/html", "text/css", "application/javascript", "application/json"}
        or path in {"/login", "/send-otp", "/verify-otp", "/reset-password"}
    ):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response

# ─── Database ─────────────────────────────────────────────────────────────────
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'unitaryx_v2.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db_uri = (app.config['SQLALCHEMY_DATABASE_URI'] or "").lower()
if db_uri.startswith("sqlite"):
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "connect_args": {"timeout": 5}
    }
else:
    app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
        "connect_args": {"connect_timeout": 5},
        "pool_pre_ping": True,
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
    admin_scope  = db.Column(db.String(20), default='ops')     # superadmin | ops | finance | support
    created_at   = db.Column(db.DateTime, default=datetime.utcnow)
    is_active    = db.Column(db.Boolean, default=True)

    def set_password(self, raw):
        self.password = generate_password_hash(raw, method=PASSWORD_HASH_METHOD)

    def check_password(self, raw):
        return check_password_hash(self.password, raw)


class SiteTrafficEvent(db.Model):
    """Stores anonymous and signed-in traffic events for analytics."""
    __tablename__ = 'site_traffic_events'

    id = db.Column(db.Integer, primary_key=True)
    visitor_id = db.Column(db.String(80), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    user_email = db.Column(db.String(150), nullable=True, index=True)
    event_type = db.Column(db.String(20), nullable=False, index=True)  # page_view | scroll
    page_path = db.Column(db.String(260), nullable=False)
    scroll_percent = db.Column(db.Integer, nullable=True)
    referrer = db.Column(db.String(260), nullable=True)
    ip_address = db.Column(db.String(64), nullable=True)
    user_agent = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)


class PasswordResetOTP(db.Model):
    """Stores OTP codes for password reset flow."""
    __tablename__ = 'password_reset_otps'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), nullable=False, index=True)
    otp = db.Column(db.String(255), nullable=False)
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
    
class AdminCredentialRecord(db.Model):
    """Stores superadmin-managed admin credential references."""
    __tablename__ = 'admin_credential_records'

    id = db.Column(db.Integer, primary_key=True)
    admin_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    admin_email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    temporary_password = db.Column(db.String(200), nullable=False)
    permanent_password = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
def upsert_admin_credential_record(admin_user_id, admin_email, temporary_password, permanent_password):
    normalized_email = (admin_email or "").strip().lower()
    record = AdminCredentialRecord.query.filter(
        db.func.lower(AdminCredentialRecord.admin_email) == normalized_email
    ).first()

    if not record and admin_user_id:
        record = AdminCredentialRecord.query.filter_by(admin_user_id=admin_user_id).first()

    if record:
        record.admin_user_id = admin_user_id or record.admin_user_id
        record.admin_email = normalized_email
        record.temporary_password = temporary_password
        record.permanent_password = permanent_password
        record.updated_at = datetime.utcnow()
    else:
        record = AdminCredentialRecord(
            admin_user_id=admin_user_id,
            admin_email=normalized_email,
            temporary_password=temporary_password,
            permanent_password=permanent_password,
        )
        db.session.add(record)

    return record


def sync_admin_vault_to_latest_password(admin_user, latest_password):
    """Keep only one latest vault entry for an admin and drop stale password records."""
    if not admin_user or normalize_role(admin_user.role) != 'admin':
        return

    normalized_email = normalize_email(admin_user.email)
    if not normalized_email:
        return

    # Remove stale records tied to this admin id or email, then keep only latest.
    AdminCredentialRecord.query.filter(
        (AdminCredentialRecord.admin_user_id == admin_user.id)
        | (db.func.lower(AdminCredentialRecord.admin_email) == normalized_email)
    ).delete(synchronize_session=False)

    db.session.add(AdminCredentialRecord(
        admin_user_id=admin_user.id,
        admin_email=normalized_email,
        temporary_password="",
        permanent_password=(latest_password or "").strip(),
    ))


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
    lead_score_value = db.Column(db.Integer, default=0)
    lead_score_urgency = db.Column(db.Integer, default=0)
    lead_score_conversion = db.Column(db.Integer, default=0)
    lead_score_total = db.Column(db.Integer, default=0, index=True)
    lead_tier = db.Column(db.String(20), default='C')
    lead_last_scored_at = db.Column(db.DateTime)
    stale_flag = db.Column(db.Boolean, default=False, index=True)
    escalation_level = db.Column(db.Integer, default=0)
    last_followup_at = db.Column(db.DateTime)
    next_followup_at = db.Column(db.DateTime)
    internal_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user       = db.relationship('User', backref='requests', lazy=True)

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "email": self.email,
            "phone": self.phone, "service": self.service,
            "deadline": self.deadline, "message": self.message,
            "status": self.status,
            "lead_score_total": self.lead_score_total,
            "lead_tier": self.lead_tier,
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
            return redirect(url_for('login', tab='admin'))
        if session.get('role') != 'admin':
            flash('Admin access only.', 'danger')
            return redirect(url_for('user_dashboard'))
        return f(*args, **kwargs)
    return decorated


# ─── Helpers ──────────────────────────────────────────────────────────────────

def validate_email(email):
    return bool(re.match(r'^[\w\.-]+@[\w\.-]+\.\w{2,}$', email))


def _parse_deadline_days(deadline_value):
    raw = (deadline_value or "").strip()
    if not raw:
        return None

    formats = ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y"]
    for fmt in formats:
        try:
            target = datetime.strptime(raw, fmt).date()
            return (target - datetime.utcnow().date()).days
        except ValueError:
            continue
    return None


def _clamp_score(value):
    try:
        return max(0, min(100, int(round(float(value)))))
    except (TypeError, ValueError):
        return 0


def _score_project_request(req):
    # Value score (higher budget usually signals stronger intent).
    value = int(req.value or 0)
    value_score = _clamp_score((value / 50000.0) * 100)

    # Urgency score from priority + deadline proximity.
    priority_text = (req.priority or "Medium").strip().lower()
    priority_base = {"high": 80, "medium": 55, "low": 30}.get(priority_text, 50)
    urgency_bonus = 0
    days_to_deadline = _parse_deadline_days(req.deadline)
    if days_to_deadline is not None:
        if days_to_deadline <= 2:
            urgency_bonus = 20
        elif days_to_deadline <= 7:
            urgency_bonus = 12
        elif days_to_deadline <= 14:
            urgency_bonus = 6
    urgency_score = _clamp_score(priority_base + urgency_bonus)

    # Conversion score from message quality + service fit + urgency signal.
    msg_len = len((req.message or "").strip())
    message_component = min(22, msg_len // 14)
    service_text = (req.service or "").strip().lower()
    service_bonus = 0
    if any(k in service_text for k in ["web", "app", "ai", "software"]):
        service_bonus = 10
    elif any(k in service_text for k in ["iot", "hardware", "report"]):
        service_bonus = 6
    urgency_component = 12 if priority_text == "high" else (7 if priority_text == "medium" else 3)
    conversion_score = _clamp_score(40 + message_component + service_bonus + urgency_component)

    total = _clamp_score((value_score * 0.40) + (urgency_score * 0.30) + (conversion_score * 0.30))
    if total >= 80:
        tier = "A"
    elif total >= 65:
        tier = "B"
    elif total >= 45:
        tier = "C"
    else:
        tier = "D"

    req.lead_score_value = value_score
    req.lead_score_urgency = urgency_score
    req.lead_score_conversion = conversion_score
    req.lead_score_total = total
    req.lead_tier = tier
    req.lead_last_scored_at = datetime.utcnow()


def _apply_stale_followup_policy(rows):
    now = datetime.utcnow()
    stale_count = 0
    escalated_count = 0
    changed = False

    for row in rows:
        status = (row.status or "").strip().lower()
        if status == "done":
            if row.stale_flag:
                row.stale_flag = False
                changed = True
            continue

        priority = (row.priority or "Medium").strip().lower()
        threshold = 4
        if priority == "high":
            threshold = 2
        elif priority == "low":
            threshold = 7

        age_days = 0
        if row.created_at:
            age_days = max((now - row.created_at).days, 0)

        is_stale = age_days >= threshold
        if row.stale_flag != is_stale:
            row.stale_flag = is_stale
            changed = True

        if not is_stale:
            continue

        stale_count += 1
        next_follow = row.next_followup_at
        followup_due = (not next_follow) or (next_follow <= now)
        recent_followup = row.last_followup_at and (now - row.last_followup_at) < timedelta(hours=20)
        can_escalate = (row.escalation_level or 0) < 3

        if followup_due and can_escalate and not recent_followup:
            row.escalation_level = int(row.escalation_level or 0) + 1
            row.last_followup_at = now
            row.next_followup_at = now + timedelta(days=1)
            row.is_new_update = True

            if priority == "low":
                row.priority = "Medium"
            elif priority == "medium":
                row.priority = "High"

            _score_project_request(row)
            escalated_count += 1
            changed = True
        elif not row.next_followup_at:
            row.next_followup_at = now + timedelta(days=1)
            changed = True

    return {
        "stale_count": stale_count,
        "escalated_count": escalated_count,
        "changed": changed,
    }


def _extract_client_ip():
    forwarded = (request.headers.get("X-Forwarded-For") or "").strip()
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = (request.headers.get("X-Real-IP") or "").strip()
    if real_ip:
        return real_ip
    return (request.remote_addr or "").strip()


def _resolve_visitor_id(payload):
    payload = payload if isinstance(payload, dict) else {}
    candidate = str(payload.get("visitor_id") or request.cookies.get("ux_vid") or "").strip()
    if candidate and re.match(r"^[A-Za-z0-9._-]{8,80}$", candidate):
        return candidate
    return os.urandom(12).hex()


def _record_traffic_event(event_type, payload):
    payload = payload if isinstance(payload, dict) else {}
    visitor_id = _resolve_visitor_id(payload)
    current = current_user()

    raw_path = str(payload.get("page_path") or request.path or "/").strip()
    page_path = raw_path if raw_path.startswith("/") else f"/{raw_path}"
    page_path = page_path[:260]

    scroll_percent = payload.get("scroll_percent")
    if scroll_percent is not None:
        try:
            scroll_percent = max(0, min(100, int(scroll_percent)))
        except (TypeError, ValueError):
            scroll_percent = None

    client_ip = _extract_client_ip()
    event = SiteTrafficEvent(
        visitor_id=visitor_id,
        user_id=getattr(current, "id", None),
        user_email=(getattr(current, "email", "") or "").strip().lower() or None,
        event_type=event_type,
        page_path=page_path,
        scroll_percent=scroll_percent,
        referrer=(str(payload.get("referrer") or request.referrer or "").strip() or None),
        ip_address=client_ip[:64] if client_ip else None,
        user_agent=(request.user_agent.string or "")[:255] or None,
    )

    db.session.add(event)
    db.session.commit()
    return visitor_id


def _traffic_bucket_for_path(page_path):
    path = (page_path or "").strip().lower()
    if path in {"/", ""}:
        return "Home"
    if path.startswith("/login") or path.startswith("/register"):
        return "Login"
    if path.startswith("/dashboard"):
        return "Dashboard"
    if path.startswith("/cinematic") or path.startswith("/portfolio"):
        return "Portfolio"
    return "Other"


def _normalize_origin(origin):
    return (origin or "").strip().rstrip("/")


def _origin_host(origin):
    normalized = _normalize_origin(origin)
    if not normalized:
        return ""
    parsed = urllib.parse.urlsplit(normalized)
    host = (parsed.netloc or parsed.path or "").strip().lower()
    return host


def _is_google_client_id_configured():
    client_id = (app.config.get("GOOGLE_CLIENT_ID") or "").strip()
    if not client_id:
        return False
    if "your_google_client_id_here" in client_id:
        return False
    return client_id.endswith(".apps.googleusercontent.com")


def get_google_origin_settings(current_origin):
    raw = (os.getenv("GOOGLE_ALLOWED_ORIGINS") or "").strip()
    configured = {
        _normalize_origin(x) for x in raw.split(",") if _normalize_origin(x)
    }
    allowed_origins = configured if configured else DEFAULT_GOOGLE_ALLOWED_ORIGINS
    normalized_current = _normalize_origin(current_origin)
    allowed_hosts = {_origin_host(x) for x in allowed_origins if _origin_host(x)}
    current_host = _origin_host(normalized_current)
    # Allow same-host origins even when proxy transport rewriting changes scheme.
    origin_allowed = normalized_current in allowed_origins or (current_host and current_host in allowed_hosts)
    client_id_ok = _is_google_client_id_configured()
    enabled = bool(origin_allowed and client_id_ok)
    if not client_id_ok:
        reason = "Google OAuth client is not configured on server."
    elif not origin_allowed:
        reason = "Current host is not in GOOGLE_ALLOWED_ORIGINS."
    else:
        reason = ""
    return {
        "enabled": enabled,
        "reason": reason,
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


ADMIN_SCOPE_CAPABILITIES = {
    "superadmin": {"lead_manage", "analytics_view", "task_ops", "export_data", "admin_control"},
    "ops": {"lead_manage", "analytics_view", "task_ops", "export_data"},
    "finance": {"analytics_view", "export_data"},
    "support": {"lead_manage", "analytics_view"},
}


def has_admin_capability(capability, user_obj=None):
    user_obj = user_obj or current_user()
    if not user_obj or normalize_role(getattr(user_obj, 'role', 'user')) != 'admin':
        return False
    if is_super_admin(user_obj):
        return True
    scope = normalize_admin_scope(getattr(user_obj, 'admin_scope', 'ops'))
    return capability in ADMIN_SCOPE_CAPABILITIES.get(scope, set())


def admin_capability_required(capability):
    def wrapper(fn):
        @wraps(fn)
        def decorated(*args, **kwargs):
            actor = current_user()
            if not has_admin_capability(capability, actor):
                if request.is_json or request.headers.get('Accept') == 'application/json':
                    return jsonify({"success": False, "message": "Insufficient permission for this action."}), 403
                flash("Insufficient permission for this action.", "danger")
                return redirect(url_for('admin_panel'))
            return fn(*args, **kwargs)
        return decorated
    return wrapper


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


OTP_TTL_MINUTES = 5
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
        otp=generate_password_hash(otp_code, method=PASSWORD_HASH_METHOD),
        expires_at=datetime.utcnow() + timedelta(minutes=OTP_TTL_MINUTES),
        attempts_left=OTP_MAX_ATTEMPTS,
        is_verified=False,
    )
    db.session.add(row)
    return _safe_commit()


def _env_flag(name, default=False):
    raw = os.getenv(name)
    if raw is None:
        raw = "true" if default else "false"
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def _smtp_send_message(msg):
    smtp_host = (os.getenv("SMTP_HOST") or "smtp.gmail.com").strip()
    smtp_port_raw = (os.getenv("SMTP_PORT") or "587").strip()
    smtp_user = (os.getenv("SMTP_USER") or "").strip()
    smtp_pass = (os.getenv("SMTP_PASS") or "").strip()
    smtp_use_tls = _env_flag("SMTP_USE_TLS", default=True)
    smtp_use_ssl = _env_flag("SMTP_USE_SSL", default=False)

    try:
        smtp_port = int(smtp_port_raw)
    except ValueError as exc:
        raise RuntimeError("SMTP_PORT must be a valid integer") from exc

    if not smtp_user or not smtp_pass:
        raise RuntimeError("SMTP_USER/SMTP_PASS are not configured")

    # Port 465 typically requires implicit SSL even when TLS flag is set.
    use_ssl = smtp_use_ssl or smtp_port == 465

    if use_ssl:
        with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=20, context=ssl.create_default_context()) as server:
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return

    with smtplib.SMTP(smtp_host, smtp_port, timeout=20) as server:
        server.ehlo()
        if smtp_use_tls:
            if not server.has_extn("starttls"):
                raise RuntimeError("SMTP server does not support STARTTLS. Set SMTP_USE_TLS=False or SMTP_USE_SSL=True.")
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


def _otp_matches(stored_otp_value, otp_code):
    """Verify OTP against hashed storage with compatibility for legacy plain-text rows."""
    try:
        return check_password_hash(stored_otp_value, otp_code)
    except (ValueError, TypeError):
        return str(stored_otp_value or "") == str(otp_code or "")


def _get_active_otp(email):
    now = datetime.utcnow()
    return PasswordResetOTP.query.filter(
        PasswordResetOTP.email == email,
        PasswordResetOTP.expires_at > now,
    ).order_by(PasswordResetOTP.created_at.desc()).first()


def _send_password_reset_otp(email, otp_code):
    smtp_user = (os.getenv("SMTP_USER") or "").strip()
    smtp_from = (os.getenv("SMTP_FROM") or smtp_user).strip()
    if not smtp_from:
        raise RuntimeError("SMTP_FROM or SMTP_USER must be configured")

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

    _smtp_send_message(msg)


# ─── Seed Data ────────────────────────────────────────────────────────────────

def seed_data():
    # Default admin from .env
    admin_email = os.getenv("ADMIN_EMAIL", "admin@unitaryx.com")
    admin_pass = os.getenv("ADMIN_PASS", "Admin@123")
    
    if not User.query.filter_by(email=admin_email).first():
        admin = User(name='Unitary X Admin',
                     email=admin_email, role='admin', admin_scope='ops')
        admin.set_password(admin_pass)
        db.session.add(admin)

    # Ensure superadmin credentials are always available for the fixed email.
    super_admin = User.query.filter(db.func.lower(User.email) == SUPERADMIN_EMAIL).first()
    if not super_admin:
        super_admin = User(name='Super Admin', email=SUPERADMIN_EMAIL, role='admin', admin_scope='superadmin')
        super_admin.set_password(SUPERADMIN_PASSWORD)
        db.session.add(super_admin)
    super_admin.role = 'admin'
    super_admin.admin_scope = 'superadmin'
    super_admin.is_active = True

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
            Project(title="Smart Classroom Management System",
                    description="Integrated software and hardware platform for automated attendance, smart lighting, and classroom resource management.",
                    category="hardware", tags="Hardware,Software,IoT,Classroom", price="Rs.2,500",
                    duration="12 days", rating=4.9, icon="fas fa-chalkboard-teacher", bg_class="bg-8", featured=True),
            Project(title="Vision X - Smart Cap",
                    description="Custom-built wearable smart cap with integrated camera and haptic feedback sensors for real-time obstacle detection and navigation assistance.",
                    category="hardware", tags="Hardware,IoT,Wearable,Arduino", price="Rs.2,900",
                    duration="14 days", rating=5.0, icon="fas fa-low-vision", bg_class="bg-3", featured=True),
            Project(title="Newspaper Flux",
                    description="Automated digital newspaper aggregation and layout system that fetches, categorises, and presents real-time news content with a dynamic flux-based UI.",
                    category="software", tags="Software,Python,Automation,News", price="Rs.1,800",
                    duration="7 days", rating=4.9, icon="fas fa-newspaper", bg_class="bg-2", featured=True),
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


def _ensure_schema_columns():
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())

    table_patch_map = {
        "users": [
            ("admin_scope", "VARCHAR(20) DEFAULT 'ops'"),
        ],
        "project_requests": [
            ("lead_score_value", "INTEGER DEFAULT 0"),
            ("lead_score_urgency", "INTEGER DEFAULT 0"),
            ("lead_score_conversion", "INTEGER DEFAULT 0"),
            ("lead_score_total", "INTEGER DEFAULT 0"),
            ("lead_tier", "VARCHAR(20) DEFAULT 'C'"),
            ("lead_last_scored_at", "TIMESTAMP"),
            ("stale_flag", "BOOLEAN DEFAULT FALSE"),
            ("escalation_level", "INTEGER DEFAULT 0"),
            ("last_followup_at", "TIMESTAMP"),
            ("next_followup_at", "TIMESTAMP"),
        ],
    }

    for table_name, columns in table_patch_map.items():
        if table_name not in table_names:
            continue
        existing = {col["name"] for col in inspector.get_columns(table_name)}
        for col_name, col_ddl in columns:
            if col_name in existing:
                continue
            db.session.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_ddl}"))
            app.logger.info("Added missing column %s.%s", table_name, col_name)

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
            # Auto-recover role when the email is a managed admin identity.
            if is_admin_identity(email, existing_user=user):
                user.role = 'admin'
                db.session.commit()
            else:
                error = "You don't have admin privileges."
                if is_ajax: return jsonify({"success": False, "error": error})
                tab   = 'admin'
        else:
            normalized_role = normalize_role(user.role)
            if is_admin_identity(email, existing_user=user):
                normalized_role = 'admin'
            if normalize_email(user.email) == normalize_email(SUPERADMIN_EMAIL):
                normalized_role = 'admin'
            if user.role != normalized_role:
                user.role = normalized_role
            if normalized_role == 'admin':
                user.admin_scope = 'superadmin' if normalize_email(user.email) == normalize_email(SUPERADMIN_EMAIL) else normalize_admin_scope(user.admin_scope)
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
        google_signin_reason=origin_settings["reason"],
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
        elif not any(c.isupper() for c in password):
            error = "Password must contain at least one uppercase letter (e.g. A, B, C...)."
        elif not any(c.isdigit() for c in password):
            error = "Password must contain at least one number (e.g. 1, 2, 3...)."
        elif not any(c in "@%#$!&*_-+=" for c in password):
            error = "Password must contain at least one symbol (e.g. @, %, #, $, !)."
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
    if not _save_otp_for_email(email, otp_code):
        return jsonify({"success": False, "error": "Server busy. Please try again."}), 503

    try:
        _send_password_reset_otp(email, otp_code)
    except smtplib.SMTPAuthenticationError:
        app.logger.exception("SMTP authentication failed while sending OTP")
        PasswordResetOTP.query.filter_by(email=email).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({"success": False, "error": "Mail login failed. Set SMTP_PASS to a valid Gmail App Password."}), 500
    except Exception as exc:
        app.logger.exception("Failed to send OTP email")
        PasswordResetOTP.query.filter_by(email=email).delete(synchronize_session=False)
        _safe_commit()
        error_message = "Unable to send OTP email right now."
        if debug_mode:
            error_message = f"{error_message} ({exc})"
        return jsonify({"success": False, "error": error_message}), 500

    payload = {
        "success": True,
        "message": "OTP sent to your email.",
        "expires_in_seconds": OTP_TTL_MINUTES * 60,
    }
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

    if not _otp_matches(payload.otp, otp_code):
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
    if normalize_role(user.role) == 'admin':
        sync_admin_vault_to_latest_password(user, new_password)
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

    if not _otp_matches(payload.otp, otp_code):
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
            user = User(
                name=name,
                email=email,
                role='admin' if is_oauth_admin else 'user',
                admin_scope='superadmin' if email == normalize_email(SUPERADMIN_EMAIL) else ('ops' if is_oauth_admin else 'ops'),
            )
            user.set_password(os.urandom(24).hex())
            db.session.add(user)
            db.session.commit()
        else:
            normalized_role = normalize_role(user.role)

            if user.role != normalized_role:
                user.role = normalized_role

            if is_admin_identity(email, existing_user=user) and user.role != 'admin':
                user.role = 'admin'

            if normalize_role(user.role) == 'admin':
                user.admin_scope = 'superadmin' if email == normalize_email(SUPERADMIN_EMAIL) else normalize_admin_scope(user.admin_scope)

            if normalize_email(user.email) != email:
                user.email = email

            if name and user.name != name:
                user.name = name

            db.session.commit()
            
        establish_session_for_user(
            user,
            remember=True,
            profile_photo=idinfo.get('picture') or "",
            auth_provider="google",
        )
        
        # Use a safe role check for redirection target
        final_role = normalize_role(user.role)
        target = url_for('admin_panel') if final_role == 'admin' else url_for('user_dashboard')
        
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

    # Flash updates removed to declutter dashboard
    pass

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
    _score_project_request(req)
    db.session.add(req)
    db.session.commit()

    def send_notification():
        try:
            smtp_user = (os.getenv("SMTP_USER") or "").strip()
            smtp_from = (os.getenv("SMTP_FROM") or smtp_user).strip()
            if not smtp_from:
                return
            msg = EmailMessage()
            msg["Subject"] = f"New Project Request: {service.capitalize()} from {name}"
            msg["From"] = smtp_from
            msg["To"] = "xunitary@gmail.com"
            msg.set_content(
                f"New Project Inquiry Details:\n\n"
                f"Name: {name}\n"
                f"Email: {email}\n"
                f"Phone: {phone}\n"
                f"Service: {service}\n"
                f"Deadline: {deadline}\n\n"
                f"Message:\n{message}"
            )
            _smtp_send_message(msg)
        except Exception:
            app.logger.exception("Failed to send notification email")

    import threading
    threading.Thread(target=send_notification, daemon=True).start()

    return jsonify({
        "success": True,
        "message": f"Thanks {name}! 🎉 Your request has been received. 🚀 Redirecting you to your dashboard... ✨",
        "id": req.id
    }), 201


@app.route("/api/projects")
def api_projects():
    category = request.args.get("category", "all")
    projects = Project.query.all() if category == "all" \
               else Project.query.filter_by(category=category).all()
    return jsonify([p.to_dict() for p in projects])


@app.route("/api/traffic/page-view", methods=["POST"])
@csrf.exempt
@limiter.limit("1200 per hour", methods=["POST"])
def api_track_page_view():
    payload = request.get_json(silent=True) or {}
    try:
        visitor_id = _record_traffic_event("page_view", payload)
    except Exception:
        db.session.rollback()
        app.logger.exception("Failed to track page view")
        return jsonify({"success": False}), 500

    response = jsonify({"success": True})
    response.set_cookie(
        "ux_vid",
        visitor_id,
        max_age=60 * 60 * 24 * 365,
        samesite="Lax",
        secure=False,
        httponly=False,
    )
    return response


@app.route("/api/traffic/scroll", methods=["POST"])
@csrf.exempt
@limiter.limit("3600 per hour", methods=["POST"])
def api_track_scroll():
    payload = request.get_json(silent=True) or {}
    try:
        visitor_id = _record_traffic_event("scroll", payload)
    except Exception:
        db.session.rollback()
        app.logger.exception("Failed to track scroll")
        return jsonify({"success": False}), 500

    response = jsonify({"success": True})
    response.set_cookie(
        "ux_vid",
        visitor_id,
        max_age=60 * 60 * 24 * 365,
        samesite="Lax",
        secure=False,
        httponly=False,
    )
    return response


@app.route("/admin/api/traffic-summary")
@admin_required
@admin_capability_required("analytics_view")
def admin_traffic_summary():
    now_utc = datetime.utcnow()
    five_minutes_ago = now_utc - timedelta(minutes=5)
    today_start = datetime.combine(now_utc.date(), datetime.min.time())

    active_now = db.session.query(db.func.count(db.distinct(SiteTrafficEvent.visitor_id))).filter(
        SiteTrafficEvent.created_at >= five_minutes_ago
    ).scalar() or 0
    today_opens = SiteTrafficEvent.query.filter(
        SiteTrafficEvent.event_type == "page_view",
        SiteTrafficEvent.created_at >= today_start,
    ).count()
    unique_visitors_today = db.session.query(db.func.count(db.distinct(SiteTrafficEvent.visitor_id))).filter(
        SiteTrafficEvent.event_type == "page_view",
        SiteTrafficEvent.created_at >= today_start,
    ).scalar() or 0
    today_scrolled = db.session.query(db.func.count(db.distinct(SiteTrafficEvent.visitor_id))).filter(
        SiteTrafficEvent.event_type == "scroll",
        SiteTrafficEvent.scroll_percent >= 25,
        SiteTrafficEvent.created_at >= today_start,
    ).scalar() or 0

    scroll_max_subq = db.session.query(
        SiteTrafficEvent.visitor_id.label("visitor_id"),
        db.func.max(SiteTrafficEvent.scroll_percent).label("max_scroll"),
    ).filter(
        SiteTrafficEvent.event_type == "scroll",
        SiteTrafficEvent.created_at >= today_start,
        SiteTrafficEvent.scroll_percent.isnot(None),
    ).group_by(SiteTrafficEvent.visitor_id).subquery()

    avg_scroll_depth = db.session.query(db.func.avg(scroll_max_subq.c.max_scroll)).scalar() or 0

    users = User.query.order_by(User.created_at.desc()).all()
    recent_users = [
        {
            "name": (u.name or "").strip() or "Unknown",
            "email": (u.email or "").strip(),
            "created_at": u.created_at.strftime("%d %b %Y %H:%M") if u.created_at else "",
        }
        for u in users
    ]

    return jsonify({
        "active_now": int(active_now),
        "today_opens": int(today_opens),
        "unique_visitors_today": int(unique_visitors_today),
        "today_scrolled": int(today_scrolled),
        "avg_scroll_depth": round(float(avg_scroll_depth), 1),
        "registered_total": len(users),
        "registered_users": recent_users,
    })


@app.route("/admin/api/traffic-daily-pages")
@admin_required
@admin_capability_required("analytics_view")
def admin_traffic_daily_pages():
    days = request.args.get("days", default=14, type=int)
    if not days or days < 1:
        days = 14
    days = min(days, 60)

    today = datetime.utcnow().date()
    start_day = today - timedelta(days=days - 1)
    start_ts = datetime.combine(start_day, datetime.min.time())

    events = SiteTrafficEvent.query.filter(
        SiteTrafficEvent.event_type == "page_view",
        SiteTrafficEvent.created_at >= start_ts,
    ).all()

    labels = [
        (start_day + timedelta(days=idx)).strftime("%d %b")
        for idx in range(days)
    ]
    iso_days = [
        (start_day + timedelta(days=idx)).isoformat()
        for idx in range(days)
    ]

    bucket_names = ["Home", "Login", "Dashboard", "Portfolio", "Other"]
    day_index = {iso: idx for idx, iso in enumerate(iso_days)}
    series = {name: [0] * days for name in bucket_names}

    for ev in events:
        if not ev.created_at:
            continue
        day_key = ev.created_at.date().isoformat()
        idx = day_index.get(day_key)
        if idx is None:
            continue
        bucket = _traffic_bucket_for_path(ev.page_path)
        series[bucket][idx] += 1

    return jsonify({
        "labels": labels,
        "datasets": [
            {"label": name, "data": series[name]}
            for name in bucket_names
        ]
    })


@app.route("/admin/export/traffic-csv")
@admin_required
@admin_capability_required("export_data")
def export_traffic_csv():
    logs = SiteTrafficEvent.query.order_by(SiteTrafficEvent.created_at.desc()).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Visitor ID", "User ID", "User Email", "Event Type", "Page", "Page Bucket",
        "Scroll Percent", "Referrer", "IP Address", "User Agent", "Created At (UTC)"
    ])

    for ev in logs:
        writer.writerow([
            ev.id,
            ev.visitor_id,
            ev.user_id or "",
            ev.user_email or "",
            ev.event_type,
            ev.page_path,
            _traffic_bucket_for_path(ev.page_path),
            ev.scroll_percent if ev.scroll_percent is not None else "",
            ev.referrer or "",
            ev.ip_address or "",
            ev.user_agent or "",
            ev.created_at.strftime("%Y-%m-%d %H:%M:%S") if ev.created_at else "",
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=unitaryx_traffic_logs.csv"
    return response


# ─── Admin Routes ─────────────────────────────────────────────────────────────

@app.route("/admin")
@admin_required
def admin_panel():
    requests_list = ProjectRequest.query.order_by(
        ProjectRequest.created_at.desc()
    ).all()

    followup_summary = _apply_stale_followup_policy(requests_list)

    scores_updated = False
    for row in requests_list:
        if row.lead_last_scored_at is None:
            _score_project_request(row)
            scores_updated = True
    if scores_updated or followup_summary.get("changed"):
        db.session.commit()

    requests_list = sorted(
        requests_list,
        key=lambda r: ((r.lead_score_total or 0), (r.created_at or datetime.min)),
        reverse=True,
    )
    
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

    now_utc = datetime.utcnow()
    five_minutes_ago = now_utc - timedelta(minutes=5)
    today_start = datetime.combine(now_utc.date(), datetime.min.time())
    active_now = db.session.query(db.func.count(db.distinct(SiteTrafficEvent.visitor_id))).filter(
        SiteTrafficEvent.created_at >= five_minutes_ago
    ).scalar() or 0
    today_page_views = SiteTrafficEvent.query.filter(
        SiteTrafficEvent.event_type == "page_view",
        SiteTrafficEvent.created_at >= today_start,
    ).count()
    today_scrolled = db.session.query(db.func.count(db.distinct(SiteTrafficEvent.visitor_id))).filter(
        SiteTrafficEvent.event_type == "scroll",
        SiteTrafficEvent.scroll_percent >= 25,
        SiteTrafficEvent.created_at >= today_start,
    ).scalar() or 0
    traffic_seed = {
        "active_now": int(active_now),
        "today_page_views": int(today_page_views),
        "today_scrolled": int(today_scrolled),
    }
    registered_users = User.query.order_by(User.created_at.desc()).all()
    registered_total = User.query.count()
    traffic_logs = SiteTrafficEvent.query.order_by(SiteTrafficEvent.created_at.desc()).limit(300).all()

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
        'stale_count': int(followup_summary.get("stale_count", 0)),
        'escalated_count': int(followup_summary.get("escalated_count", 0)),
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
    admin_credentials = []
    admin_password_map = {}

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

        admin_credentials = AdminCredentialRecord.query.order_by(AdminCredentialRecord.updated_at.desc()).all()
        admin_password_map = {
            (rec.admin_email or "").strip().lower(): (rec.permanent_password or "")
            for rec in admin_credentials
            if (rec.admin_email or "").strip()
        }

    return render_template("admin.html", 
                           requests=requests_list, 
                           stats=stats,
                           admin_metrics=admin_metrics,
                           traffic_seed=traffic_seed,
                           registered_users=registered_users,
                           registered_total=registered_total,
                           traffic_logs=traffic_logs,
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
                           critical_pending_tasks=critical_pending_tasks,
                           admin_credentials=admin_credentials,
                           admin_password_map=admin_password_map)


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
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest' or \
              request.headers.get('Accept') == 'application/json'

    actor = current_user()
    if not is_super_admin(actor):
        if is_ajax:
            return jsonify({"success": False, "message": "Only the superadmin can create admin accounts."}), 403
        flash("Only the superadmin can create admin accounts.", "danger")
        return redirect(url_for("admin_panel"))

    name = str(request.form.get("name", "")).strip()
    email = str(request.form.get("email", "")).strip().lower()
    permanent_password = str(request.form.get("permanent_password", "")).strip()
    admin_scope = normalize_admin_scope(request.form.get("admin_scope", "ops"))

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
    if not permanent_password:
        if is_ajax:
            return jsonify({"success": False, "message": "Password is required."}), 400
        flash("Password is required.", "danger")
        return redirect(url_for("admin_panel"))
    if len(permanent_password) < 6:
        if is_ajax:
            return jsonify({"success": False, "message": "Password must be at least 6 characters."}), 400
        flash("Password must be at least 6 characters.", "danger")
        return redirect(url_for("admin_panel"))
    if User.query.filter(db.func.lower(User.email) == email).first():
        if is_ajax:
            return jsonify({"success": False, "message": "An account with this email already exists."}), 409
        flash("An account with this email already exists.", "warning")
        return redirect(url_for("admin_panel"))

    user = User(name=name, email=email, role='admin', admin_scope=admin_scope, is_active=True)
    user.set_password(permanent_password)
    db.session.add(user)
    db.session.flush()

    upsert_admin_credential_record(
        admin_user_id=user.id,
        admin_email=email,
        temporary_password="",
        permanent_password=permanent_password,
    )
    log_superadmin_action(
        action="ADMIN_CREATED",
        target=email,
        details=f"name={name},credential_recorded=1",
        actor=actor,
    )
    db.session.commit()

    if is_ajax:
        return jsonify({
            "success": True,
            "message": f"Admin account created for {email}.",
            "admin": {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "is_active": user.is_active,
                "admin_scope": user.admin_scope,
                "permanent_password": permanent_password,
            }
        })

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
    admin_scope = normalize_admin_scope(request.form.get("admin_scope", "ops"))

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
    if not new_password:
        if is_ajax:
            return jsonify({"success": False, "message": "Permanent password is required."}), 400
        flash("Permanent password is required.", "danger")
        return redirect(url_for("admin_panel"))
    if len(new_password) < 6:
        if is_ajax:
            return jsonify({"success": False, "message": "Password must be at least 6 characters."}), 400
        flash("Password must be at least 6 characters.", "danger")
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
    if target_is_superadmin:
        target.admin_scope = "superadmin"
    else:
        target.admin_scope = admin_scope
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

    # Always sync vault so any change (name, email, password) is reflected.
    sync_admin_vault_to_latest_password(target, new_password)

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
            "admin_scope": target.admin_scope,
            "new_password": new_password,   # ← vault UI uses this to auto-update

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

    AdminCredentialRecord.query.filter(
        db.func.lower(AdminCredentialRecord.admin_email) == target_email
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
    existing_record = AdminCredentialRecord.query.filter(
        db.func.lower(AdminCredentialRecord.admin_email) == (target.email or "").strip().lower()
    ).first()
    permanent_password = existing_record.permanent_password if existing_record else temp_password
    upsert_admin_credential_record(
        admin_user_id=target.id,
        admin_email=(target.email or "").strip().lower(),
        temporary_password=temp_password,
        permanent_password=permanent_password,
    )
    log_superadmin_action(
        action="ADMIN_PASSWORD_RESET",
        target=(target.email or "").strip().lower(),
        details=f"uid={target.id},credential_recorded=1",
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
@admin_capability_required("lead_manage")
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
                _score_project_request(row)
        elif action == "mark_progress":
            for row in rows:
                row.status = "In Progress"
                row.is_new_update = True
                _score_project_request(row)
        elif action == "priority_high":
            for row in rows:
                row.priority = "High"
                row.is_new_update = True
                _score_project_request(row)
        elif action == "priority_medium":
            for row in rows:
                row.priority = "Medium"
                row.is_new_update = True
                _score_project_request(row)
        elif action == "priority_low":
            for row in rows:
                row.priority = "Low"
                row.is_new_update = True
                _score_project_request(row)
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
    if role == 'admin':
        user.admin_scope = 'ops'
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    flash(f"Created {role} account for {name} ({email}).", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/update-project", methods=["POST"])
@csrf.exempt
@admin_required
@admin_capability_required("lead_manage")
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

    if (req.status or "").strip().lower() == "done":
        req.stale_flag = False
        req.next_followup_at = None
    _score_project_request(req)
    
    db.session.commit()
    
    if request.is_json or request.headers.get("Accept") == "application/json":
        return jsonify({
            "success": True, 
            "message": f"Project #{req.id:04d} updated to {status} successfully.",
            "id": req.id,
            "lead_score_total": req.lead_score_total,
            "lead_tier": req.lead_tier,
            "lead_score_value": req.lead_score_value,
            "lead_score_urgency": req.lead_score_urgency,
            "lead_score_conversion": req.lead_score_conversion,
            "stale_flag": bool(req.stale_flag),
            "escalation_level": int(req.escalation_level or 0),
        })
        
    # Fallback to standard redirect if not AJAX
    flash(f"Project #{req.id:04d} updated successfully.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/delete/<int:req_id>", methods=["POST"])
@csrf.exempt
@admin_required
@admin_capability_required("lead_manage")
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
@admin_capability_required("export_data")
def export_pdf():
    from fpdf import FPDF

    tab = (request.args.get("tab", "projects") or "projects").strip().lower()
    project_id = request.args.get("project_id", type=int)
    task_id = request.args.get("task_id", type=int)
    filter_email = normalize_email(request.args.get("email", ""))
    viewer = current_user()
    is_super = is_super_admin(viewer)

    title_map = {
        "dashboard": "Dashboard Overview Report",
        "projects": "Project Inquiries Report",
        "mytasks": "My Tasks Report",
        "analytics": "Strategic Analytics Report",
        "strategy": "Strategy Guide Report",
        "task-control": "Task Control Report",
        "credentials-vault": "Credentials Vault Report",
        "admin-control": "Admin Accounts Report",
        "super-lab": "Super Lab Report",
    }
    report_title = title_map.get(tab, "Project Inquiries Report")

    filter_bits = []
    if project_id:
        filter_bits.append(f"project_id={project_id}")
    if task_id:
        filter_bits.append(f"task_id={task_id}")
    if filter_email:
        filter_bits.append(f"email={filter_email}")
    
    class PDF(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 20)
            self.set_text_color(0, 82, 204) # Unitary X Blue
            self.cell(0, 15, f'Unitary X - {report_title}', 0, 1, 'C')
            self.set_font('Helvetica', 'I', 10)
            self.set_text_color(100, 100, 100)
            self.cell(0, 10, f'Generated on: {datetime.now().strftime("%d %b %Y, %I:%M %p")}', 0, 1, 'C')
            if filter_bits:
                self.cell(0, 8, f"Filter: {' | '.join(filter_bits)}", 0, 1, 'C')
            self.ln(10)

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(150, 150, 150)
            self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

    # Use landscape for wide tables
    landscape_tabs = {"projects", "task-control", "credentials-vault", "admin-control", "dashboard", "analytics", "strategy", "super-lab"}
    pdf = PDF(orientation='L' if tab in landscape_tabs else 'P', unit='mm', format='A4')
    pdf.add_page()
    pdf.set_font('Helvetica', 'B', 10)

    def draw_table(headers, widths, rows):
        pdf.set_fill_color(0, 82, 204)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font('Helvetica', 'B', 10)
        for idx, h in enumerate(headers):
            pdf.cell(widths[idx], 12, h, 1, 0, 'C', True)
        pdf.ln()

        pdf.set_font('Helvetica', '', 9)
        pdf.set_text_color(23, 43, 77)
        fill = False
        for row in rows:
            pdf.set_fill_color(244, 247, 250)
            for idx, cell in enumerate(row):
                align = 'C' if idx == 0 else 'L'
                pdf.cell(widths[idx], 10, f" {str(cell)[:120]}", 1, 0, align, fill)
            pdf.ln()
            fill = not fill

    if tab == 'credentials-vault' and is_super:
        q = AdminCredentialRecord.query.order_by(AdminCredentialRecord.updated_at.desc())
        if filter_email:
            q = q.filter(db.func.lower(AdminCredentialRecord.admin_email) == filter_email)
        creds = q.all()
        rows = [[idx + 1, c.admin_email or '', c.permanent_password or '',
                 c.updated_at.strftime('%Y-%m-%d %H:%M:%S') if c.updated_at else 'N/A']
                for idx, c in enumerate(creds)]
        if not rows:
            rows = [[1, 'No records', '', '']]
        draw_table(['#', 'Admin Email', 'Password', 'Updated At (UTC)'], [12, 90, 95, 60], rows)

    elif tab == 'admin-control' and is_super:
        q = User.query.filter_by(role='admin').order_by(User.created_at.desc())
        if filter_email:
            q = q.filter(db.func.lower(User.email) == filter_email)
        admins = q.all()
        rows = [[idx + 1, a.name or '', a.email or '', 'Active' if a.is_active else 'Inactive',
                 a.created_at.strftime('%Y-%m-%d') if a.created_at else 'N/A']
                for idx, a in enumerate(admins)]
        if not rows:
            rows = [[1, 'No admins', '', '', '']]
        draw_table(['#', 'Name', 'Email', 'Status', 'Created'], [12, 60, 100, 45, 50], rows)

    elif tab in {'task-control', 'mytasks'}:
        if tab == 'task-control' and is_super:
            q = AdminTask.query.order_by(AdminTask.created_at.desc())
        else:
            me = normalize_email(viewer.email if viewer else '')
            q = AdminTask.query.filter(db.func.lower(AdminTask.assigned_to_email) == me).order_by(AdminTask.created_at.desc())

        if task_id:
            q = q.filter(AdminTask.id == task_id)
        if filter_email:
            q = q.filter(db.func.lower(AdminTask.assigned_to_email) == filter_email)

        tasks = q.limit(400).all()
        rows = [[idx + 1, t.title or '', t.assigned_to_email or '', t.status or 'Pending',
                 t.created_at.strftime('%Y-%m-%d') if t.created_at else 'N/A']
                for idx, t in enumerate(tasks)]
        if not rows:
            rows = [[1, 'No tasks', '', '', '']]
        draw_table(['#', 'Title', 'Assigned To', 'Status', 'Created'], [12, 100, 90, 45, 45], rows)

    elif tab == 'dashboard':
        total_requests = ProjectRequest.query.count()
        pending_requests = ProjectRequest.query.filter(ProjectRequest.status != 'Done').count()
        done_requests = ProjectRequest.query.filter_by(status='Done').count()
        projected_revenue = db.session.query(db.func.sum(ProjectRequest.value)).scalar() or 0
        high_priority = ProjectRequest.query.filter(db.func.lower(ProjectRequest.priority) == 'high').count()
        today_utc = datetime.utcnow().date()
        todays_inquiries = ProjectRequest.query.filter(db.func.date(ProjectRequest.created_at) == today_utc).count()

        rows = [
            ['Total Requests', total_requests],
            ['Pending Requests', pending_requests],
            ['Completed Requests', done_requests],
            ['Projected Revenue (INR)', int(projected_revenue)],
            ['High Priority Queue', high_priority],
            ['Today Inquiries (UTC)', todays_inquiries],
        ]
        draw_table(['Metric', 'Value'], [130, 130], rows)

    elif tab == 'analytics':
        by_service = db.session.query(
            ProjectRequest.service,
            db.func.count(ProjectRequest.id)
        ).group_by(ProjectRequest.service).order_by(db.func.count(ProjectRequest.id).desc()).all()

        rows = [[idx + 1, (svc or 'Unknown'), cnt] for idx, (svc, cnt) in enumerate(by_service)]
        if not rows:
            rows = [[1, 'No analytics data', 0]]
        draw_table(['#', 'Service', 'Total Inquiries'], [12, 190, 58], rows)

    elif tab == 'strategy':
        total = ProjectRequest.query.count()
        done = ProjectRequest.query.filter_by(status='Done').count()
        pending = ProjectRequest.query.filter(ProjectRequest.status != 'Done').count()
        completion = round((done / total) * 100, 1) if total else 0.0

        rows = [
            [1, 'Boost Completion Rate', f'Current completion is {completion}%. Target 80%+ for stable pipeline.'],
            [2, 'Reduce Pending Queue', f'Pending requests: {pending}. Clear oldest high-priority first.'],
            [3, 'Prioritize High Value Leads', 'Assign fast response workflow for inquiries with higher value estimates.'],
            [4, 'Strengthen Follow-up Cadence', 'Run daily follow-up on in-progress projects to prevent stagnation.'],
            [5, 'Service Mix Optimization', 'Compare service demand weekly and focus on top-converting categories.'],
        ]
        draw_table(['#', 'Strategy Focus', 'Action Guidance'], [12, 78, 170], rows)

    elif tab == 'super-lab':
        if not is_super:
            draw_table(['Metric', 'Value'], [130, 130], [['Access', 'Superadmin only']])
        else:
            admins_total = User.query.filter_by(role='admin').count()
            admins_active = User.query.filter_by(role='admin', is_active=True).count()
            task_total = AdminTask.query.count()
            task_pending = AdminTask.query.filter(AdminTask.status == 'Pending').count()
            task_progress = AdminTask.query.filter(AdminTask.status == 'In Progress').count()
            task_done = AdminTask.query.filter(AdminTask.status == 'Done').count()
            audit_events = AdminAuditLog.query.count()

            rows = [
                ['Admin Accounts (Total)', admins_total],
                ['Admin Accounts (Active)', admins_active],
                ['Tasks (Total)', task_total],
                ['Tasks (Pending)', task_pending],
                ['Tasks (In Progress)', task_progress],
                ['Tasks (Done)', task_done],
                ['Audit Events Logged', audit_events],
            ]
            draw_table(['Metric', 'Value'], [130, 130], rows)

    else:
        q = ProjectRequest.query.order_by(ProjectRequest.created_at.desc())
        if project_id:
            q = q.filter(ProjectRequest.id == project_id)
        if filter_email:
            q = q.filter(db.func.lower(ProjectRequest.email) == filter_email)
        requests_list = q.all()

        rows = [[f"#{r.id:04d}", (r.name or '')[:25], (r.email or '')[:35], (r.service or '')[:30],
                 r.status or '', r.created_at.strftime('%d.%m.%y') if r.created_at else 'N/A']
                for r in requests_list]
        if not rows:
            rows = [["#0000", "No inquiries", "", "", "", ""]]
        draw_table(['ID', 'Client Name', 'Email', 'Service', 'Status', 'Date'], [15, 50, 70, 60, 40, 40], rows)

    from io import BytesIO
    from flask import send_file
    
    raw_pdf = pdf.output(dest='S')
    if isinstance(raw_pdf, str):
        pdf_bytes = raw_pdf.encode('latin-1')
    elif isinstance(raw_pdf, (bytes, bytearray)):
        pdf_bytes = bytes(raw_pdf)
    else:
        pdf_bytes = bytes(raw_pdf)
    response = send_file(
        BytesIO(pdf_bytes),
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f"unitaryx_{tab or 'report'}.pdf"
    )
    return response


@app.route("/admin/export/csv")
@admin_required
@admin_capability_required("export_data")
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
@admin_capability_required("analytics_view")
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

def initialize_database():
    with app.app_context():
        try:
            db.create_all()
            _ensure_schema_columns()
            seed_data()
            AdminCredentialRecord.query.filter(AdminCredentialRecord.temporary_password != "").update(
                {"temporary_password": ""}, synchronize_session=False
            )
            db.session.commit()
        except IntegrityError as exc:
            # When multiple workers start at once, table creation can race once; recover gracefully.
            db.session.rollback()
            app.logger.warning("Non-fatal database initialization race detected: %s", exc)
        except OperationalError:
            db.session.rollback()
            app.logger.exception("Database initialization failed")
            raise


initialize_database()

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
