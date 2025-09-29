from flask import Flask, flash, session, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secure-and-random-key' # !! CHANGE THIS !!
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///login.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# The User model is renamed for clarity and includes unique=True for
# username and email to prevent duplicates.
class Owner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_name = db.Column(db.String(200), nullable=False)
    owner_mail = db.Column(db.String(200), nullable=False, unique=True)
    owner_phone = db.Column(db.String(15), nullable=False) # Phone numbers should be strings
    owner_username = db.Column(db.String(200), nullable=False, unique=True)
    owner_password = db.Column(db.String(200), nullable=False)
    phar_name = db.Column(db.String(200), nullable=False)
    phar_lic_num = db.Column(db.String(200), nullable=False, unique=True)
    phar_add = db.Column(db.String(1000), nullable=True)

    def __repr__(self):
        return f'<Owner {self.owner_username}>'
    
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/about-us')
def about_us():
    return render_template('about-us.html')

# Create a simple route for the contact page
@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Mapped form names directly to model attributes
        owner_name = request.form['name']
        owner_mail = request.form['email']
        owner_phone = request.form['phone']
        owner_username = request.form['UserName']
        owner_password = request.form['password']
        phar_name = request.form['Pharmacy-name']
        phar_lic_num = request.form['DRL']
        phar_add = request.form['Address']

        # Hashing the password for security
        hashed_password = generate_password_hash(owner_password)
        
        # Check for existing user or license number
        if Owner.query.filter_by(owner_username=owner_username).first():
            flash('Username already exists. Please choose a different one.', 'danger')
            return redirect(url_for('register'))
        
        if Owner.query.filter_by(phar_lic_num=phar_lic_num).first():
            flash('License number already registered.', 'danger')
            return redirect(url_for('register'))

        # The names must match your model columns exactly
        new_owner = Owner(
            owner_name=owner_name,
            owner_mail=owner_mail,
            owner_phone=owner_phone,
            owner_username=owner_username,
            owner_password=hashed_password,
            phar_name=phar_name,
            phar_lic_num=phar_lic_num,
            phar_add=phar_add
        )
        db.session.add(new_owner)
        db.session.commit()
        flash('Registration successful!', 'success')
        return redirect(url_for('login')) # Redirect to the login page
    
    return render_template('register_page.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = Owner.query.filter_by(owner_username=username).first()
        if user and check_password_hash(user.owner_password, password):
            session['logged_in'] = True
            session['username'] = user.owner_username
            flash(f"Welcome back, {user.owner_name}!", 'success')
            return redirect(url_for('dashboard'))
        else:
            flash("Invalid username or password", 'danger')
            return redirect(url_for('login'))
        

    return render_template("login_page.html")


@app.route('/dashboard')
def dashboard():
    if not session.get('logged_in'):
        flash("Please log in to access the dashboard.", 'warning')
        return redirect(url_for('login'))
    
    return render_template("dashboard.html")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)