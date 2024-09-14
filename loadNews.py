import feedparser
import pandas as pd
import psycopg2
from psycopg2 import sql
from dateutil import parser
from bs4 import BeautifulSoup

# URL of the RSS feed
csv_file = 'data/newsSources.csv'
df = pd.read_csv(csv_file, encoding='UTF-8')

# Database connection details
conn = psycopg2.connect(
    dbname="news_b5qj",
    user="news_b5qj_user",
    password="gdUyyzbLbc5fJtBhXFMDL1LqMiCBiS6t",
    host="dpg-criuujqj1k6c73fiep8g-a",
    port="5432"
)
cur = conn.cursor()

for row in df['links']:
    if row != '.':
        url = row
        print(f"Parsing URL: {url}")
        feed = feedparser.parse(url)

        if not feed.entries:
            print(feed)
            print(f"No entries found for URL: {url}")

        
        for entry in feed.entries:
            if 'title' in entry and 'link' in entry and 'published' in entry:
                title = entry.title
                link = entry.link
                try:
                    publish_date = parser.parse(entry.published)
                except ValueError as e:
                    print(f"Failed to parse date: {entry.published}")
                    print(f"Error: {e}")
                    continue  # Skip this entry and continue with the next one
                
                description = ''
                if 'description' in entry:
                    description = entry.description
                elif 'summary' in entry:
                    description = entry.summary

                # Clean HTML tags using BeautifulSoup
                description = BeautifulSoup(description, "lxml").get_text()

                # Truncate long descriptions
                max_length = 220  # Adjust this length as needed
                if len(description) > max_length:
                    description = description[:max_length] + "..."

                print(f"Inserting news: {title}")

                # Insert the data into the PostgreSQL table
                insert_query = sql.SQL(
                    "INSERT INTO news (title, link, publish_date, description) VALUES (%s, %s, %s, %s)"
                )
                cur.execute(insert_query, (title, link, publish_date, description))

# Commit the transaction and close the connection
conn.commit()
cur.close()
conn.close()
                
            

