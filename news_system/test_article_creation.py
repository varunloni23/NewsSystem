import os
import mysql.connector
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

# Database connection
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD', ''),
        database=os.getenv('DB_NAME', 'news_system')
    )

def test_article_creation():
    """Test creating an article directly in the database"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        print("Connected to database successfully")
        
        # Test data
        title = "Test Article"
        subtitle = "Test Subtitle"
        content = "This is a test article content."
        image_filename = None
        category_id = 1  # Make sure this category exists
        author_id = 1    # Make sure this user exists
        status = "published"
        featured = True
        tags = "test, article"
        
        # Insert article into database
        insert_query = """INSERT INTO articles 
           (title, subtitle, content, image, category_id, author_id, status, 
            featured, tags, created_at, updated_at) 
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())"""
        
        insert_values = (
            title, subtitle, content, image_filename, category_id, author_id, 
            status, featured, tags
        )
        
        print(f"Executing query: {insert_query}")
        print(f"With values: {insert_values}")
        
        cursor.execute(insert_query, insert_values)
        conn.commit()
        
        article_id = cursor.lastrowid
        print(f"Article inserted successfully with ID: {article_id}")
        
        # Verify the article was created
        cursor.execute("SELECT * FROM articles WHERE id = %s", (article_id,))
        article = cursor.fetchone()
        
        if article:
            print("Article verified in database:")
            print(f"ID: {article['id']}")
            print(f"Title: {article['title']}")
            print(f"Status: {article['status']}")
            print(f"Featured: {article['featured']}")
        else:
            print("Failed to retrieve the article from database")
        
        cursor.close()
        conn.close()
        print("Database connection closed")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    test_article_creation() 