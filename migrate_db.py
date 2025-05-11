from flask import Flask
from models import db
import sqlite3
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/parking.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def add_selection_method_column():
    """Add selection_method column to the booking table if it doesn't exist"""
    db_path = os.path.join('instance', 'parking.db')
    
    if not os.path.exists(db_path):
        print(f"Database file not found at {db_path}")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(booking)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'selection_method' not in columns:
        print("Adding selection_method column to booking table...")
        cursor.execute("ALTER TABLE booking ADD COLUMN selection_method VARCHAR(20) DEFAULT 'Manual'")
        conn.commit()
        print("Column added successfully")
    else:
        print("selection_method column already exists")
    
    conn.close()

if __name__ == '__main__':
    with app.app_context():
        add_selection_method_column()