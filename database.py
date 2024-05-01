import mysql.connector

# Establish a connection to your MySQL database
conn = mysql.connector.connect(
    host="127.0.0.1",
    port="3307",
    user="root",
    password="",
    database="database"
)

# Create a cursor object to execute SQL queries
cursor = conn.cursor()

def create_user(username, password, age_input, email):
    # Insert a new user into the 'users' table
    query = "INSERT INTO user (username, user_password, age_input, email) VALUES (%s, %s, %s, %s)"
    cursor.execute(query, (username, password, age_input, email))
    conn.commit()

def authenticate_user(username, password):
    # Check if the provided username and password match a record in the 'users' table
    query = "SELECT * FROM user WHERE username = %s AND user_password = %s"
    cursor.execute(query, (username, password))
    return cursor.fetchone() is not None

def get_user_age(username):
    # Retrieve the age of the user from the 'user' table
    query = "SELECT age_input FROM user WHERE username = %s"
    cursor.execute(query, (username,))
    result = cursor.fetchone()
    return result[0] if result else None