from flask import Flask, render_template, request, redirect, session, flash
from sqlalchemy.exc import IntegrityError
import os 
import psycopg2
from forms import SignupForm
from forms import LoginForm
from models import  User
from flask import g
from models import Favorite


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgresql:///news'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")

from models import db, connect_db

connect_db(app)

CURR_USER_KEY = "curr_user"

# Database connection details
def get_db_connection():
    conn = psycopg2.connect(
        dbname="news",
        user="carlinha",
        password="240291",
        host="localhost",
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
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT title, link, publish_date, description FROM news ORDER BY publish_date DESC;")
    news_items = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('index.html', news_items=news_items)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q')
    conn = get_db_connection()
    cur = conn.cursor()

    if query:
        cur.execute(
            "SELECT title, link, publish_date, description FROM news WHERE title ILIKE %s OR publish_date::text ILIKE %s ORDER BY publish_date DESC;",
            (f'%{query}%', f'%{query}%')
        )
    else:
        cur.execute("SELECT title, link, publish_date, description FROM news ORDER BY publish_date DESC;")

    search_results = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('index.html', news_items=search_results)

@app.route('/saved_news')
def view_saved_news():
    if not g.user:
        flash("You need to log in to view your saved news.", "warning")
        return redirect("/login")

    saved_news = Favorite.query.filter_by(user_id=g.user.id).all()

    return render_template('saved_news.html', saved_news=saved_news)


if __name__ == '__main__':
    app.run(debug=True)