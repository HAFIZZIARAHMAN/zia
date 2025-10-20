import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from app import update_db_structure
print('Running update_db_structure()...')
try:
    update_db_structure()
    print('update_db_structure completed.')
except Exception as e:
    print('update_db_structure failed:', e)
