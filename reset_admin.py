import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy import text
from src.auth.user_store import create_user, engine

def reset():
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM users WHERE username='admin'"))
    
    try:
        create_user('admin', 'admin')
        print("Admin user created successfully with password: admin")
    except Exception as e:
        print(f"Error creating user: {e}")

if __name__ == "__main__":
    reset()
