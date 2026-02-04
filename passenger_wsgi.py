"""
Passenger WSGI file for PASCI API
This file is used by Plesk's Passenger to run the FastAPI application
"""
import sys
import os
from pathlib import Path

# Get the application directory
INTERP = os.path.join(os.environ['HOME'], 'pasci-api', 'venv', 'bin', 'python3')
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)

# Add the application directory to the Python path
cwd = os.getcwd()
sys.path.insert(0, cwd)

# Set the application root directory
application_path = Path(__file__).parent.absolute()
sys.path.insert(0, str(application_path))

# Load environment variables from .env file
from dotenv import load_dotenv
env_path = application_path / '.env'
load_dotenv(dotenv_path=env_path)

# Import the FastAPI application
from app.main import app as application

# If you need ASGI to WSGI conversion, uncomment below:
# from asgiref.wsgi import WsgiToAsgi
# application = WsgiToAsgi(application)
