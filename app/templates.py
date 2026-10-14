import os
from fastapi.templating import Jinja2Templates

# Calculate absolute path to app/templates directory
APP_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(APP_DIR, "templates")

# Shared Jinja2Templates instance with absolute directory path
templates = Jinja2Templates(directory=TEMPLATES_DIR)
