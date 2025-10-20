import requests

BASE = 'http://127.0.0.1:5000'

print('Testing /search_users?q=demo')
try:
    r = requests.get(BASE + '/search_users', params={'q':'demo'}, timeout=5)
    print(r.status_code, r.headers.get('content-type'))
    print(r.text[:1000])
    data = r.json()
    print('Returned items:', len(data))
    if data:
        first = data[0]
        username = first.get('username') or first.get('name')
        print('Testing /api/profile for', username)
        r2 = requests.get(BASE + '/api/profile/' + str(username))
        print(r2.status_code)
        print(r2.text)
except Exception as e:
    print('Error:', e)
