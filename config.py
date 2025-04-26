import os
import mysql.connector

db = mysql.connector.connect(
    host=os.getenv('localhost'),
    user=os.getenv('root'),
    password=os.getenv('btsgot7svt'),
    database=os.getenv('bookalmost'),
    ssl_ca=os.getenv('SSL_CERT', None)  # PlanetScale uses SSL
)
