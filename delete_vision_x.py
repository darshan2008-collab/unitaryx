"""
Run this once to:
  1. Delete the old merged 'Vision X' project (if it exists)
  2. Add 'Vision X - Smart Cap' and 'Newspaper Flux' as two separate projects
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from freelancer.app import app, db, Project

with app.app_context():
    # --- Remove old Vision X entries ---
    old = Project.query.filter(Project.title.ilike('%Vision X%')).all()
    for p in old:
        print(f"Removing old: [{p.id}] {p.title}")
        db.session.delete(p)

    # --- Remove Newspaper Flux if already added ---
    flux = Project.query.filter(Project.title.ilike('%Newspaper Flux%')).first()
    if flux:
        print(f"Removing duplicate: [{flux.id}] {flux.title}")
        db.session.delete(flux)

    db.session.flush()

    # --- Add Vision X - Smart Cap ---
    db.session.add(Project(
        title="Vision X - Smart Cap",
        description="Custom-built wearable smart cap with integrated camera and haptic feedback sensors for real-time obstacle detection and navigation assistance.",
        category="hardware",
        tags="Hardware,IoT,Wearable,Arduino",
        price="Rs.2,900",
        duration="14 days",
        rating=5.0,
        icon="fas fa-low-vision",
        bg_class="bg-3",
        featured=True,
    ))

    # --- Add Newspaper Flux ---
    db.session.add(Project(
        title="Newspaper Flux",
        description="Automated digital newspaper aggregation and layout system that fetches, categorises, and presents real-time news content with a dynamic flux-based UI.",
        category="software",
        tags="Software,Python,Automation,News",
        price="Rs.1,800",
        duration="7 days",
        rating=4.9,
        icon="fas fa-newspaper",
        bg_class="bg-2",
        featured=True,
    ))

    db.session.commit()
    print("\nDone! Current projects:")
    for p in Project.query.all():
        print(f"  [{p.id}] {p.title}")
