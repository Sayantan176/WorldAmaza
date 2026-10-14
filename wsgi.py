import sys
import os
from dotenv import load_dotenv

# Ensure project root is in sys.path
project_home = os.path.dirname(os.path.abspath(__file__))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Load environment variables from .env
load_dotenv(os.path.join(project_home, ".env"))

from a2wsgi import ASGIMiddleware
from app.database import init_db
from app.main import app

# Ensure database tables exist even in WSGI environments where lifespan events don't trigger
try:
    init_db()
except Exception as e:
    print(f"Notice during database initialization: {e}")

# Standard WSGI callable for PythonAnywhere / Gunicorn / uWSGI
application = ASGIMiddleware(app)
