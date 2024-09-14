from flask import Flask, render_template, request, redirect, session, flash, url_for
from sqlalchemy.exc import IntegrityError
import os 
import psycopg2
from forms import SignupForm
from forms import LoginForm
from models import  User
from flask import g
from models import Favorite
from models import News

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgresql:///news_b5qj'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")

from models import db, connect_db

connect_db(app)

CURR_USER_KEY = "curr_user"

# Database connection details
def get_db_connection():
    conn = psycopg2.connect(
        dbname="news_b5qj",
        user="news_b5qj_user",
        password="gdUyyzbLbc5fJtBhXFMDL1LqMiCBiS6t",
        host="dpg-criuujqj1k6c73fiep8g-a",
        port="5432"
    )
    return conn


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id
    session['username'] = user.username # Store username in session


def do_logout():
    """Logout user."""

    if CURR_USER_KEY in session:
        session.pop(CURR_USER_KEY)
    if 'username' in session:
        session.pop('username')

def delete_duplicate_news():
    conn = get_db_connection()
    cur = conn.cursor()

    # Use a CTE (Common Table Expression) to find and delete duplicates based on the 'link' column
    cur.execute("""
        DELETE FROM news
        WHERE id IN (
            SELECT id FROM (
                SELECT id, ROW_NUMBER() OVER (PARTITION BY link ORDER BY id) AS row_num
                FROM news
            ) t
            WHERE t.row_num > 1
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


# Function to load the currently logged-in user before each request
@app.before_request
def add_user_to_g():
    """If we're logged in, add the curr user to Flask global."""
    
    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])
    else:
        g.user = None


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """
    form = SignupForm()
    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                email=form.email.data,
                password=form.password.data
            )
            db.session.commit()
            flash("Signup successful!", "success")
            return redirect('/login')
        except IntegrityError:
            db.session.rollback()
            flash("Username or email already taken", "danger")

    return render_template('signup.html', form=form)

@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""

    do_logout()
    flash("Goodbye!", "info")
    return redirect('/')

def do_logout():
    """Logout user."""
    
    if CURR_USER_KEY in session:
        session.pop(CURR_USER_KEY)

@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('/index.html', users=users)



@app.route('/')
def index():
    delete_duplicate_news()

    conn = get_db_connection()
    cur = conn.cursor()
    
    per_page = 7
    page = request.args.get('page', 1, type=int)
    offset = (page - 1) * per_page
    
    cur.execute("SELECT title, link, publish_date, description FROM news ORDER BY publish_date DESC LIMIT %s OFFSET %s;", (per_page, offset))
    news_items = cur.fetchall()

    cur.execute("SELECT COUNT(*) FROM news;")
    total_news = cur.fetchone()[0]
    cur.close()
    conn.close()

    total_pages = (total_news + per_page - 1) // per_page

    # Calculate which page numbers to show
    num_visible_pages = 5
    start_page = max(1, page - 2)
    end_page = min(start_page + num_visible_pages - 1, total_pages)
    if end_page - start_page + 1 < num_visible_pages:
        start_page = max(1, end_page - num_visible_pages + 1)

    return render_template('index.html', news_items=news_items, page=page, total_pages=total_pages, start_page=start_page, end_page=end_page)




@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '')
    page = request.args.get('page', 1, type=int)
    per_page = 7
    offset = (page - 1) * per_page

    conn = get_db_connection()
    cur = conn.cursor()

    # Modify your search query as needed for title or date search
    cur.execute("SELECT title, link, publish_date, description FROM news WHERE title ILIKE %s OR publish_date::text ILIKE %s LIMIT %s OFFSET %s;", 
                (f"%{query}%", f"%{query}%", per_page, offset))
    search_results = cur.fetchall()

    # Get the total count of results for pagination
    cur.execute("SELECT COUNT(*) FROM news WHERE title ILIKE %s OR publish_date::text ILIKE %s;", 
                (f"%{query}%", f"%{query}%",))
    total_search_results = cur.fetchone()[0]
    cur.close()
    conn.close()

    total_pages = (total_search_results + per_page - 1) // per_page

    # Calculate which page numbers to show
    num_visible_pages = 5
    start_page = max(1, page - 2)
    end_page = min(start_page + num_visible_pages - 1, total_pages)
    if end_page - start_page + 1 < num_visible_pages:
        start_page = max(1, end_page - num_visible_pages + 1)

    return render_template('index.html', news_items=search_results, page=page, total_pages=total_pages, start_page=start_page, end_page=end_page)


@app.route('/saved_news')
def view_saved_news():
    if not g.user:
        flash("You need to log in to view your saved news.", "warning")
        return redirect("/login")

    saved_news = Favorite.query.filter_by(user_id=g.user.id).all()

    return render_template('saved_news.html', saved_news=saved_news)

@app.route('/save_favorite', methods=['POST'])
def save_favorite():
    if not g.user:
        flash("You need to log in to save news.", "warning")
        return redirect(url_for('login'))

    # Retrieve form data from the request
    news_title = request.form['news_title']
    news_link = request.form['news_link']
    publish_date = request.form['publish_date']
    description = request.form['description']

    # Check if this news item is already saved for this user
    existing_favorite = Favorite.query.filter_by(user_id=g.user.id, news_title=news_title).first()

    if existing_favorite:
        flash("You already saved this news item.", "info")
    else:
        # Save the new favorite news item for the current user
        new_favorite = Favorite(
            user_id=g.user.id,
            news_title=news_title,
            news_link=news_link,
            publish_date=publish_date,
            description=description
        )
        db.session.add(new_favorite)
        db.session.commit()
        flash("News saved successfully!", "success")

    return redirect(url_for('index'))


if __name__ == '__main__':
    app.run(debug=True)