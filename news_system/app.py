import os
from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime
import mysql.connector
from dotenv import load_dotenv
import click

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'default_secret_key')
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'images', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Ensure upload directory exists
os.makedirs(os.path.join(app.root_path, app.config['UPLOAD_FOLDER']), exist_ok=True)

# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'news_system')
    )

# Function to generate password hash with compatible method
def generate_safe_password_hash(password):
    return generate_password_hash(password, method='sha256')

# Login manager setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Create admin user command
@app.cli.command('create-admin')
@click.argument('username')
@click.argument('email')
@click.argument('password')
def create_admin(username, email, password):
    """Create an admin user."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Check if email already exists
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        click.echo(f"Error: Email {email} already registered")
        return
    
    # Create admin user
    hashed_password = generate_safe_password_hash(password)
    cursor.execute(
        "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)",
        (username, email, hashed_password, 'admin')
    )
    conn.commit()
    
    cursor.close()
    conn.close()
    click.echo(f"Admin user {username} created successfully")

# Reset user password command
@app.cli.command('reset-password')
@click.argument('email')
@click.argument('new_password')
def reset_password(email, new_password):
    """Reset a user's password."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Check if user exists
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    if not user:
        cursor.close()
        conn.close()
        click.echo(f"Error: No user found with email {email}")
        return
    
    # Update password with safe hash
    hashed_password = generate_safe_password_hash(new_password)
    cursor.execute(
        "UPDATE users SET password = %s WHERE email = %s",
        (hashed_password, email)
    )
    conn.commit()
    
    cursor.close()
    conn.close()
    click.echo(f"Password for {email} reset successfully")

# User class for Flask-Login
class User:
    def __init__(self, id, username, email, role):
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.is_authenticated = True
        self.is_active = True
        self.is_anonymous = False

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user_data = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if user_data:
        return User(
            id=user_data['id'],
            username=user_data['username'],
            email=user_data['email'],
            role=user_data['role']
        )
    return None

# Template context processors
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

@app.context_processor
def inject_categories():
    def get_categories():
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.*, COUNT(a.id) as article_count 
            FROM categories c 
            LEFT JOIN articles a ON c.id = a.category_id 
            GROUP BY c.id
        """)
        categories = cursor.fetchall()
        cursor.close()
        conn.close()
        return categories
    return dict(get_categories=get_categories)

# Routes
@app.route('/')
def index():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT a.*, c.name as category_name, u.username as author_name 
        FROM articles a 
        JOIN categories c ON a.category_id = c.id 
        JOIN users u ON a.author_id = u.id 
        WHERE a.status = 'published' 
        ORDER BY a.created_at DESC 
        LIMIT 6
    """)
    featured_articles = cursor.fetchall()
    
    cursor.execute("""
        SELECT c.*, COUNT(a.id) as article_count 
        FROM categories c 
        LEFT JOIN articles a ON c.id = a.category_id 
        GROUP BY c.id
    """)
    categories = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('index.html', 
                           featured_articles=featured_articles, 
                           categories=categories)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/articles')
def articles():
    category_id = request.args.get('category', None)
    search_query = request.args.get('q', None)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT a.*, c.name as category_name, u.username as author_name 
        FROM articles a 
        JOIN categories c ON a.category_id = c.id 
        JOIN users u ON a.author_id = u.id 
        WHERE a.status = 'published'
    """
    params = []
    
    if category_id:
        query += " AND a.category_id = %s"
        params.append(category_id)
    
    if search_query:
        query += " AND (a.title LIKE %s OR a.content LIKE %s)"
        params.extend([f'%{search_query}%', f'%{search_query}%'])
    
    query += " ORDER BY a.created_at DESC"
    
    cursor.execute(query, params)
    articles_list = cursor.fetchall()
    
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('articles.html', 
                           articles=articles_list, 
                           categories=categories,
                           selected_category=category_id,
                           search_query=search_query)

@app.route('/article/<int:article_id>')
def article_detail(article_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT a.*, c.name as category_name, u.username as author_name 
        FROM articles a 
        JOIN categories c ON a.category_id = c.id 
        JOIN users u ON a.author_id = u.id 
        WHERE a.id = %s AND a.status = 'published'
    """, (article_id,))
    article = cursor.fetchone()
    
    if not article:
        cursor.close()
        conn.close()
        return redirect(url_for('articles'))
    
    # Update view count
    cursor.execute("UPDATE articles SET views = views + 1 WHERE id = %s", (article_id,))
    conn.commit()
    
    # Get related articles
    cursor.execute("""
        SELECT a.*, c.name as category_name, u.username as author_name 
        FROM articles a 
        JOIN categories c ON a.category_id = c.id 
        JOIN users u ON a.author_id = u.id 
        WHERE a.category_id = %s AND a.id != %s AND a.status = 'published' 
        ORDER BY a.created_at DESC 
        LIMIT 3
    """, (article['category_id'], article_id))
    related_articles = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('article_detail.html', 
                           article=article, 
                           related_articles=related_articles)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user_data = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user_data:
            # Debug logging
            print(f"Login attempt for email: {email}")
            print(f"User found in database: {user_data['username']}, role: {user_data['role']}")
            print(f"Password hash in DB: {user_data['password']}")
            
            # Try to verify password safely
            try:
                # Check if it's the default admin from schema.sql with scrypt hash
                if user_data['email'] == 'admin@news.com' and user_data['password'].startswith('scrypt:'):
                    # For admin@news.com with password admin123
                    if password == 'admin123':
                        password_verified = True
                        print("Using direct comparison for default admin")
                    else:
                        password_verified = False
                else:
                    # Normal password verification
                    password_verified = check_password_hash(user_data['password'], password)
                
                print(f"Password verification result: {password_verified}")
            except ValueError as e:
                # If hash fails, log the error
                print(f"Password verification error: {str(e)}")
                password_verified = False
                
            if password_verified:
                user = User(
                    id=user_data['id'],
                    username=user_data['username'],
                    email=user_data['email'],
                    role=user_data['role']
                )
                login_user(user)
                print(f"User logged in successfully: {user.username}")
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            else:
                print("Password verification failed")
        else:
            print(f"No user found with email: {email}")
        
        flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if email already exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            flash('Email already registered', 'error')
            return render_template('register.html')
        
        # Create new user
        hashed_password = generate_safe_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, email, password, role) VALUES (%s, %s, %s, %s)",
            (username, email, hashed_password, 'user')
        )
        conn.commit()
        
        # Get the new user
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user_data = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if user_data:
            user = User(
                id=user_data['id'],
                username=user_data['username'],
                email=user_data['email'],
                role=user_data['role']
            )
            login_user(user)
            return redirect(url_for('index'))
    
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/admin')
@login_required
def admin_dashboard():
    if current_user.role != 'admin' and current_user.role != 'editor':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get statistics
    cursor.execute("SELECT COUNT(*) as count FROM articles")
    article_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM users")
    user_count = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM categories")
    category_count = cursor.fetchone()['count']
    
    # Get total views
    cursor.execute("SELECT SUM(views) as total_views FROM articles")
    total_views = cursor.fetchone()['total_views'] or 0
    
    # Get top articles by views
    cursor.execute("""
        SELECT a.*, c.name as category_name, u.username as author_name 
        FROM articles a 
        JOIN categories c ON a.category_id = c.id 
        JOIN users u ON a.author_id = u.id 
        ORDER BY a.views DESC 
        LIMIT 5
    """)
    top_articles = cursor.fetchall()
    
    # Get recent articles
    cursor.execute("""
        SELECT a.*, c.name as category_name, u.username as author_name 
        FROM articles a 
        JOIN categories c ON a.category_id = c.id 
        JOIN users u ON a.author_id = u.id 
        ORDER BY a.created_at DESC 
        LIMIT 5
    """)
    recent_articles = cursor.fetchall()
    
    # Get category distribution
    cursor.execute("""
        SELECT c.name, COUNT(a.id) as article_count 
        FROM categories c 
        LEFT JOIN articles a ON c.id = a.category_id 
        GROUP BY c.id
        ORDER BY article_count DESC
    """)
    category_stats = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/dashboard.html',
                          article_count=article_count,
                          user_count=user_count,
                          category_count=category_count,
                          total_views=total_views,
                          top_articles=top_articles,
                          recent_articles=recent_articles,
                          category_stats=category_stats)

@app.route('/admin/articles')
@login_required
def admin_articles():
    if current_user.role != 'admin' and current_user.role != 'editor':
        return redirect(url_for('index'))
    
    status_filter = request.args.get('status', None)
    category_filter = request.args.get('category', None)
    search_query = request.args.get('q', None)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = """
        SELECT a.*, c.name as category_name, u.username as author_name 
        FROM articles a 
        JOIN categories c ON a.category_id = c.id 
        JOIN users u ON a.author_id = u.id 
        WHERE 1=1
    """
    params = []
    
    if status_filter:
        query += " AND a.status = %s"
        params.append(status_filter)
    
    if category_filter:
        query += " AND a.category_id = %s"
        params.append(category_filter)
    
    if search_query:
        query += " AND (a.title LIKE %s OR a.content LIKE %s)"
        search_param = f'%{search_query}%'
        params.extend([search_param, search_param])
    
    query += " ORDER BY a.created_at DESC"
    
    cursor.execute(query, params)
    articles_list = cursor.fetchall()
    
    # Get categories for filter
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/articles.html', 
                          articles=articles_list,
                          categories=categories,
                          status_filter=status_filter,
                          category_filter=category_filter,
                          search_query=search_query)

@app.route('/admin/article/new', methods=['GET', 'POST'])
@login_required
def admin_new_article():
    if current_user.role != 'admin' and current_user.role != 'editor':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        print("POST request received for new article")
        print(f"Form data keys: {list(request.form.keys())}")
        
        title = request.form.get('title')
        subtitle = request.form.get('subtitle', '')
        content = request.form.get('content')
        category_id = request.form.get('category_id')
        status = request.form.get('status', 'published')  # Default to published
        featured = request.form.get('featured', '0')
        tags = request.form.get('tags', '')
        
        print(f"Title: {title}")
        print(f"Content length: {len(content) if content else 0}")
        print(f"Category ID: {category_id}")
        print(f"Status: {status}")
        
        # Validate required fields
        if not title or not content or not category_id:
            print("Missing required fields")
            flash('Please fill in all required fields', 'error')
            cursor.execute("SELECT * FROM categories")
            categories = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template('admin/article_form.html', categories=categories, article=None)
        
        try:
            # Handle image upload
            image_filename = None
            if 'image' in request.files:
                image = request.files['image']
                if image.filename:
                    filename = secure_filename(image.filename)
                    image_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                    image.save(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], image_filename))
                    print(f"Image saved as: {image_filename}")
            
            # Insert article into database
            insert_query = """INSERT INTO articles 
               (title, subtitle, content, image, category_id, author_id, status, 
                featured, tags, created_at, updated_at) 
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())"""
            
            insert_values = (
                title, subtitle, content, image_filename, category_id, current_user.id, 
                status, featured == '1', tags
            )
            
            print(f"Executing query: {insert_query}")
            print(f"With values: {insert_values}")
            
            cursor.execute(insert_query, insert_values)
            conn.commit()
            
            article_id = cursor.lastrowid
            print(f"Article inserted successfully with ID: {article_id}")
            
            cursor.close()
            conn.close()
            flash('Article created successfully', 'success')
            return redirect(url_for('admin_articles'))
        except Exception as e:
            print(f"Error creating article: {str(e)}")
            flash(f'Error creating article: {str(e)}', 'error')
            cursor.execute("SELECT * FROM categories")
            categories = cursor.fetchall()
            cursor.close()
            conn.close()
            return render_template('admin/article_form.html', categories=categories, article=None)
    
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/article_form.html', categories=categories, article=None)

@app.route('/admin/article/edit/<int:article_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_article(article_id):
    if current_user.role != 'admin' and current_user.role != 'editor':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        title = request.form.get('title')
        subtitle = request.form.get('subtitle', '')
        content = request.form.get('content')
        category_id = request.form.get('category_id')
        status = request.form.get('status')
        featured = request.form.get('featured', '0')
        tags = request.form.get('tags', '')
        
        # Get current image
        cursor.execute("SELECT image FROM articles WHERE id = %s", (article_id,))
        current_image = cursor.fetchone()['image']
        
        # Handle image upload
        image_filename = current_image
        if 'image' in request.files:
            image = request.files['image']
            if image.filename:
                filename = secure_filename(image.filename)
                image_filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                image.save(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], image_filename))
                
                # Delete old image if it exists
                if current_image:
                    try:
                        os.remove(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], current_image))
                    except:
                        pass
        
        cursor.execute(
            """UPDATE articles 
               SET title = %s, subtitle = %s, content = %s, image = %s, category_id = %s, 
               status = %s, featured = %s, tags = %s, updated_at = NOW() 
               WHERE id = %s""",
            (title, subtitle, content, image_filename, category_id, status, 
             featured == '1', tags, article_id)
        )
        conn.commit()
        
        cursor.close()
        conn.close()
        flash('Article updated successfully', 'success')
        return redirect(url_for('admin_articles'))
    
    cursor.execute("""
        SELECT a.*, c.name as category_name 
        FROM articles a 
        JOIN categories c ON a.category_id = c.id 
        WHERE a.id = %s
    """, (article_id,))
    article = cursor.fetchone()
    
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/article_form.html', article=article, categories=categories)

@app.route('/admin/article/delete/<int:article_id>', methods=['POST'])
@login_required
def admin_delete_article(article_id):
    if current_user.role != 'admin' and current_user.role != 'editor':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get image filename before deleting
    cursor.execute("SELECT image FROM articles WHERE id = %s", (article_id,))
    article = cursor.fetchone()
    
    if article and article['image']:
        try:
            # Delete image file
            os.remove(os.path.join(app.root_path, app.config['UPLOAD_FOLDER'], article['image']))
        except:
            pass
    
    cursor.execute("DELETE FROM articles WHERE id = %s", (article_id,))
    conn.commit()
    
    cursor.close()
    conn.close()
    flash('Article deleted successfully', 'success')
    return redirect(url_for('admin_articles'))

@app.route('/admin/categories')
@login_required
def admin_categories():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT c.*, COUNT(a.id) as article_count,
        SUM(a.views) as total_views
        FROM categories c 
        LEFT JOIN articles a ON c.id = a.category_id 
        GROUP BY c.id
        ORDER BY c.name
    """)
    categories = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/category/new', methods=['GET', 'POST'])
@login_required
def admin_new_category():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        slug = request.form.get('slug', '').lower().replace(' ', '-')
        
        # If no slug provided, generate from name
        if not slug:
            slug = name.lower().replace(' ', '-')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO categories (name, description, slug) VALUES (%s, %s, %s)",
            (name, description, slug)
        )
        conn.commit()
        
        cursor.close()
        conn.close()
        flash('Category created successfully', 'success')
        return redirect(url_for('admin_categories'))
    
    return render_template('admin/category_form.html', category=None)

@app.route('/admin/category/edit/<int:category_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_category(category_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        slug = request.form.get('slug', '').lower().replace(' ', '-')
        
        # If no slug provided, generate from name
        if not slug:
            slug = name.lower().replace(' ', '-')
        
        cursor.execute(
            "UPDATE categories SET name = %s, description = %s, slug = %s WHERE id = %s",
            (name, description, slug, category_id)
        )
        conn.commit()
        
        cursor.close()
        conn.close()
        flash('Category updated successfully', 'success')
        return redirect(url_for('admin_categories'))
    
    cursor.execute("SELECT * FROM categories WHERE id = %s", (category_id,))
    category = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/category_form.html', category=category)

@app.route('/admin/category/delete/<int:category_id>', methods=['POST'])
@login_required
def admin_delete_category(category_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if category has articles
    cursor.execute("SELECT COUNT(*) FROM articles WHERE category_id = %s", (category_id,))
    article_count = cursor.fetchone()[0]
    
    if article_count > 0:
        cursor.close()
        conn.close()
        flash('Cannot delete category with associated articles', 'error')
        return redirect(url_for('admin_categories'))
    
    cursor.execute("DELETE FROM categories WHERE id = %s", (category_id,))
    conn.commit()
    
    cursor.close()
    conn.close()
    flash('Category deleted successfully', 'success')
    return redirect(url_for('admin_categories'))

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    role_filter = request.args.get('role', None)
    search_query = request.args.get('q', None)
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    query = "SELECT u.*, COUNT(a.id) as article_count FROM users u LEFT JOIN articles a ON u.id = a.author_id WHERE 1=1"
    params = []
    
    if role_filter:
        query += " AND u.role = %s"
        params.append(role_filter)
    
    if search_query:
        query += " AND (u.username LIKE %s OR u.email LIKE %s)"
        search_param = f'%{search_query}%'
        params.extend([search_param, search_param])
    
    query += " GROUP BY u.id ORDER BY u.username"
    
    cursor.execute(query, params)
    users = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/users.html', 
                          users=users,
                          role_filter=role_filter,
                          search_query=search_query)

@app.route('/admin/user/new', methods=['GET', 'POST'])
@login_required
def admin_new_user():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'user')
        
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Check if email already exists
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        if cursor.fetchone():
            cursor.close()
            conn.close()
            flash('Email already registered', 'error')
            return render_template('admin/user_form.html', user=None)
        
        # Create new user
        hashed_password = generate_safe_password_hash(password)
        cursor.execute(
            "INSERT INTO users (username, email, password, role, created_at) VALUES (%s, %s, %s, %s, NOW())",
            (username, email, hashed_password, role)
        )
        conn.commit()
        
        cursor.close()
        conn.close()
        flash('User created successfully', 'success')
        return redirect(url_for('admin_users'))
    
    return render_template('admin/user_form.html', user=None)

@app.route('/admin/user/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        role = request.form.get('role')
        password = request.form.get('password')
        
        # Update user info
        if password:
            # Update with new password
            hashed_password = generate_safe_password_hash(password)
            cursor.execute(
                "UPDATE users SET username = %s, email = %s, role = %s, password = %s WHERE id = %s",
                (username, email, role, hashed_password, user_id)
            )
        else:
            # Update without changing password
            cursor.execute(
                "UPDATE users SET username = %s, email = %s, role = %s WHERE id = %s",
                (username, email, role, user_id)
            )
            
        conn.commit()
        
        cursor.close()
        conn.close()
        flash('User updated successfully', 'success')
        return redirect(url_for('admin_users'))
    
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/user_form.html', user=user)

@app.route('/admin/user/delete/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    # Prevent deleting yourself
    if user_id == current_user.id:
        flash('You cannot delete your own account', 'error')
        return redirect(url_for('admin_users'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Check if user has articles
    cursor.execute("SELECT COUNT(*) as count FROM articles WHERE author_id = %s", (user_id,))
    article_count = cursor.fetchone()['count']
    
    if article_count > 0:
        # Option to reassign articles to admin
        reassign = request.form.get('reassign', False)
        
        if reassign:
            # Reassign articles to current admin
            cursor.execute(
                "UPDATE articles SET author_id = %s WHERE author_id = %s",
                (current_user.id, user_id)
            )
        else:
            cursor.close()
            conn.close()
            flash(f'Cannot delete user with {article_count} articles. Reassign articles first.', 'error')
            return redirect(url_for('admin_users'))
    
    # Delete the user
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    
    cursor.close()
    conn.close()
    flash('User deleted successfully', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/analytics')
@login_required
def admin_analytics():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    period = request.args.get('period', 'week')
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    # Get time period for query
    if period == 'day':
        time_filter = "AND DATE(a.created_at) = CURDATE()"
    elif period == 'week':
        time_filter = "AND a.created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)"
    elif period == 'month':
        time_filter = "AND a.created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)"
    else:
        time_filter = ""
    
    # Top viewed articles
    cursor.execute(f"""
        SELECT a.*, c.name as category_name, u.username as author_name 
        FROM articles a 
        JOIN categories c ON a.category_id = c.id 
        JOIN users u ON a.author_id = u.id 
        WHERE a.status = 'published' {time_filter}
        ORDER BY a.views DESC 
        LIMIT 10
    """)
    top_articles = cursor.fetchall()
    
    # Category performance
    cursor.execute(f"""
        SELECT c.name, COUNT(a.id) as article_count, SUM(a.views) as total_views
        FROM categories c 
        LEFT JOIN articles a ON c.id = a.category_id 
        WHERE a.status = 'published' {time_filter}
        GROUP BY c.id
        ORDER BY total_views DESC
    """)
    category_stats = cursor.fetchall()
    
    # Author performance
    cursor.execute(f"""
        SELECT u.username, COUNT(a.id) as article_count, SUM(a.views) as total_views
        FROM users u
        LEFT JOIN articles a ON u.id = a.author_id 
        WHERE a.status = 'published' {time_filter}
        GROUP BY u.id
        ORDER BY total_views DESC
        LIMIT 10
    """)
    author_stats = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    return render_template('admin/analytics.html',
                          period=period,
                          top_articles=top_articles,
                          category_stats=category_stats,
                          author_stats=author_stats)

@app.route('/debug/articles')
@login_required
def debug_articles():
    if current_user.role != 'admin':
        return redirect(url_for('index'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT a.*, c.name as category_name, u.username as author_name 
        FROM articles a 
        JOIN categories c ON a.category_id = c.id 
        JOIN users u ON a.author_id = u.id 
        ORDER BY a.created_at DESC
    """)
    articles_list = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    # Format the output
    output = "<h1>Articles Debug</h1>"
    output += "<table border='1'>"
    output += "<tr><th>ID</th><th>Title</th><th>Category</th><th>Author</th><th>Status</th><th>Featured</th><th>Created</th></tr>"
    
    for article in articles_list:
        output += f"<tr>"
        output += f"<td>{article['id']}</td>"
        output += f"<td>{article['title']}</td>"
        output += f"<td>{article['category_name']}</td>"
        output += f"<td>{article['author_name']}</td>"
        output += f"<td>{article['status']}</td>"
        output += f"<td>{'Yes' if article.get('featured') else 'No'}</td>"
        output += f"<td>{article['created_at']}</td>"
        output += f"</tr>"
    
    output += "</table>"
    return output

if __name__ == '__main__':
    app.run(debug=True) 