from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os
from werkzeug.utils import secure_filename
import pymysql

app = Flask(__name__, template_folder='template')
app.config['SECRET_KEY'] = 'your-secret-key'

# Create database if it doesn't exist
try:
    conn = pymysql.connect(host='localhost', user='root', password='rishu')
    with conn.cursor() as cursor:
        cursor.execute("CREATE DATABASE IF NOT EXISTS movie_review_system")
    conn.close()
except Exception as e:
    print(f"Error creating database: {e}")

app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:rishu@localhost/movie_review_system'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure upload folder with absolute path
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
print(f"Upload folder configured as: {UPLOAD_FOLDER}")

# Ensure upload directory exists
if not os.path.exists(UPLOAD_FOLDER):
    try:
        os.makedirs(UPLOAD_FOLDER)
        print(f"Created upload directory at {UPLOAD_FOLDER}")
    except Exception as e:
        print(f"Error creating upload directory: {e}")
else:
    print(f"Upload directory already exists at {UPLOAD_FOLDER}")

# Configure allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
print(f"Allowed file extensions: {ALLOWED_EXTENSIONS}")

# Configure maximum content length (16MB)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviews = db.relationship('Review', backref='user', lazy=True)

class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    genre = db.Column(db.String(100), nullable=False)
    release_year = db.Column(db.Integer, nullable=False)
    image_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviews = db.relationship('Review', backref='movie', lazy=True)
    roles = db.relationship('Role', backref='movie', lazy=True)

class Person(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    roles = db.relationship('Role', backref='person', lazy=True)

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)
    person_id = db.Column(db.Integer, db.ForeignKey('person.id'), nullable=False)
    role_type = db.Column(db.Enum('actor', 'director', 'producer', name='role_types'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Add unique constraint to prevent duplicate roles for same person in same movie
    __table_args__ = (
        db.UniqueConstraint('movie_id', 'person_id', 'role_type', name='unique_person_role_per_movie'),
    )

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movie_id = db.Column(db.Integer, db.ForeignKey('movie.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    review = db.Column(db.Text, nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes
@app.route('/')
def home():
    movies = Movie.query.all()
    return render_template('index.html', movies=movies)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return redirect(url_for('register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already exists')
            return redirect(url_for('register'))
        
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, email=email, password=hashed_password)
        db.session.add(new_user)
        db.session.commit()
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('Logged in successfully!')
            return redirect(url_for('admin_dashboard' if user.is_admin else 'user_dashboard'))
        
        flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!')
    return redirect(url_for('login'))

@app.route('/admin_dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash('Access denied!')
        return redirect(url_for('user_dashboard'))
    
    # Get all movies with their roles and reviews
    movies = Movie.query.options(
        db.joinedload(Movie.roles).joinedload(Role.person),
        db.joinedload(Movie.reviews).joinedload(Review.user)
    ).all()
    
    # Get all persons with their roles
    persons = Person.query.options(
        db.joinedload(Person.roles).joinedload(Role.movie)
    ).all()
    
    return render_template('admin_dashboard.html', movies=movies, persons=persons)

@app.route('/user_dashboard')
@login_required
def user_dashboard():
    # Get all movies with their roles and reviews
    movies = Movie.query.options(
        db.joinedload(Movie.roles).joinedload(Role.person),
        db.joinedload(Movie.reviews).joinedload(Review.user)
    ).all()
    return render_template('user_dashboard.html', movies=movies)

@app.route('/add_movie', methods=['POST'])
@login_required
def add_movie():
    if not current_user.is_admin:
        flash('Only admins can add movies')
        return redirect(url_for('user_dashboard'))
    
    try:
        title = request.form.get('title')
        genre = request.form.get('genre')
        release_year = request.form.get('release_year')
        
        print("\n=== Movie Upload Debug Info ===")
        print("Form data received:", request.form)
        print("Files received:", request.files)
        
        # Handle image upload
        image_path = None
        if 'image' not in request.files:
            print("No 'image' in request.files")
            flash('No image file provided')
            return redirect(url_for('admin_dashboard'))
            
        file = request.files['image']
        if file.filename == '':
            print("No file selected")
            flash('No file selected')
            return redirect(url_for('admin_dashboard'))
            
        print(f"File info: name={file.filename}, content_type={file.content_type}")
        
        if not allowed_file(file.filename):
            print(f"Invalid file type: {file.filename}")
            flash('Invalid file type. Allowed types are: png, jpg, jpeg, gif, webp')
            return redirect(url_for('admin_dashboard'))
        
        try:
            # Create unique filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            original_filename = secure_filename(file.filename)
            filename = f"{timestamp}_{original_filename}"
            
            # Ensure the upload folder exists
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            
            # Save the file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            print(f"Attempting to save file to: {file_path}")
            file.save(file_path)
            
            # Verify file was saved
            if os.path.exists(file_path):
                print(f"File successfully saved at: {file_path}")
                print(f"File size: {os.path.getsize(file_path)} bytes")
                # Store the path relative to static folder
                image_path = f"uploads/{filename}"
                print(f"Image path for database: {image_path}")
            else:
                raise Exception("File was not saved successfully")
                
        except Exception as e:
            print(f"Error saving file: {str(e)}")
            flash('Error saving image file')
            return redirect(url_for('admin_dashboard'))
        
        # Create movie record
        movie = Movie(
            title=title,
            genre=genre,
            release_year=release_year,
            image_path=image_path
        )
        db.session.add(movie)
        db.session.commit()
        print(f"Movie added to database with image path: {image_path}")
        flash('Movie added successfully')
        
    except Exception as e:
        print(f"Error in add_movie: {str(e)}")
        db.session.rollback()
        flash('Error adding movie')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/add_person', methods=['POST'])
@login_required
def add_person():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    name = request.form['name']
    
    new_person = Person(name=name)
    db.session.add(new_person)
    db.session.commit()
    
    flash('Person added successfully!')
    return redirect(url_for('admin_dashboard'))

@app.route('/submit_review', methods=['POST'])
@login_required
def submit_review():
    movie_id = request.form['movie_id']
    review_text = request.form['review']
    rating = int(request.form['rating'])
    
    if not 1 <= rating <= 5:
        flash('Rating must be between 1 and 5')
        return redirect(url_for('user_dashboard'))
    
    new_review = Review(
        movie_id=movie_id,
        user_id=current_user.id,
        review=review_text,
        rating=rating
    )
    db.session.add(new_review)
    db.session.commit()
    
    flash('Review submitted successfully!')
    return redirect(url_for('user_dashboard'))

@app.route('/delete_review', methods=['POST'])
@login_required
def delete_review():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    review_id = request.form['review_id']
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    
    flash('Review deleted successfully!')
    return redirect(url_for('admin_dashboard'))

@app.route('/reviews')
def get_reviews():
    reviews = Review.query.all()
    review_list = []
    for review in reviews:
        review_list.append({
            'id': review.id,
            'movie_title': review.movie.title,
            'username': review.user.username,
            'review': review.review,
            'rating': review.rating
        })
    return jsonify(review_list)

@app.route('/assign_person', methods=['POST'])
@login_required
def assign_person():
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    movie_id = request.form['movie_id']
    person_id = request.form['person_id']
    role_type = request.form['role_type']  # Get role type from form
    
    try:
        # Create new role
        new_role = Role(
            movie_id=movie_id,
            person_id=person_id,
            role_type=role_type
        )
        db.session.add(new_role)
        db.session.commit()
        flash('Person assigned to movie successfully!')
    except db.IntegrityError:
        db.session.rollback()
        flash('This person already has this role in this movie.')
    
    return redirect(url_for('admin_dashboard'))

@app.route('/delete_movie/<int:movie_id>', methods=['POST'])
@login_required
def delete_movie(movie_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    movie = Movie.query.get_or_404(movie_id)
    
    # Delete all associated roles first
    Role.query.filter_by(movie_id=movie_id).delete()
    # Delete all associated reviews
    Review.query.filter_by(movie_id=movie_id).delete()
    # Finally delete the movie
    db.session.delete(movie)
    db.session.commit()
    
    return jsonify({'message': 'Movie deleted successfully'})

@app.route('/delete_person/<int:person_id>', methods=['POST'])
@login_required
def delete_person(person_id):
    if not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    
    person = Person.query.get_or_404(person_id)
    
    # Delete all associated roles first
    Role.query.filter_by(person_id=person_id).delete()
    # Finally delete the person
    db.session.delete(person)
    db.session.commit()
    
    return jsonify({'message': 'Person deleted successfully'})

if __name__ == '__main__':
    with app.app_context():
        try:
            # Create all tables if they don't exist
            db.create_all()
            print("Database tables are ready!")
            
            # Create admin user if it doesn't exist
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                admin = User(
                    username='admin',
                    email='admin@example.com',
                    password=generate_password_hash('admin123'),
                    is_admin=True
                )
                db.session.add(admin)
                db.session.commit()
                print("Admin user created successfully!")
            else:
                print("Admin user already exists")
        except Exception as e:
            print(f"Error initializing database: {e}")
            db.session.rollback()
    
    app.run(host='127.0.0.1', port=5000, debug=True)
