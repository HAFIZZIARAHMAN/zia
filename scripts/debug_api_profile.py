import sys, os, traceback
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import app

username = 'hiimzia'

with app.test_request_context(f'/api/profile/{username}'):
    try:
        rv = app.view_functions['api_profile'](username)
        print('Returned:', rv)
    except Exception:
        print('Exception during api_profile:')
        traceback.print_exc()
