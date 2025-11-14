from flask import Flask, render_template, request, session, redirect, url_for, flash, make_response
import qrcode
import os
import uuid
import json
import send_from_directory

app = Flask(__name__)
app.secret_key = "supersecretkey"

UPLOAD_FOLDER = 'static/qrcodes/'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- HEADERS ----------------
@app.after_request
def add_headers(response):
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    response.headers['Content-Security-Policy'] = "frame-ancestors 'self' https://whop.com"
    return response

# ---------------- USER DATA ----------------
def load_users():
    if not os.path.exists("users.json"):
        return {}
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {}  # safe fallback

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f, indent=4)

# ---------------- INDEX / QR GENERATOR ----------------
@app.route("/", methods=["GET", "POST"])
def index():
    qr_img = None
    qr_name_user = None

    if request.method == "POST":
        if 'username' not in session:
            flash("You need to log in to save QR codes!")
            return redirect(url_for('login'))

        username = session['username']
        text = request.form.get("text-url")
        file = request.files.get("fichier")
        qr_name_input = request.form.get("qr-name") or "Untitled QR"

        # --- Save QR code ---
        qr_filename = f"qr_{uuid.uuid4().hex}.png"
        qr_path = os.path.join(app.config['UPLOAD_FOLDER'], qr_filename)

        # Determine content
        if file and file.filename != "":
            filename = f"{uuid.uuid4().hex}_{file.filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            qr_content = f"{request.host_url}static/qrcodes/{filename}"
        elif text:
            qr_content = text
        else:
            flash("Please enter text or upload a file.")
            return redirect(url_for('index'))

        # --- Optimized QR generation ---
        qr = qrcode.QRCode(
            version=1,  # smallest QR
            error_correction=qrcode.constants.ERROR_CORRECT_L,  # faster
            box_size=5,
            border=2
        )
        qr.add_data(qr_content)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(qr_path)
        qr_img = f"static/qrcodes/{qr_filename}"
        qr_name_user = qr_name_input

        # --- Save to user safely ---
        users = load_users()
        if username not in users:
            users[username] = {"password": "", "qr_codes": []}
        if not isinstance(users[username].get("qr_codes"), list):
            users[username]["qr_codes"] = []

        users[username]["qr_codes"].append({"name": qr_name_user, "file": qr_img})
        save_users(users)
        flash(f"QR '{qr_name_user}' saved successfully!")

    # Logged-in user's QR gallery
    user_qr_list = []
    if 'username' in session:
        users = load_users()
        user_data = users.get(session['username'], {})
        user_qr_list = user_data.get("qr_codes", [])

    return render_template("HTMLpage.html", qr_img=qr_img, username=session.get('username'), user_qr_list=user_qr_list)

# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        users = load_users()

        if username in users and users[username]["password"] == password:
            session['username'] = username
            flash(f"Welcome, {username}!")
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password!")
            return redirect(url_for('login'))

    return render_template("login.html")

# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        password2 = request.form.get("password2")
        users = load_users()

        if username in users:
            flash("Username already exists!")
        elif password != password2:
            flash("Passwords do not match!")
        else:
            users[username] = {"password": password, "qr_codes": []}
            save_users(users)
            flash("Registration successful! You can now login.")
            return redirect(url_for('login'))

    return render_template("register.html")

# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.pop('username', None)
    flash("Logged out successfully.")
    return redirect(url_for('index'))

# ---------------- DELETE QR ----------------
@app.route("/delete_qr/<qr_file>", methods=["POST"])
def delete_qr(qr_file):
    if 'username' not in session:
        flash("You must be logged in to delete QR codes!")
        return redirect(url_for('login'))

    username = session['username']
    users = load_users()
    user_data = users.get(username, {})

    # Remove QR from user's list
    qr_list = user_data.get("qr_codes", [])
    qr_to_remove = None
    for qr in qr_list:
        if qr['file'].endswith(qr_file):
            qr_to_remove = qr
            break

    if qr_to_remove:
        qr_list.remove(qr_to_remove)
        qr_path = os.path.join("static/qrcodes", qr_file)
        if os.path.exists(qr_path):
            os.remove(qr_path)
        users[username]["qr_codes"] = qr_list
        save_users(users)
        flash("QR code deleted successfully!")
    else:
        flash("QR code not found!")

    return redirect(url_for('index'))
    
    

@app.route('/robots.txt')
def robots():
    return send_from_directory('static', 'robots.txt')


# ---------------- RUN APP ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "False") == "True"
    app.run(host="0.0.0.0", port=port, debug=debug)






