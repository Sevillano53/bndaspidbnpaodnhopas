#!/usr/bin/env python3
"""
Flask Product Inventory Management Application
A clean, professional web app for managing product inventory using CSV files.
Designed for users 50+ with minimal colors and intuitive interface.
Now with secure login and CSV download functionality.
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, send_file, session, flash
import csv
import os
from datetime import datetime
import json
from functools import wraps
import hashlib

app = Flask(__name__)
app.secret_key = 'Mst@Ph@2025#Inv3nt0ry$SecureK3y!'  # Strong secret key

# Configuration
CSV_FILE = 'products.csv'
CSV_HEADERS = ['id', 'name', 'serial_number', 'provider', 'buy_price', 'sell_price', 'benefit', 'date', 'sell_date']

# Login credentials
USERNAME = 'mustapha'
PASSWORD_HASH = hashlib.sha256('kingkong2025'.encode()).hexdigest()  # Strong password

def login_required(f):
    """Decorator to require login for protected routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def ensure_csv_exists():
    """Create CSV file with headers if it doesn't exist"""
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(CSV_HEADERS)

def load_products():
    """Load all products from CSV file"""
    ensure_csv_exists()
    products = []
    try:
        with open(CSV_FILE, 'r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                # Convert numeric fields
                row['id'] = int(row['id']) if row['id'] else 0
                row['buy_price'] = float(row['buy_price']) if row['buy_price'] else 0.0
                row['sell_price'] = float(row['sell_price']) if row['sell_price'] else 0.0
                row['benefit'] = float(row['benefit']) if row['benefit'] else 0.0
                # Handle sell_date field for backward compatibility
                if 'sell_date' not in row:
                    row['sell_date'] = ''
                products.append(row)
    except FileNotFoundError:
        pass
    return products

def save_products(products):
    """Save all products to CSV file"""
    with open(CSV_FILE, 'w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(products)

def get_next_id():
    """Get the next available ID"""
    products = load_products()
    if not products:
        return 1
    return max(int(p['id']) for p in products) + 1

def calculate_benefit(buy_price, sell_price):
    """Calculate benefit from buy and sell prices"""
    buy = float(buy_price) if buy_price else 0.0
    sell = float(sell_price) if sell_price else 0.0
    # Only calculate benefit if item is actually sold (sell_price > 0)
    return sell - buy if sell > 0 else 0.0

def get_unique_providers():
    """Get list of unique providers from existing products"""
    products = load_products()
    providers = set()
    for product in products:
        if product['provider'] and product['provider'].strip():
            providers.add(product['provider'].strip())
    return sorted(list(providers))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Login page"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if username == USERNAME and password_hash == PASSWORD_HASH:
            session['logged_in'] = True
            flash('Welcome to Product Inventory Manager!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password. Access denied.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """Logout and clear session"""
    session.clear()
    flash('You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    """Main page - requires login"""
    products = load_products()
    providers = get_unique_providers()
    return render_template('index.html', products=products, providers=providers)

@app.route('/summary')
@login_required
def summary():
    """Summary page with analytics - requires login"""
    products = load_products()
    return render_template('summary.html', products=products)

@app.route('/download-csv')
@login_required
def download_csv():
    """Download the CSV file"""
    try:
        return send_file(
            CSV_FILE,
            as_attachment=True,
            download_name=f'inventory_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
            mimetype='text/csv'
        )
    except Exception as e:
        flash('Error downloading CSV file.', 'error')
        return redirect(url_for('index'))

@app.route('/api/products')
@login_required
def api_products():
    """API endpoint to get all products"""
    products = load_products()
    return jsonify(products)

@app.route('/api/products/add', methods=['POST'])
@login_required
def add_product():
    """Add new product(s)"""
    data = request.json
    
    name = data.get('name', '').strip()
    serial_number = data.get('serial_number', '').strip()
    provider = data.get('provider', '').strip()
    buy_price = float(data.get('buy_price', 0))
    sell_price = float(data.get('sell_price', 0)) if data.get('sell_price') else 0
    quantity = int(data.get('quantity', 1))
    
    if not name:
        return jsonify({'error': 'Product name is required'}), 400
    
    products = load_products()
    next_id = get_next_id()
    current_date = datetime.now().strftime('%Y-%m-%d')
    
    # Add multiple products if quantity > 1
    new_products = []
    for i in range(quantity):
        benefit = calculate_benefit(buy_price, sell_price)
        sell_date = current_date if sell_price > 0 else ''
        product = {
            'id': next_id + i,
            'name': name,
            'serial_number': serial_number,
            'provider': provider,
            'buy_price': buy_price,
            'sell_price': sell_price,
            'benefit': benefit,
            'date': current_date,
            'sell_date': sell_date
        }
        new_products.append(product)
    
    products.extend(new_products)
    save_products(products)
    
    return jsonify({'success': True, 'products_added': len(new_products)})

@app.route('/api/products/update', methods=['POST'])
@login_required
def update_product():
    """Update existing product"""
    data = request.json
    product_id = int(data.get('id'))
    
    products = load_products()
    for product in products:
        if product['id'] == product_id:
            # Store old sell_price to detect changes
            old_sell_price = product['sell_price']
            
            product['name'] = data.get('name', product['name'])
            product['serial_number'] = data.get('serial_number', product['serial_number'])
            product['provider'] = data.get('provider', product['provider'])
            product['buy_price'] = float(data.get('buy_price', product['buy_price']))
            product['sell_price'] = float(data.get('sell_price', product['sell_price'])) if data.get('sell_price') else 0
            product['benefit'] = calculate_benefit(product['buy_price'], product['sell_price'])
            
            # Set sell_date when sell_price is first added or changed from 0 to a value
            if product['sell_price'] > 0 and old_sell_price == 0:
                product['sell_date'] = datetime.now().strftime('%Y-%m-%d')
            elif product['sell_price'] == 0:
                product['sell_date'] = ''
            
            break
    
    # Auto-save immediately
    save_products(products)
    return jsonify({'success': True})

@app.route('/api/products/delete', methods=['POST'])
@login_required
def delete_product():
    """Delete a product"""
    data = request.json
    product_id = int(data.get('id'))
    
    products = load_products()
    products = [p for p in products if p['id'] != product_id]
    
    # Auto-save immediately
    save_products(products)
    return jsonify({'success': True})

@app.route('/api/products/save', methods=['POST'])
@login_required
def save_all_products():
    """Save all products from frontend"""
    data = request.json
    products = data.get('products', [])
    
    # Recalculate benefits for all products
    for product in products:
        product['benefit'] = calculate_benefit(product['buy_price'], product['sell_price'])
    
    save_products(products)
    return jsonify({'success': True})

@app.route('/api/summary/stats')
@login_required
def get_summary_stats():
    """Get summary statistics"""
    products = load_products()
    
    # Calculate total benefits (sum of all benefits where sell_price > 0)
    total_benefits = sum(
        float(product.get('benefit', 0)) 
        for product in products 
        if float(product.get('sell_price', 0)) > 0
    )
    
    # Calculate capital (sum of buy_price for unsold products)
    # Unsold = sell_price is 0 or empty
    capital = sum(
        float(product.get('buy_price', 0)) 
        for product in products 
        if float(product.get('sell_price', 0)) == 0
    )
    
    # Additional stats
    total_products = len(products)
    sold_products = len([p for p in products if float(p.get('sell_price', 0)) > 0])
    unsold_products = total_products - sold_products
    
    return jsonify({
        'total_benefits': total_benefits,
        'capital': capital,
        'total_products': total_products,
        'sold_products': sold_products,
        'unsold_products': unsold_products
    })

@app.route('/api/summary/monthly/<int:year>')
@login_required
def get_monthly_stats(year):
    """Get monthly statistics for a specific year"""
    products = load_products()
    
    # Initialize monthly data
    monthly_data = {}
    for month in range(1, 13):
        monthly_data[month] = {
            'month_name': ['', 'January', 'February', 'March', 'April', 'May', 'June',
                          'July', 'August', 'September', 'October', 'November', 'December'][month],
            'benefits': 0,
            'capital': 0,
            'products_bought': 0,
            'products_sold': 0
        }
    
    year_totals = {
        'total_benefits': 0,
        'total_capital': 0,
        'total_products_bought': 0,
        'total_products_sold': 0
    }
    
    for product in products:
        # Parse dates
        buy_date = product.get('date', '')
        sell_date = product.get('sell_date', '')
        
        # Check if product was bought in this year
        if buy_date.startswith(str(year)):
            month = int(buy_date.split('-')[1])
            monthly_data[month]['products_bought'] += 1
            year_totals['total_products_bought'] += 1
            
            # Add to capital if not sold
            if float(product.get('sell_price', 0)) == 0:
                buy_price = float(product.get('buy_price', 0))
                monthly_data[month]['capital'] += buy_price
                year_totals['total_capital'] += buy_price
        
        # Check if product was sold in this year
        if sell_date and sell_date.startswith(str(year)):
            month = int(sell_date.split('-')[1])
            benefit = float(product.get('benefit', 0))
            monthly_data[month]['benefits'] += benefit
            monthly_data[month]['products_sold'] += 1
            year_totals['total_benefits'] += benefit
            year_totals['total_products_sold'] += 1
    
    return jsonify({
        'year': year,
        'monthly_data': monthly_data,
        'year_totals': year_totals
    })

@app.route('/api/summary/available-years')
@login_required
def get_available_years():
    """Get all years that have products"""
    products = load_products()
    years = set()
    
    for product in products:
        # Extract year from buy date
        buy_date = product.get('date', '')
        if buy_date:
            year = buy_date.split('-')[0]
            if year.isdigit():
                years.add(int(year))
        
        # Extract year from sell date
        sell_date = product.get('sell_date', '')
        if sell_date:
            year = sell_date.split('-')[0]
            if year.isdigit():
                years.add(int(year))
    
    return jsonify(sorted(list(years), reverse=True))

@app.route('/api/providers')
@login_required
def get_providers():
    """Get all unique providers"""
    providers = get_unique_providers()
    return jsonify(providers)

if __name__ == '__main__':
    ensure_csv_exists()
    app.run(debug=True, port=5000)
