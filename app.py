from flask import Flask, flash, session, request, render_template, redirect, url_for, get_flashed_messages
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta 
import json
import os

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

class Medicine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    expiry_date = db.Column(db.String(50), nullable=False)
    
    # --- THESE NEW COLUMNS MUST BE PRESENT ---
    cost_price = db.Column(db.Float, nullable=False)    
    selling_price = db.Column(db.Float, nullable=False) 
    # ----------------------------------------
    
    owner_id = db.Column(db.Integer, db.ForeignKey('owner.id'), nullable=False)
    owner = db.relationship('Owner', backref=db.backref('medicines', lazy=True))

def delete_expired_stock(owner_id):
    """Deletes all medicine records belonging to a specific owner that have expired."""
    today = datetime.now().date()
    
    medicines = Medicine.query.filter_by(owner_id=owner_id).all()
    deleted_count = 0
    
    for medicine in medicines:
        try:
            # Convert 'yyyy-mm-dd' string to date object
            expiry = datetime.strptime(medicine.expiry_date, '%Y-%m-%d').date()
            
            # Check if the medicine has expired (expiry date is today or earlier)
            if expiry <= today:
                db.session.delete(medicine)
                deleted_count += 1

        except ValueError:
            # Skip items with bad date format
            continue
    
    if deleted_count > 0:
        db.session.commit()
        return f'{deleted_count} expired medicine(s) have been automatically removed from your stock.'
    
    return None # Returns None if no items were deleted

def get_dashboard_alerts(owner_id):
    """Calculates counts for expiring stock and low stock items."""
    medicines = Medicine.query.filter_by(owner_id=owner_id).all()
    
    today = datetime.now().date()
    expiring_soon_count = 0
    low_stock_count = 0
    LOW_STOCK_THRESHOLD = 10 # Define the threshold for low stock

    for medicine in medicines:
        # Check for Expiry Alert (Expired or within 90 days)
        try:
            expiry = datetime.strptime(medicine.expiry_date, '%Y-%m-%d').date()
            days_until_expiry = (expiry - today).days
            
            if days_until_expiry <= 90:
                expiring_soon_count += 1
        except ValueError:
            pass

        # Check for Low Stock Alert
        if medicine.quantity <= LOW_STOCK_THRESHOLD:
            low_stock_count += 1

    return {
        'expiring_count': expiring_soon_count,
        'low_stock_count': low_stock_count
    }

class SaleTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('owner.id'), nullable=False)
    customer_name = db.Column(db.String(200), nullable=True)
    customer_phone = db.Column(db.String(15), nullable=True)
    total_amount = db.Column(db.Float, nullable=False)
    total_cost = db.Column(db.Float, nullable=False, default=0.0)
    transaction_date = db.Column(db.DateTime, default=datetime.utcnow)
    bill_content = db.Column(db.String(5000), nullable=True) # Stores the text content of the final bill

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
            flash('Username already exists!', 'error')
            return redirect(url_for('register'))
        
        if Owner.query.filter_by(phar_lic_num=phar_lic_num).first():
            flash('License Number already registered!', 'error')
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
        flash('Registration successful! Please log in.', 'success')
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
            flash(f'Welcome back, {user.owner_username}!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
            return redirect(url_for('login'))
        

    return render_template("login_page.html")


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # 1. OPTIONAL: Automatically delete expired stock upon login
    message = delete_expired_stock(session['user_id'])
    if message:
        flash(message, 'info')
    
    # 2. Calculate and fetch alert metrics for the dashboard display
    alerts = get_dashboard_alerts(session['user_id'])

    return render_template("dashboard.html", alerts=alerts)


@app.route('/add_stock', methods=['GET', 'POST'])
def add_stock():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        name = request.form['name'].strip()
        quantity = request.form['quantity']
        expiry_date = request.form['expiry_date']
        
        cost_price = request.form['cost_price']
        selling_price = request.form['selling_price']

        try:
            quantity = int(quantity)
            cost_price = float(cost_price)
            selling_price = float(selling_price)
        except ValueError:
            flash('Quantity and prices must be valid numbers.', 'error')
            return redirect(url_for('add_stock'))

        new_medicine = Medicine(
            name=name,
            quantity=quantity,
            expiry_date=expiry_date,
            cost_price=cost_price,         
            selling_price=selling_price,   
            owner_id=session['user_id']
        )
        db.session.add(new_medicine)
        db.session.commit()
        
        # --- SIMPLIFIED FLASH MESSAGE ---
        flash(f'{name} added to stock successfully!', 'success_popup')
        
        flashed_messages = get_flashed_messages(with_categories=True)
        return render_template('add_stock.html', messages=flashed_messages)
        
    flashed_messages = get_flashed_messages(with_categories=True)
    return render_template('add_stock.html', messages=flashed_messages)


@app.route('/display_stock')
def display_stock():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # We call delete_expired_stock here too for immediate cleanup when viewing stock
    message = delete_expired_stock(session['user_id'])
    if message:
        flash(message, 'info')

    # --- NEW LOGIC TO HANDLE DASHBOARD LINKS ---
    alert_type = request.args.get('alert') # Get the alert parameter from the URL
    
    medicines = Medicine.query.filter_by(owner_id=session['user_id']).all()
    
    today = datetime.now().date()
    filtered_medicines = []
    LOW_STOCK_THRESHOLD = 10 # Must match the threshold used in get_dashboard_alerts

    for medicine in medicines:
        is_expiring = False
        is_low_stock = medicine.quantity <= LOW_STOCK_THRESHOLD

        try:
            expiry = datetime.strptime(medicine.expiry_date, '%Y-%m-%d').date()
            days_until_expiry = (expiry - today).days
            
            medicine.alert_class = ''
            if days_until_expiry <= 0:
                medicine.alert_class = 'expired'
                is_expiring = True
            elif days_until_expiry <= 90:
                medicine.alert_class = 'expiring-soon'
                is_expiring = True
            
            medicine.days_until_expiry = days_until_expiry

        except ValueError:
            medicine.alert_class = 'date-error'
            medicine.days_until_expiry = 'N/A'
        
        # Filter the results based on the URL parameter
        if alert_type == 'expiry' and is_expiring:
            filtered_medicines.append(medicine)
        elif alert_type == 'low_stock' and is_low_stock:
            filtered_medicines.append(medicine)
        elif not alert_type:
            # If no alert parameter, show all medicines
            filtered_medicines.append(medicine)

    flashed_messages = get_flashed_messages(with_categories=True)
    
    # Pass the filtered list to the template
    return render_template('display_stock.html', medicines=filtered_medicines, messages=flashed_messages)


@app.route('/view_sales_report')
def view_sales_report():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Logic to fetch sales transactions from the SaleTransaction model
    sales = SaleTransaction.query.filter_by(owner_id=session['user_id']).order_by(SaleTransaction.transaction_date.desc()).all()
    
    # Pass the list of sales transactions to the template
    return render_template('sales_report.html', sales=sales)

@app.route('/billing', methods=['GET', 'POST'])
def billing():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        # --- 1. Retrieve Data from Hidden Form ---
        customer_name = request.form['customer_name_final']
        customer_phone = request.form['customer_phone_final']
        bill_items_json = request.form['bill_items_json']
        total_amount = float(request.form['total_amount_final'])
        bill_text_content = request.form['bill_text_content'].replace('\n', '\\n').replace('\r', '') # Escape newlines
        
        # Parse the item list
        try:
            bill_items = json.loads(bill_items_json)
        except json.JSONDecodeError:
            flash("Error processing bill data: Invalid JSON format.", "error")
            return redirect(url_for('billing'))
        
        if not bill_items:
            flash("Cannot generate bill: no items recorded.", "error")
            return redirect(url_for('billing'))

        # --- 2. Process Sales and Calculate Totals ---
        stock_updated = True
        total_revenue = 0.0
        total_cost_of_goods_sold = 0.0 
        
        # Loop through each item in the bill to deduct stock and calculate costs/revenue
        for item in bill_items:
            medicine = Medicine.query.filter_by(
                id=item['id'],
                owner_id=session['user_id']
            ).first()

            if medicine and medicine.quantity >= item['qty']:
                medicine.quantity -= item['qty']
                
                # Accumulate costs and revenue
                total_revenue += item['rate'] * item['qty']
                total_cost_of_goods_sold += item['cost'] * item['qty'] 
            else:
                # If stock check failed for any item, abort the transaction
                flash(f"Stock error: Insufficient quantity for {item['name']}. Transaction aborted.", "error")
                stock_updated = False
                break
        
        if not stock_updated:
            return redirect(url_for('billing'))

        # --- 3. Save Transaction Record ---
        new_transaction = SaleTransaction(
            owner_id=session['user_id'],
            customer_name=customer_name,
            customer_phone=customer_phone,
            total_amount=total_revenue,
            total_cost=total_cost_of_goods_sold,
            bill_content=bill_text_content
        )
        db.session.add(new_transaction)
        db.session.commit()
        
        
        # --- 4. Save Bill Copy as .txt File ---
        bill_filename = f"bill_{new_transaction.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        
        # Ensure a 'bills' directory exists in your project root
        bills_dir = os.path.join(app.root_path, 'bills')
        os.makedirs(bills_dir, exist_ok=True)
        
        bill_path = os.path.join(bills_dir, bill_filename)

        with open(bill_path, 'w') as f:
            f.write(bill_text_content.replace('\\n', '\n')) # Unescape newlines for the file content
        
        # --- 5. Flash Success Message ---
        flash(f"Bill #{new_transaction.id} processed successfully! Total: ₹{total_amount:.2f}. Bill saved as {bill_filename}.", "success")
        return redirect(url_for('billing'))

    # --- GET request logic (for initial page load) ---
    
    # FIFO SUGGESTION: Order the stock by expiry_date ascending (oldest date first)
    available_stock = Medicine.query.filter_by(owner_id=session['user_id']).order_by(Medicine.expiry_date.asc()).all()

    flashed_messages = get_flashed_messages(with_categories=True)
    return render_template('billing_page.html', 
                           messages=flashed_messages,
                           stock=available_stock)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)