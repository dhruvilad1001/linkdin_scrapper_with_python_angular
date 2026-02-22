from flask import Flask
from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)

@app.route('/')
def hello():
    try:
        # Test MongoDB connection
        client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
        client.admin.command('ping')
        db_status = "MongoDB Connected ✓"
        client.close()
    except Exception as e:
        db_status = f"MongoDB Error: {str(e)}"
    
    return f"""
    <html>
    <body>
        <h1>LinkedIn Scraper Status</h1>
        <p>Flask: Working ✓</p>
        <p>Database: {db_status}</p>
        <p>Environment: {os.getenv('DATABASE_NAME', 'Not loaded')}</p>
    </body>
    </html>
    """

if __name__ == '__main__':
    app.run(debug=True, port=5000)