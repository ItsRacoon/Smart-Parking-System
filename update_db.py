import sqlite3
import os

# Get the database file path
# Try both possible locations
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance', 'parking.db')
if not os.path.exists(DB_PATH):
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'parking.db')

def update_payment_table():
    """Update the payment table to add new columns for Razorpay integration"""
    if not os.path.exists(DB_PATH):
        print(f"Database file not found at: {DB_PATH}")
        return
        
    print(f"Updating database at: {DB_PATH}")
    
    try:
        # Connect to the database
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check if the payment table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='payment'")
        if not cursor.fetchone():
            print("Payment table does not exist, skipping update")
            conn.close()
            return
        
        # Check if the columns already exist
        cursor.execute("PRAGMA table_info(payment)")
        columns = [column[1] for column in cursor.fetchall()]
    except Exception as e:
        print(f"Error connecting to database: {str(e)}")
        return
    
    try:
        # Add new columns if they don't exist
        new_columns = {
            'payment_id': 'VARCHAR(100)',
            'currency': 'VARCHAR(3) DEFAULT "INR"',
            'payment_data': 'TEXT'
        }
        
        for column_name, column_type in new_columns.items():
            if column_name not in columns:
                print(f"Adding column {column_name} to payment table")
                cursor.execute(f"ALTER TABLE payment ADD COLUMN {column_name} {column_type}")
        
        # Rename timestamp column to payment_date if it exists
        if 'timestamp' in columns and 'payment_date' not in columns:
            print("Renaming timestamp column to payment_date")
            try:
                # SQLite doesn't support direct column renaming, so we need to create a new table
                cursor.execute("""
                CREATE TABLE payment_new (
                    id INTEGER PRIMARY KEY,
                    booking_id INTEGER NOT NULL,
                    amount FLOAT NOT NULL,
                    payment_method VARCHAR(50) NOT NULL,
                    transaction_id VARCHAR(100),
                    payment_id VARCHAR(100),
                    status VARCHAR(20) DEFAULT 'Pending',
                    payment_date DATETIME,
                    currency VARCHAR(3) DEFAULT 'INR',
                    payment_data TEXT,
                    FOREIGN KEY (booking_id) REFERENCES booking (id)
                )
                """)
                
                # Copy data from old table to new table
                cursor.execute("""
                INSERT INTO payment_new (id, booking_id, amount, payment_method, transaction_id, status, payment_date)
                SELECT id, booking_id, amount, payment_method, transaction_id, status, timestamp
                FROM payment
                """)
                
                # Drop old table and rename new table
                cursor.execute("DROP TABLE payment")
                cursor.execute("ALTER TABLE payment_new RENAME TO payment")
            except Exception as e:
                print(f"Error renaming timestamp column: {str(e)}")
        
        # Add status column if it doesn't exist
        if 'status' not in columns:
            print("Adding status column to payment table")
            cursor.execute("ALTER TABLE payment ADD COLUMN status VARCHAR(20) DEFAULT 'Pending'")
        
        # Commit changes and close connection
        conn.commit()
        conn.close()
        
        print("Database update completed successfully")
    except Exception as e:
        print(f"Error updating database: {str(e)}")
        try:
            conn.close()
        except:
            pass
    
if __name__ == "__main__":
    update_payment_table()