from flask import Flask, render_template, request, redirect, url_for, send_file, flash, make_response
from flask_sqlalchemy import SQLAlchemy
import csv
from io import StringIO, BytesIO
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from functools import wraps

# Initialize Flask app and configurations
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///project.db'  
app.config["SECRET_KEY"] = "welcome" 
db = SQLAlchemy(app)

# Flask-Login Setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "loginFunction" 

@app.route("/")
def home():
    return render_template("home.html")

# Inventory Database Model
class InventoryItem(db.Model):
    __tablename__ = "inventory"
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    item_number = db.Column(db.String(100), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    last_changed = db.Column(db.DateTime, nullable=True)

# User Database Model (for authentication)
class User(db.Model, UserMixin):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100))
    email = db.Column(db.String(100))
    password_hash = db.Column(db.String(200))
    role = db.Column(db.String(100), default="user")

    def generate_password(self, simple_password):
        self.password_hash = generate_password_hash(simple_password)
    
    def check_password(self, simple_password):
        return check_password_hash(self.password_hash, simple_password)
    
# User Authentication Routes
@app.route("/register", methods=["POST", "GET"])
def registerFunction():
    if request.method == "POST":
        username = request.form.get("username")
        email = request.form.get("email")
        role=request.form.get("role")
        password = request.form.get("password")

        if User.query.filter_by(email=email).first():
            flash("User already exists")
            return redirect(url_for("home"))

        user_object = User(username=username, email=email,role=role)
        user_object.generate_password(password)
        db.session.add(user_object)
        db.session.commit()

        flash("User registered successfully.")
        return redirect(url_for("loginFunction"))

    return render_template("signup.html")

# Initialize Login Manager
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User,int(user_id))

# Route for Inventory Page
@app.route('/index')
@login_required
def index():
    sort_by = request.args.get('sort_by', 'date_added') 
    order = request.args.get('order', 'asc') 
    search_query = request.args.get('search', '')  
    query = InventoryItem.query
    if search_query:
        query = query.filter(
            db.or_(
                InventoryItem.item_name.ilike(f'%{search_query}%'),
                InventoryItem.item_number.ilike(f'%{search_query}%'),
                InventoryItem.quantity.ilike(f'%{search_query}%'),
                InventoryItem.price.ilike(f'%{search_query}%')
            )
        )
# Apply sorting based on the selected criteria
    if order == 'asc':
        if sort_by == 'item_name':
            items = query.order_by(db.asc(InventoryItem.item_name)).all()
        elif sort_by == 'item_number':
            items = query.order_by(db.asc(InventoryItem.item_number)).all()
        elif sort_by == 'quantity':
            items = query.order_by(db.asc(InventoryItem.quantity)).all()
        elif sort_by == 'price':
            items = query.order_by(db.asc(InventoryItem.price)).all()
        else: 
            items = query.order_by(db.asc(InventoryItem.date_added)).all()
    else:
        if sort_by == 'item_name':
            items = query.order_by(db.desc(InventoryItem.item_name)).all()
        elif sort_by == 'item_number':
            items = query.order_by(db.desc(InventoryItem.item_number)).all()
        elif sort_by == 'quantity':
            items = query.order_by(db.desc(InventoryItem.quantity)).all()
        elif sort_by == 'price':
            items = query.order_by(db.desc(InventoryItem.price)).all()
        else: 
            items = query.order_by(db.desc(InventoryItem.date_added)).all()
    return render_template(
        'index.html', 
        items=items, 
        mode='index', 
        sort_by=sort_by, 
        order=order, 
        search_query=search_query 
    )

@app.route("/aboutus")
def aboutus():
    return render_template("aboutus.html")

# Route for Adding Item
@app.route('/add', methods=['POST'])
@login_required
def add_item():
    item_number = request.form['item_number']
    item_name = request.form['item_name']
    quantity = request.form['quantity']
    price = request.form['price']
    new_item = InventoryItem(item_number=item_number, item_name=item_name, quantity=quantity, price=price)
    db.session.add(new_item)
    db.session.commit()
    flash('Item added successfully!', 'success')
    return redirect(url_for('index'))

# Route for Viewing an Item
@app.route('/view/<int:id>', methods=['GET'])
@login_required
def view_item(id):
    item = InventoryItem.query.get_or_404(id)  
    return render_template('view_item.html', item=item, mode='view')

# Route for Editing Item
@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_item(id):
    item = InventoryItem.query.get_or_404(id)

    if request.method == 'POST':
        updated_item_name = request.form['item_name']
        updated_item_number = request.form['item_number']
        updated_quantity = int(request.form['quantity'])
        updated_price = float(request.form['price'])
        updated_date_added = datetime.strptime(request.form['date_added'], '%Y-%m-%d')

        if (updated_item_number == item.item_number and
            updated_item_name == item.item_name and
            updated_quantity == item.quantity and
            updated_price == item.price and
            updated_date_added == item.date_added):
            flash('Nothing has been changed', 'info')
        else:
            item.item_number = updated_item_number
            item.item_name = updated_item_name
            item.quantity = updated_quantity
            item.price = updated_price
            item.date_added = updated_date_added
            item.last_changed = datetime.utcnow() 
            db.session.commit()
            flash('Item updated successfully!', 'success')

        return redirect(url_for('index'))

    return render_template('index.html', item=item, mode='edit')

# Route for Deleting Item
@app.route('/delete/<int:id>',methods=["POST","GET"])
@login_required
def delete_item(id):
    item = InventoryItem.query.get_or_404(id)
    db.session.delete(item)
    db.session.commit()
    flash('Item deleted successfully!', 'success')
    return redirect(url_for('index'))

@app.route('/export')
@login_required
def export_csv():
    items = InventoryItem.query.all()
    si = StringIO()
    writer = csv.writer(si)
    writer.writerow(['Date Added', 'Item Name', 'ID', 'Quantity', 'Price', 'Last Changed'])

    for item in items:
        date_added = item.date_added.strftime('%Y/%m/%d')
        last_changed = item.last_changed.strftime('%Y/%m/%d') if item.last_changed else ''
        writer.writerow([date_added, item.item_name, item.id, item.quantity, item.price, last_changed])

    output = si.getvalue().encode('utf-8')
    si.close()
    return send_file(BytesIO(output), mimetype='text/csv', as_attachment=True, download_name='inventory.csv')

def role_required(role):
    def decorator(func):
        @wraps(func)  
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role != role:
                flash("Unauthorized Access", "danger")
                return redirect(url_for("index"))
            return func(*args, **kwargs)
        return wrapper
    return decorator

# Route for Inventory Page
@app.route('/admin')
@role_required("admin")
@login_required
def admin():
    sort_by = request.args.get('sort_by', 'date_added') 
    order = request.args.get('order', 'asc') 
    search_query = request.args.get('search', '')  
    query = InventoryItem.query
    if search_query:
        query = query.filter(
            db.or_(
                InventoryItem.item_name.ilike(f'%{search_query}%'),
                InventoryItem.item_number.ilike(f'%{search_query}%'),
                InventoryItem.quantity.ilike(f'%{search_query}%'),
                InventoryItem.price.ilike(f'%{search_query}%')
            )
        )
# Apply sorting based on the selected criteria
    if order == 'asc':
        if sort_by == 'item_name':
            items = query.order_by(db.asc(InventoryItem.item_name)).all()
        elif sort_by == 'item_number':
            items = query.order_by(db.asc(InventoryItem.item_number)).all()
        elif sort_by == 'quantity':
            items = query.order_by(db.asc(InventoryItem.quantity)).all()
        elif sort_by == 'price':
            items = query.order_by(db.asc(InventoryItem.price)).all()
        else: 
            items = query.order_by(db.asc(InventoryItem.date_added)).all()
    else:
        if sort_by == 'item_name':
            items = query.order_by(db.desc(InventoryItem.item_name)).all()
        elif sort_by == 'item_number':
            items = query.order_by(db.desc(InventoryItem.item_number)).all()
        elif sort_by == 'quantity':
            items = query.order_by(db.desc(InventoryItem.quantity)).all()
        elif sort_by == 'price':
            items = query.order_by(db.desc(InventoryItem.price)).all()
        else: 
            items = query.order_by(db.desc(InventoryItem.date_added)).all()
    return render_template(
        'admin.html', 
        items=items, 
        mode='admin', 
        sort_by=sort_by, 
        order=order, 
        search_query=search_query 
    )

@app.route("/login", methods=["POST", "GET"])
def loginFunction():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        user_object = User.query.filter_by(email=email).first()

        if user_object and user_object.check_password(password):
            login_user(user_object)
            

            if user_object.role == "admin":
                flash("Admin logged in successfully.")
                return redirect(url_for("admin"))
            else:
                flash("User logged in successfully.")
                return redirect(url_for("index"))
        else:
            flash("Invalid credentials.", "danger")
            return redirect(url_for("loginFunction"))

    return render_template("login.html")

@app.route("/logout")
def logout():
    logout_user()
    flash("User Logged Out Successfully")
    return redirect(url_for("home"))

@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html", user=current_user)

@app.errorhandler(404)
def error_404(e):
    print(e)
    return render_template("errorPages/404.html"),404

@app.errorhandler(500)
def error_500(e):
    print(e)
    return render_template("errorPages/500.html"),500

with app.app_context(): 
    db.create_all()

    if not User.query.filter_by(role='admin').first():
        admin=User(username="admin" ,email="admin@gmail.com" ,role="admin")
        admin.generate_password("admin")
        db.session.add(admin)
        db.session.commit()

if __name__ == "__main__":
    app.run(debug=True)