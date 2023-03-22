from flask_login import UserMixin


class User(UserMixin):
    def __init__(self, id, username, password):
        self.id = id
        self.username = username
        self.password = password

    @staticmethod
    def get(user_id):
        # query the database for the user with the given id
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM users WHERE id = %s', (user_id,))
        user_data = cursor.fetchone()
        if user_data:
            # create a User object from the database data
            return User(user_data[0], user_data[1], user_data[2])
        else:
            return None

    @staticmethod
    def authenticate(username, password):
        # query the database for the user with the given username and password
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT * FROM users WHERE username = %s AND password = %s', (username, password))
        user_data = cursor.fetchone()
        if user_data:
            # create a User object from the database data
            return User(user_data[0], user_data[1], user_data[2])
        else:
            return None