from tinydb import TinyDB, Query
import hashlib

db = TinyDB('database.json')
users_table = db.table('users')
diaries_table = db.table('diaries')


def register_user(username, password):
    User = Query()
    if users_table.search(User.username == username):
        return False
    hashed = hash_password(password)
    users_table.insert({'username': username, 'password': hashed})
    return True


def check_login(username, password):
    User = Query()
    hashed = hash_password(password)
    return users_table.search((User.username == username) & (User.password == hashed))


def hash_password(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

