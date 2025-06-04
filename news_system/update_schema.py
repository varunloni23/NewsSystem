import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'news_system')
}

def update_schema():
    """Update the database schema to add missing columns"""
    connection = None
    try:
        # Connect to the database
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        print("Connected to the database successfully")
        
        # Check if columns exist
        cursor.execute("SHOW COLUMNS FROM articles LIKE 'subtitle'")
        has_subtitle = cursor.fetchone() is not None
        
        cursor.execute("SHOW COLUMNS FROM articles LIKE 'featured'")
        has_featured = cursor.fetchone() is not None
        
        cursor.execute("SHOW COLUMNS FROM articles LIKE 'tags'")
        has_tags = cursor.fetchone() is not None
        
        # Add missing columns
        if not has_subtitle:
            print("Adding 'subtitle' column...")
            cursor.execute("ALTER TABLE articles ADD COLUMN subtitle VARCHAR(255) AFTER title")
            print("Added 'subtitle' column successfully")
        else:
            print("'subtitle' column already exists")
            
        if not has_featured:
            print("Adding 'featured' column...")
            cursor.execute("ALTER TABLE articles ADD COLUMN featured BOOLEAN DEFAULT FALSE AFTER status")
            print("Added 'featured' column successfully")
        else:
            print("'featured' column already exists")
            
        if not has_tags:
            print("Adding 'tags' column...")
            cursor.execute("ALTER TABLE articles ADD COLUMN tags VARCHAR(255) AFTER featured")
            print("Added 'tags' column successfully")
        else:
            print("'tags' column already exists")
        
        connection.commit()
        print("Schema update completed successfully")
        
    except Error as e:
        print(f"Error: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection closed")

if __name__ == "__main__":
    update_schema() 