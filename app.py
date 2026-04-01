from flask import Flask, render_template, request, jsonify, redirect, url_for, abort
from flask_sqlalchemy import SQLAlchemy
import json
import os
import requests # For Telegram
from datetime import datetime
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import threading
import time
from flask import Response

app = Flask(__name__)

@app.route("/favicon.ico")
def favicon():
    return app.send_static_file("favicon.ico")


@app.route("/robots.txt")
def robots():
    content = """User-agent: *
Allow: /
Allow: /static/
Allow: /static/css/
Allow: /static/js/
Allow: /static/images/

Sitemap: https://www.axflo.in/sitemap.xml
"""
    return Response(content, mimetype="text/plain")


@app.route("/sitemap.xml")
def sitemap():
    pages = []

    # Static pages with priorities
    pages.append({"url": "https://www.axflo.in/", "priority": "1.0", "changefreq": "weekly"})
    pages.append({"url": "https://www.axflo.in/products", "priority": "0.9", "changefreq": "weekly"})
    pages.append({"url": "https://www.axflo.in/about", "priority": "0.8", "changefreq": "monthly"})
    pages.append({"url": "https://www.axflo.in/contact", "priority": "0.8", "changefreq": "monthly"})
    pages.append({"url": "https://www.axflo.in/events", "priority": "0.7", "changefreq": "weekly"})
    pages.append({"url": "https://www.axflo.in/request-quote", "priority": "0.8", "changefreq": "monthly"})

    # Dynamic product pages
    products = load_products()
    for product in products:
        if product.get("id"):
            pages.append({
                "url": f"https://www.axflo.in/product/{product['id']}", 
                "priority": "0.7", 
                "changefreq": "monthly"
            })

    # Dynamic event pages
    events = load_events()
    for event in events:
        if event.get("id"):
            pages.append({
                "url": f"https://www.axflo.in/event/{event['id']}", 
                "priority": "0.6", 
                "changefreq": "weekly"
            })

    xml = ['<?xml version="1.0" encoding="UTF-8"?>']
    xml.append('<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">')

    for page in pages:
        xml.append(f"""
  <url>
    <loc>{page['url']}</loc>
    <lastmod>2025-02-09</lastmod>
    <changefreq>{page['changefreq']}</changefreq>
    <priority>{page['priority']}</priority>
  </url>
""")

    xml.append('</urlset>')

    return Response("".join(xml), mimetype="application/xml")


# Disable template caching for development
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

# --- Database Configuration ---
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///local_dev.db') # Fallback for local dev
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Database Models ---
class ContactMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    name = db.Column(db.String(100), nullable=False)
    email_phone = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)

class QuoteRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    name = db.Column(db.String(100), nullable=False)
    contact_info = db.Column(db.String(100), nullable=False)
    company = db.Column(db.String(100), nullable=True)
    selected_products = db.Column(db.Text, nullable=True) # Storing as comma-separated string
    details = db.Column(db.Text, nullable=False)

# --- Helper Functions ---

# Global variables to cache data
_products_cache = None
_events_cache = None
_cache_lock = threading.Lock()

class DataFileHandler(FileSystemEventHandler):
    """Handles file system events for data JSON files"""
    
    def on_modified(self, event):
        if not event.is_directory:
            global _products_cache, _events_cache
            
            if event.src_path.endswith('products.json'):
                print(f"Products file modified: {event.src_path}")
                with _cache_lock:
                    _products_cache = None
                print("Products cache cleared - will reload on next request")
                
            elif event.src_path.endswith('events.json'):
                print(f"Events file modified: {event.src_path}")
                with _cache_lock:
                    _events_cache = None
                print("Events cache cleared - will reload on next request")

def start_file_watcher():
    """Start watching the data JSON files for changes"""
    event_handler = DataFileHandler()
    observer = Observer()
    
    # Watch the data directory
    data_dir = os.path.join(os.path.dirname(__file__), 'data')
    if os.path.exists(data_dir):
        observer.schedule(event_handler, data_dir, recursive=False)
        observer.start()
        print(f"Started watching {data_dir} for JSON file changes")
        return observer
    else:
        print(f"Warning: Data directory {data_dir} not found")
        return None

def load_products():
    """Loads product data from the JSON file with caching."""
    global _products_cache
    
    with _cache_lock:
        if _products_cache is not None:
            return _products_cache
    
    try:
        with open("data/products.json", "r", encoding="utf-8") as f:
            products = json.load(f)
        
        with _cache_lock:
            _products_cache = products
            
        print(f"Loaded {len(products)} products from JSON file")
        return products
    except FileNotFoundError:
        print("ERROR: data/products.json not found.")
        return []
    except json.JSONDecodeError as e:
        print(f"ERROR: data/products.json contains invalid JSON: {e}")
        return []

def load_events():
    """Loads event data from the JSON file with caching."""
    global _events_cache
    
    with _cache_lock:
        if _events_cache is not None:
            return _events_cache
    
    try:
        with open("data/events.json", "r", encoding="utf-8") as f:
            events = json.load(f)
        
        with _cache_lock:
            _events_cache = events
            
        print(f"Loaded {len(events)} events from JSON file")
        return events
    except FileNotFoundError:
        print("ERROR: data/events.json not found.")
        return []
    except json.JSONDecodeError as e:
        print(f"ERROR: data/events.json contains invalid JSON: {e}")
        return []

def get_product_by_id(product_id):
    """Finds a single product by its ID."""
    products = load_products()
    for product in products:
        if product.get("id") is not None and int(product.get("id")) == product_id:
            return product
    return None

def get_event_by_id(event_id):
    """Finds a single event by its ID."""
    events = load_events()
    for event in events:
        if event.get("id") is not None and int(event.get("id")) == event_id:
            # Handle backward compatibility for image field
            if "image" in event and "featured_image" not in event:
                event["featured_image"] = event["image"]
            return event
    return None

# --- Telegram Notification Function ---
def send_telegram_message(message_text):
    """Sends a message to your Telegram bot."""
    BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
    if BOT_TOKEN == "YOUR_BOT_TOKEN_FROM_BOTFATHER" or CHAT_ID == "YOUR_CHAT_ID_FROM_USERINFOBOT":
        print("WARNING: Telegram Bot Token or Chat ID not configured. Skipping notification.")
        return None
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(api_url, json={'chat_id': CHAT_ID, 'text': message_text, 'parse_mode': 'Markdown'})
        response.raise_for_status()
        print("Telegram message sent successfully.")
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error sending Telegram message: {e}")
        if e.response is not None:
             print(f"Telegram API Response: {e.response.text}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred in send_telegram_message: {e}")
        return None

# --- WEBSITE ROUTES ---

@app.route("/")
def home():
    products = load_products()
    return render_template("index.html", products=products[:3]) # Show only first 3 on home

@app.route("/products")
def products_page():
    products = load_products()
    return render_template("products.html", products=products)

@app.route("/product/<int:product_id>")
def product_detail(product_id):
    product = get_product_by_id(product_id)
    if product:
        return render_template("product_detail.html", product=product)
    else:
        abort(404, description=f"Product with ID {product_id} not found.")

@app.route("/events")
def events_page():
    events = load_events()
    return render_template("events.html", events=events)

@app.route("/event/<int:event_id>")
def event_detail(event_id):
    event = get_event_by_id(event_id)
    if event:
        return render_template("event_detail.html", event=event)
    else:
        abort(404, description=f"Event with ID {event_id} not found.")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        name = request.form.get("name", "N/A")
        email = request.form.get("email", "N/A")
        message_content = request.form.get("message", "N/A")

        # --- SAVE TO DATABASE ---
        try:
            new_message = ContactMessage(name=name, email_phone=email, message=message_content)
            db.session.add(new_message)
            db.session.commit()
            print("Contact message saved to database.")
        except Exception as e:
            db.session.rollback()
            print(f"Error saving contact message to database: {e}")
        # ---

        # --- SEND TELEGRAM NOTIFICATION ---
        telegram_text = f"✉️ *New General Contact Form Submission*:\n\n*Name:* {name}\n*Contact:* {email}\n*Message:* {message_content}"
        send_telegram_message(telegram_text)
        # ---

        return render_template("contact.html", success=True)

    return render_template("contact.html", success=False)

@app.route("/request-quote", methods=["GET", "POST"])
def request_quote():
    products = load_products() # Load products for the dropdown

    if request.method == "POST":
        name = request.form.get("name", "N/A")
        contact_info = request.form.get("contact_info", "N/A")
        company = request.form.get("company", "N/A")
        selected_products = request.form.getlist("products")
        details = request.form.get("details", "N/A")
        product_str = ", ".join(selected_products) if selected_products else "None Selected"

        # --- SAVE TO DATABASE ---
        try:
            new_quote = QuoteRequest(name=name, contact_info=contact_info, company=company, selected_products=product_str, details=details)
            db.session.add(new_quote)
            db.session.commit()
            print("Quote request saved to database.")
        except Exception as e:
            db.session.rollback()
            print(f"Error saving quote request to database: {e}")
        # ---

        # --- SEND DETAILED TELEGRAM NOTIFICATION ---
        product_list_md = "\n - ".join(selected_products) if selected_products else "None Selected"
        telegram_text = (f"📝 *New Quote Request on AxFlo:*\n\n"
                         f"*Name:* {name}\n"
                         f"*Contact:* {contact_info}\n"
                         f"*Company:* {company}\n\n"
                         f"*Products Interested In:*\n - {product_list_md}\n\n"
                         f"*Project Details:*\n{details}")
        send_telegram_message(telegram_text)
        # ---

        return render_template("request_quote.html", success=True, products=products)

    return render_template("request_quote.html", success=False, products=products)

# --- API Routes ---
@app.route("/api/products")
def api_products():
    products = load_products()
    return jsonify(products)

@app.route("/api/events")
def api_events():
    events = load_events()
    return jsonify(events)

@app.route("/api/refresh-products", methods=["POST"])
def refresh_products():
    """Manual endpoint to refresh products cache"""
    global _products_cache
    with _cache_lock:
        _products_cache = None
    products = load_products()
    return jsonify({"success": True, "message": f"Products cache refreshed. Loaded {len(products)} products."})

@app.route("/api/refresh-events", methods=["POST"])
def refresh_events():
    """Manual endpoint to refresh events cache"""
    global _events_cache
    with _cache_lock:
        _events_cache = None
    events = load_events()
    return jsonify({"success": True, "message": f"Events cache refreshed. Loaded {len(events)} events."})

@app.route("/api/order", methods=["POST"])
def place_order():
    try:
        data = request.get_json()
        if not data: return jsonify({"success": False, "message": "Invalid JSON payload."}), 400
        product_name = data.get("productName", "N/A")
        buyer = data.get("buyer", "N/A")
        contact = data.get("contact", "N/A")
        # Optional: Send Telegram
        telegram_order_text = f"🛒 *New Order Inquiry (via Modal):*\n\n*Product:* {product_name}\n*Buyer:* {buyer}\n*Contact:* {contact}"
        send_telegram_message(telegram_order_text)
        return jsonify({"success": True, "message": "Order inquiry received successfully!"})
    except Exception as e:
        print(f"Error processing order API request: {e}")
        return jsonify({"success": False, "message": "Server error processing request."}), 500

# --- Error Handling ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html', error=e), 404

@app.errorhandler(500)
def internal_server_error(e):
    print(f"Server Error: {e}") # Log the actual error
    db.session.rollback() # Rollback db session in case of error during request handling
    return render_template('500.html', error="An internal server error occurred."), 500 # Don't pass raw error object

# --- Initialize Database and File Watcher ---
file_observer = None

with app.app_context():
    try:
        db.create_all()
        print("Database tables checked/created.")
    except Exception as e:
        print(f"Error during initial db.create_all(): {e}")

# --- RUN SERVER ---
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    file_observer = start_file_watcher()
    try:
        # Set debug=False for production deployment!
        app.run(debug=False, host='0.0.0.0', port=port)
    finally:
        # Clean up file watcher when server stops
        if file_observer:
            file_observer.stop()
            file_observer.join()
            print("File watcher stopped")










