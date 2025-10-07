import pandas as pd
from config import db

df = pd.read_csv("Goodreads.csv")
cursor = db.cursor()

df = df.drop_duplicates(subset='Title')

for _, row in df.iterrows():
    Title = row['Title']
    cursor.execute("SELECT COUNT(*) FROM books WHERE Title = %s", (Title,))
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO books (title, author, genres, isbn, rating)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            row['Title'], row['Author'], row['genres'],
            row['isbn'], row['average_rating']
        ))

db.commit()
print("Books imported successfully without duplicates")
