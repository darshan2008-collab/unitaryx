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
import os, re
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

# Security & Config
from flask_talisman import Talisman
from flask_seasurf import SeaSurf
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

load_dotenv()  # Load variables from .env

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "fallback_weak_key_for_dev_only")
app.config['GOOGLE_CLIENT_ID'] = os.getenv("GOOGLE_CLIENT_ID", "your_google_client_id_here.apps.googleusercontent.com")

# ─── Security Configuration ──────────────────────────────────────────────────

# 1. CSRF Protection
csrf = SeaSurf(app)

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
    'img-src': ['\'self\'', 'data:', '*'],
    'media-src': ['\'self\'', 'https://cdn.pixabay.com', 'data:', '*'],
    'script-src': [
        '\'self\'',
        '\'unsafe-inline\'', # Needed for some existing scripts in templates
        'https://cdnjs.cloudflare.com',
        'https://cdn.jsdelivr.net',
    ],
    'style-src': [
        '\'self\'',
        '\'unsafe-inline\'',
        'https://cdnjs.cloudflare.com',
        'https://fonts.googleapis.com',
        'https://use.fontawesome.com',
        'https://cdn.jsdelivr.net',
    ],
}

talisman = Talisman(
    app,
    content_security_policy=csp,
    force_https=False, # Set to True in production with SSL
    session_cookie_secure=False, # Set to True in production with SSL
    session_cookie_http_only=True,
    session_cookie_samesite='Lax'
)

# 3. Rate Limiting (Relaxed for Development)
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["10000 per day", "2000 per hour"],
    storage_uri="memory://"
)

# ─── Database ─────────────────────────────────────────────────────────────────
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'unitaryx_v2.db')}")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
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
        self.password = generate_password_hash(raw)

    def check_password(self, raw):
        return check_password_hash(self.password, raw)


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


def current_user():
    uid = session.get('user_id')
    return User.query.get(uid) if uid else None


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
            Project(title="Vision X - AI System",
                    description="Advanced deep learning software that translates visual environments into descriptive audio feedback for the visually impaired.",
                    category="software", tags="AI,Software,Python", price="Rs.1,800",
                    duration="10 days", rating=5.0, icon="fas fa-low-vision", bg_class="bg-2", featured=True),
            Project(title="Vision X - Smart Glasses",
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


# ─── Auth Routes ──────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])  # Brute force protection
def login():
    if 'user_id' in session:
        return redirect(url_for('admin_panel') if session.get('role') == 'admin'
                        else url_for('user_dashboard'))

    tab   = request.args.get('tab', 'user')  # 'user' or 'admin'
    error = None

    if request.method == "POST":
        login_type = request.form.get('login_type', 'user')
        email      = request.form.get('email', '').strip().lower()
        password   = request.form.get('password', '').strip()
        remember   = request.form.get('remember') == 'on'

        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            error = "Invalid email or password."
            tab   = login_type
        elif not user.is_active:
            error = "Your account has been deactivated. Contact admin."
            tab   = login_type
        elif login_type == 'admin' and user.role != 'admin':
            error = "You don't have admin privileges."
            tab   = 'admin'
        elif login_type == 'user' and user.role == 'admin':
            error = "Please use the Admin login tab."
            tab   = 'user'
        else:
            session.permanent = remember
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['role']    = user.role
            flash(f"Welcome back, {user.name}!", "success")
            if user.role == 'admin':
                return redirect(url_for('admin_panel'))
            return redirect(url_for('user_dashboard'))

    return render_template("login.html", tab=tab, error=error)


@app.route("/register", methods=["GET", "POST"])
@limiter.limit("3 per hour", methods=["POST"])  # Prevent spam accounts
def register():
    if 'user_id' in session:
        return redirect(url_for('user_dashboard'))

    error = None

    if request.method == "POST":
        name     = request.form.get('name', '').strip()
        email    = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        confirm  = request.form.get('confirm', '').strip()

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
        else:
            user = User(name=name, email=email, role='user')
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            session['user_id']   = user.id
            session['user_name'] = user.name
            session['role']      = user.role
            flash(f"Account created! Welcome, {name}!", "success")
            return redirect(url_for('user_dashboard'))

    return render_template("login.html", tab='register', error=error)


@app.route("/google-login", methods=["POST"])
def google_login():
    token = request.json.get("credential") if request.is_json else request.form.get("credential")
    if not token:
        return jsonify({"success": False, "error": "Missing token"}), 400
        
    try:
        idinfo = id_token.verify_oauth2_token(token, google_requests.Request(), app.config['GOOGLE_CLIENT_ID'])
        email = idinfo['email']
        name = idinfo.get('name', email.split("@")[0])
        
        user = User.query.filter_by(email=email).first()
        if not user:
            user = User(name=name, email=email, role='user')
            user.set_password(os.urandom(24).hex())
            db.session.add(user)
            db.session.commit()
            
        session.permanent = True
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['role'] = user.role
        flash(f"Signed in via Google! Welcome, {user.name}!", "success")
        return jsonify({"success": True, "redirect": url_for('user_dashboard')})
        
    except Exception as e:
        return jsonify({"success": False, "error": "Invalid token"}), 400


@app.route("/logout")
def logout():
    name = session.get('user_name', 'User')
    session.clear()
    flash(f"Goodbye, {name}! You have been logged out.", "info")
    return redirect(url_for('login'))


# ─── User Dashboard ───────────────────────────────────────────────────────────

@app.route("/dashboard")
@login_required
def user_dashboard():
    user = current_user()
    my_requests = ProjectRequest.query.filter_by(
        email=user.email
    ).order_by(ProjectRequest.created_at.desc()).all()
    
    # Check for new updates to notify user
    for req in my_requests:
        if req.is_new_update:
            flash(f"Your project #{req.id:04d} has been updated to '{req.status}'!", "success")
            req.is_new_update = False
    db.session.commit()

    return render_template("dashboard.html", user=user,
                           my_requests=my_requests)


# ─── API — Contact Form ───────────────────────────────────────────────────────

@app.route("/api/contact", methods=["POST"])
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

    import urllib.parse
    wa_msg = f"Hello Unitary X Admin! I am {name}. I have just submitted a new project request on your website for {service}. Please review request #{req.id:04d}."
    wa_url = f"https://api.whatsapp.com/send?phone=918754379559&text={urllib.parse.quote(wa_msg)}"

    return jsonify({
        "success": True,
        "message": f"Thanks {name}! Your request has been received. Redirecting you to WhatsApp...",
        "id": req.id,
        "whatsapp_url": wa_url
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
    
    # Simple income calculation (can be improved with actual prices)
    # Let's assume a default value for 'Done' projects for the dashboard aesthetic
    total_valuation = done_req * 15000 

    stats = {
        'total_requests': ProjectRequest.query.count(),
        'pending_requests': ProjectRequest.query.filter(ProjectRequest.status != 'Done').count(),
        'done_requests': ProjectRequest.query.filter_by(status='Done').count(),
        'projected_revenue': db.session.query(db.func.sum(ProjectRequest.value)).scalar() or 0
    }
    
    # Distribution Analysis (Service counts)
    services = ['Web Development', 'Software Projects', 'Hardware & IoT', 'AI & Machine Learning', 'Mobile Apps', 'Reports & Documentation']
    dist_data = [ProjectRequest.query.filter_by(service=s).count() for s in services]

    return render_template("admin.html", 
                           requests=requests_list, 
                           stats=stats,
                           dist_data=dist_data,
                           admin=current_user())


@app.route("/admin/update-project", methods=["POST"])
@admin_required
def update_project():
    # Support both JSON and Form Data for testing/compatibility
    if request.is_json:
        data = request.get_json()
        req_id = data.get("req_id")
        status = data.get("status")
        priority = data.get("priority")
        value = int(data.get("value", 0))
    else:
        req_id = request.form.get("req_id")
        status = request.form.get("status")
        priority = request.form.get("priority")
        value = int(request.form.get("value", 0))

    req = ProjectRequest.query.get_or_404(req_id)
    
    req.status = status
    req.priority = priority
    req.value = value
    req.is_new_update = True  # Notify student via dashboard sync too
    
    db.session.commit()
    
    # Generate WhatsApp URL
    import urllib.parse
    wa_url = None
    if req.phone:
        wa_msg = f"Hello {req.name}! This is an update from Unitary X regarding your project request (#{req.id:04d}).\n\nYour project status is now: *{status}*.\n\nPriority: {priority}\nProjected Value: ₹{value}\n\nLet us know if you have any questions!"
        wa_url = f"https://api.whatsapp.com/send?phone={req.phone}&text={urllib.parse.quote(wa_msg)}"

    if request.is_json or request.headers.get("Accept") == "application/json":
        return jsonify({
            "success": True, 
            "message": f"Project #{req.id:04d} updated to {status} successfully.",
            "whatsapp_url": wa_url,
            "id": req.id
        })
        
    # Fallback to standard redirect if not AJAX
    flash(f"Project #{req.id:04d} updated successfully.", "success")
    return redirect(url_for("admin_panel"))


@app.route("/admin/delete/<int:req_id>", methods=["POST"])
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

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        seed_data()
        print("\n" + "="*58)
        print("  [*]  Unitary X Freelancer Website")
        print("  [*]  Main Site : http://127.0.0.1:5005")
        print("  [*]  Login     : http://127.0.0.1:5005/login")
        print("  [*]  Admin     : http://127.0.0.1:5005/admin")
        print("  [*]  Admin creds: admin@unitaryx.com / Admin@123")
        print("="*58 + "\n")
    app.run(
        debug=os.getenv("DEBUG", "True") == "True",
        port=int(os.getenv("PORT", 5005))
    )
