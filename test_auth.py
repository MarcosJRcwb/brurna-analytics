import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
from src.auth.user_store import authenticate_user
from config import config

print("POSTGRES_CONN is:", config.POSTGRES_CONN)
print("Auth test for 'admin':", authenticate_user('admin', 'admin'))
