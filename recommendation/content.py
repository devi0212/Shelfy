import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from config import db

def get_content_recommendations(book_id, user_id=None, top_n=5):
    cursor = db.cursor()

    # Fetch all books
    cursor.execute("SELECT book_id, title, genres, author FROM books")
    books = cursor.fetchall()
    df = pd.DataFrame(books, columns=['book_id', 'title', 'genres', 'author'])
    
    df['genres'] = df['genres'].fillna('')
    df['author'] = df['author'].fillna('')
    df['title'] = df['title'].fillna('')
    df['text'] = (
        df['title'] + ' ' +
        (df['genres'] + ' ') * 3 +  
        df['author']
    ).str.lower().str.strip()

    # TF-IDF Vectorization
    tfidf = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
    tfidf_matrix = tfidf.fit_transform(df['text'])

    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

    if user_id:
        cursor.execute("SELECT book_id, rating FROM reviews WHERE user_id = %s", (user_id,))
        user_reviews = cursor.fetchall()

        if not user_reviews:
            return []  

        score_map = {}
        for reviewed_id, rating in user_reviews:
            try:
                idx = df.index[df['book_id'] == reviewed_id][0]
                sim_scores = list(enumerate(cosine_sim[idx]))
                for i, score in sim_scores:
                    if df.iloc[i]['book_id'] == reviewed_id:
                        continue  
                    score_map[i] = score_map.get(i, 0) + score * rating
            except IndexError:
                continue

        sorted_scores = sorted(score_map.items(), key=lambda x: x[1], reverse=True)
        top_indices = [i[0] for i in sorted_scores[:top_n]]
    else:
        try:
            idx = df.index[df['book_id'] == int(book_id)][0]
        except IndexError:
            return []

        sim_scores = list(enumerate(cosine_sim[idx]))
        sim_scores = sorted(sim_scores, key=lambda x: x[1], reverse=True)[1:top_n+1]
        top_indices = [i[0] for i in sim_scores]

    recommended_books = df.iloc[top_indices][['book_id', 'title', 'genres']].values.tolist()
    return recommended_books
