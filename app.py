from flask import Flask, render_template, request, redirect, session, url_for
from config import db
import hashlib
import os

app = Flask(__name__)

@app.route('/')
def index():
    if not session.get('saw_splash'):
        return redirect(url_for('splash'))

    if 'user_id' in session:
        return redirect(url_for('home'))
    return redirect(url_for('login'))


@app.route('/splash')
def splash():
    session['saw_splash'] = True
    return render_template('splash.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('home'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username=%s AND password=%s", (username, password))
        user = cursor.fetchone()
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('home'))
        else:
            return "Invalid credentials"
    return render_template('login.html')



@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        cursor = db.cursor()
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", (username, password))
        db.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

########################################################
@app.route('/home', methods=['GET', 'POST'])
def home():
    if 'user_id' not in session:
        return redirect('/login')

    cursor = db.cursor()
    search_query = request.form.get('search') if request.method == 'POST' else None

    query = "SELECT book_id, title, author, genres, rating, isbn FROM books"
    if search_query:
        query += " WHERE title LIKE %s"
        cursor.execute(query, (f"%{search_query}%",))
    else:
        cursor.execute(query)
    books = cursor.fetchall()

    return render_template('home.html', books=books)

########################################################
@app.route('/filter', methods=['GET', 'POST'])
def filter_books():
    if 'user_id' not in session:
        return redirect('/login')

    cursor = db.cursor()
    genre_filter = request.form.get('genre') if request.method == 'POST' else None
    rating_filter = request.form.get('rating') if request.method == 'POST' else None

    query = "SELECT book_id, title, author, genres, rating, isbn FROM books WHERE 1=1"
    filters = []

    if genre_filter and genre_filter != 'All':
        query += " AND genres = %s"
        filters.append(genre_filter)

    if rating_filter:
        query += " AND rating >= %s"
        filters.append(rating_filter)

    cursor.execute(query, tuple(filters))
    books = cursor.fetchall()

    cursor.execute("SELECT DISTINCT genres FROM books")
    genres = [row[0] for row in cursor.fetchall() if row[0]]

    return render_template('filter.html', books=books, genres=genres)

#########################################################
@app.route('/reading_list', methods=['GET'])
def reading_list():
    if 'user_id' not in session:
        return redirect('/login')

    user_id = session['user_id']
    search_query = request.args.get('search', '').lower()

    cursor = db.cursor()

    query = """
        SELECT b.book_id, b.title, b.author, b.genres, b.rating, b.isbn, r.status
        FROM books b
        JOIN reading_list r ON b.book_id = r.book_id
        WHERE r.user_id = %s
    """
    cursor.execute(query, (user_id,))
    books = cursor.fetchall()

    if search_query:
        books = [
            book for book in books
            if search_query in book[1].lower() or
               search_query in book[2].lower() or
               search_query in book[3].lower()
        ]

    categorized = {
        'Want To Read': [],
        'Reading': [],
        'Read': []
    }

    for book in books:
        status = book[6]
        if status in categorized:
            categorized[status].append(book)
        else:
            categorized[status] = [book]

    return render_template('reading_list.html', reading_list=categorized, search_query=search_query)

#################################################################
@app.route('/update_status', methods=['POST'])
def update_status():
    if 'user_id' not in session:
        return redirect('/login')

    book_id = request.form['book_id']
    status = request.form['status']
    user_id = session['user_id']

    cursor = db.cursor()
    if status == "Remove":
        cursor.execute("DELETE FROM reading_list WHERE user_id = %s AND book_id = %s", (user_id, book_id))
    else:
        cursor.execute("SELECT * FROM reading_list WHERE user_id = %s AND book_id = %s", (user_id, book_id))
        if cursor.fetchone():
            cursor.execute("UPDATE reading_list SET status = %s WHERE user_id = %s AND book_id = %s", (status, user_id, book_id))
        else:
            cursor.execute("INSERT INTO reading_list (user_id, book_id, status) VALUES (%s, %s, %s)", (user_id, book_id, status))

    db.commit()
    return redirect(request.referrer or "{{ url_for('reading_list') }}" )

###########################################################
@app.route('/recommend')
def recommend():
    if 'user_id' not in session:
        return redirect('/login')

    cursor = db.cursor()
    cursor.execute("""
        SELECT DISTINCT b.genres
        FROM books b
        JOIN reading_list r ON b.book_id = r.book_id
        WHERE r.user_id = %s AND r.status IN ('Reading', 'Read')
    """, (session['user_id'],))

    genres = [row[0] for row in cursor.fetchall() if row[0]]

    if genres:
        format_strings = ','.join(['%s'] * len(genres))
        cursor.execute(f"""
            SELECT DISTINCT book_id, title, author, genres, rating, isbn
            FROM books
            WHERE genres IN ({format_strings})
            AND book_id NOT IN (SELECT book_id FROM reading_list WHERE user_id = %s)
            LIMIT 10
        """, (*genres, session['user_id']))
        recommendations = cursor.fetchall()
    else:
        recommendations = []

    return render_template('recommend.html', recommendations=recommendations)
@app.route('/reviews/<int:book_id>')
def reviews(book_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cursor = db.cursor()
    cursor.execute("SELECT book_id, title, author, genres, rating, isbn FROM books WHERE book_id = %s", (book_id,))
    book = cursor.fetchone()

    cursor.execute("SELECT rating, review FROM reviews WHERE user_id = %s AND book_id = %s", (session['user_id'], book_id))
    row = cursor.fetchone()
    review = {'rating': row[0], 'review': row[1]} if row else None

    return render_template("reviews.html", book=book, review=review)

@app.route('/submit_review', methods=['POST'])
def submit_review():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    book_id = request.form['book_id']
    rating = request.form.get('rating')
    review_text = request.form.get('review')

    cursor = db.cursor()
    cursor.execute("SELECT * FROM reviews WHERE user_id = %s AND book_id = %s", (user_id, book_id))
    if cursor.fetchone():
        cursor.execute("""
            UPDATE reviews SET rating = %s, review = %s
            WHERE user_id = %s AND book_id = %s
        """, (rating, review_text, user_id, book_id))
    else:
        cursor.execute("""
            INSERT INTO reviews (user_id, book_id, rating, review)
            VALUES (%s, %s, %s, %s)
        """, (user_id, book_id, rating, review_text))

    db.commit()
    return redirect(url_for('reviews', book_id=book_id))

@app.route('/delete_review', methods=['POST'])
def delete_review():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    book_id = request.form['book_id']

    cursor = db.cursor()
    cursor.execute("DELETE FROM reviews WHERE user_id = %s AND book_id = %s", (user_id, book_id))
    db.commit()

    return redirect(url_for('reviews', book_id=book_id))
@app.route('/my_reviews')
def my_reviews():
    if 'user_id' not in session:
        return redirect('/login')

    cursor = db.cursor()
    cursor.execute("""
        SELECT b.book_id, b.title, b.author, b.genres, b.rating, b.isbn, r.rating, r.review
        FROM books b
        JOIN reviews r ON b.book_id = r.book_id
        WHERE r.user_id = %s
    """, (session['user_id'],))
    reviews = cursor.fetchall()

    return render_template('my_reviews.html', reviews=reviews)
    
if __name__ == '__main__':
    app.run(debug=True)

