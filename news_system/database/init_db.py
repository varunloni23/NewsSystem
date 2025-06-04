import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
}

DB_NAME = os.getenv('DB_NAME', 'news_system')

def create_database():
    """Create the database and tables if they don't exist"""
    connection = None
    try:
        # Connect to MySQL server
        connection = mysql.connector.connect(**DB_CONFIG)
        cursor = connection.cursor()
        
        # Create database if it doesn't exist
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}")
        print(f"Database '{DB_NAME}' created or already exists.")
        
        # Switch to the database
        cursor.execute(f"USE {DB_NAME}")
        
        # Read and execute the schema.sql file
        with open(os.path.join(os.path.dirname(__file__), 'schema.sql'), 'r') as f:
            # Split the file into individual statements
            sql_commands = f.read().split(';')
            for command in sql_commands:
                # Skip empty commands
                if command.strip():
                    cursor.execute(command)
        
        connection.commit()
        print("Database schema created successfully.")
        
    except Error as e:
        print(f"Error: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection closed.")

def create_sample_data():
    """Create sample data for the news system"""
    connection = None
    try:
        # Connect to the database
        db_config = DB_CONFIG.copy()
        db_config['database'] = DB_NAME
        connection = mysql.connector.connect(**db_config)
        cursor = connection.cursor()
        
        # Check if there are already articles
        cursor.execute("SELECT COUNT(*) FROM articles")
        article_count = cursor.fetchone()[0]
        
        if article_count > 0:
            print("Sample data already exists. Skipping...")
            return
        
        # Get admin user ID
        cursor.execute("SELECT id FROM users WHERE email = 'admin@news.com'")
        admin_id = cursor.fetchone()[0]
        
        # Sample articles
        sample_articles = [
            (
                "The Future of Artificial Intelligence",
                "Artificial intelligence (AI) is rapidly transforming our world. From self-driving cars to virtual assistants, AI technologies are becoming increasingly integrated into our daily lives. This article explores the latest developments in AI research and their potential impact on society.\n\nRecent breakthroughs in machine learning, particularly in deep learning algorithms, have enabled computers to perform tasks that once required human intelligence. These advancements have led to significant improvements in image recognition, natural language processing, and decision-making capabilities.\n\nHowever, as AI continues to evolve, it raises important questions about ethics, privacy, and the future of work. Experts are divided on whether AI will create more jobs than it eliminates, but most agree that it will fundamentally change the nature of work across many industries.\n\nAs we navigate this technological revolution, it is crucial to develop frameworks that ensure AI is developed and deployed responsibly, with appropriate safeguards to protect against potential risks.",
                "ai_future.jpg",
                3,  # Technology category
                admin_id,
                "published",
                42
            ),
            (
                "Global Economic Outlook for 2023",
                "The global economy faces significant challenges and opportunities in 2023. Following years of pandemic-related disruptions, inflation concerns, and supply chain issues, economists are cautiously optimistic about the path forward.\n\nInflation, which reached multi-decade highs in many countries during 2022, is showing signs of moderating. Central banks worldwide have implemented aggressive monetary tightening policies, which appear to be having the desired effect of cooling price pressures without triggering a severe recession.\n\nSupply chains, which experienced unprecedented disruptions during the pandemic, are gradually normalizing. However, geopolitical tensions and the ongoing transition to more resilient and localized supply networks continue to present challenges for global trade.\n\nEmerging markets, particularly in Asia, are expected to drive global growth in 2023. Countries with strong domestic demand and limited exposure to external shocks are positioned to outperform.\n\nDespite these positive signs, risks remain. Energy price volatility, potential new COVID variants, and escalating geopolitical conflicts could all derail the fragile recovery. Policymakers must remain vigilant and flexible in their approach to economic management.",
                "economy_2023.jpg",
                2,  # Business category
                admin_id,
                "published",
                35
            ),
            (
                "Breakthrough in Renewable Energy Storage",
                "Scientists have announced a significant breakthrough in renewable energy storage technology, potentially solving one of the biggest challenges facing the transition to clean energy.\n\nThe new battery technology, developed by researchers at a leading university, can store large amounts of energy for extended periods at a fraction of the cost of current solutions. This advancement could make renewable energy sources like solar and wind more reliable and competitive with fossil fuels.\n\n\"This is a game-changer for the renewable energy industry,\" said Dr. Sarah Chen, the lead researcher. \"Our technology addresses the intermittency problem that has long been a barrier to widespread adoption of renewable energy.\"\n\nThe innovative approach uses abundant, non-toxic materials and can be manufactured using existing production facilities, making it potentially scalable in the near term.\n\nEnergy experts predict that if successfully commercialized, this technology could accelerate the global transition to renewable energy and significantly reduce carbon emissions within the next decade.",
                "renewable_energy.jpg",
                3,  # Technology category
                admin_id,
                "published",
                28
            ),
            (
                "The Rise of Plant-Based Diets",
                "Plant-based diets are experiencing unprecedented popularity worldwide, driven by health concerns, environmental awareness, and ethical considerations.\n\nRecent studies have linked plant-based eating patterns to numerous health benefits, including reduced risk of heart disease, certain cancers, and type 2 diabetes. Nutritionists point out that well-planned plant-based diets can provide all necessary nutrients while being rich in fiber, antioxidants, and phytonutrients.\n\nEnvironmental impact is another significant factor driving this trend. Research indicates that plant-based diets generally have a smaller carbon footprint than diets high in animal products. As climate change concerns grow, many individuals are adopting plant-based eating as a personal environmental action.\n\nThe food industry has responded to this shift with an explosion of plant-based alternatives to meat, dairy, and eggs. These products have improved dramatically in taste and texture in recent years, making the transition to plant-based eating more accessible for mainstream consumers.\n\nWhile strict veganism continues to grow, many people are adopting flexitarian approaches, reducing animal product consumption without eliminating it entirely. This balanced approach may be more sustainable for many individuals long-term.",
                "plant_based_diet.jpg",
                6,  # Health category
                admin_id,
                "published",
                31
            ),
            (
                "Major Sporting Event Announces Sustainability Initiative",
                "One of the world's largest sporting events has announced a comprehensive sustainability initiative aimed at making the event carbon-neutral by 2025.\n\nThe ambitious plan includes powering venues with 100% renewable energy, implementing zero-waste policies, offsetting travel emissions, and using sustainable materials throughout the event's infrastructure.\n\n\"Sports have a unique power to inspire and influence,\" said the event's director. \"We want to use our platform to demonstrate that large-scale events can be held responsibly and sustainably.\"\n\nThe initiative also includes community engagement programs, educational components for attendees, and partnerships with environmental organizations to maximize positive impact.\n\nSustainability experts have praised the move, noting that high-profile events adopting such practices can help normalize environmental responsibility across industries and influence millions of fans worldwide.",
                "sports_sustainability.jpg",
                4,  # Sports category
                admin_id,
                "published",
                24
            ),
            (
                "Award-Winning Film Director Announces New Project",
                "Acclaimed film director Alexandra Rodriguez has announced her next project, a psychological thriller set against the backdrop of climate change.\n\nThe film, titled \"Tipping Point,\" will explore the psychological impact of environmental anxiety through the story of a climate scientist who makes a breakthrough discovery with far-reaching implications.\n\n\"I wanted to create something that addresses one of the most pressing issues of our time, but through a deeply human lens,\" Rodriguez explained at a press conference. \"This isn't just a film about climate change—it's about how we face existential threats and find meaning in uncertain times.\"\n\nRodriguez, whose previous film won multiple awards including Best Director at several international film festivals, has assembled an impressive cast including several A-list actors who have been vocal about environmental causes.\n\nProduction is scheduled to begin next month, with filming locations in several countries particularly affected by climate change. The film is expected to be released in late 2024.",
                "film_director.jpg",
                5,  # Entertainment category
                admin_id,
                "published",
                19
            )
        ]
        
        # Insert sample articles
        for article in sample_articles:
            cursor.execute("""
                INSERT INTO articles 
                (title, content, image, category_id, author_id, status, views, created_at, updated_at) 
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, article)
        
        connection.commit()
        print("Sample data created successfully.")
        
    except Error as e:
        print(f"Error: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == "__main__":
    print("Initializing database...")
    create_database()
    
    # Wait a moment to ensure database is ready
    time.sleep(1)
    
    print("\nCreating sample data...")
    create_sample_data()
    
    print("\nDatabase setup complete!") 