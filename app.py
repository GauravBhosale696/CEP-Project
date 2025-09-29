from flask import Flask, flash, session, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
# In your app.py file

app = Flask(__name__)
app.config['SECRET_KEY'] = 'a-very-long-and-random-string-of-characters-that-you-will-not-guess'
app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///login.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

class Owner(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_name = db.Column(db.String(200), nullable=False)
    owner_mail = db.Column(db.String(200), nullable=False, unique=True)
    owner_phone = db.Column(db.String(15), nullable=False) 
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

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        owner_name = request.form['name']
        owner_mail = request.form['email']
        owner_phone = request.form['phone']
        owner_username = request.form['UserName']
        owner_password = request.form['password']
        phar_name = request.form['Pharmacy-name']
        phar_lic_num = request.form['DRL']
        phar_add = request.form['Address']

        hashed_password = generate_password_hash(owner_password)
        
        if Owner.query.filter_by(owner_username=owner_username).first():
            return redirect(url_for('register'))
        
        if Owner.query.filter_by(phar_lic_num=phar_lic_num).first():
            return redirect(url_for('register'))

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
        return redirect(url_for('login')) 
    
    return render_template('register_page.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = Owner.query.filter_by(owner_username=username).first()
        if user and check_password_hash(user.owner_password, password):
            session['user_id'] = user.id
            session['username'] = user.owner_username
            return redirect(url_for('dashboard'))
        else:
            return redirect(url_for('login'))
        

    return render_template("login_page.html")


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    return render_template("dashboard.html")

class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    expiry_date = db.Column(db.String(50), nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('owner.id'), nullable=False)
    owner = db.relationship('Owner', backref=db.backref('medicines', lazy=True))

@app.route('/add_stock', methods=['GET', 'POST'])
def add_stock():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name']
        quantity = request.form['quantity']
        expiry_date = request.form['expiry_date']

        new_medicine = Medicine(
            name=name,
            quantity=quantity,
            expiry_date=expiry_date,
            owner_id=session['user_id']
        )
        db.session.add(new_medicine)
        db.session.commit()
    
    return render_template('add_stock.html')

@app.route('/display_stock')
def display_stock():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    medicines = Medicine.query.filter_by(owner_id=session['user_id']).all()
    
    return render_template('display_stock.html', medicines=medicines)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)