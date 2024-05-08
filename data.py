import mysql.connector

# Establishing the connection
connection = mysql.connector.connect(
    host="your_host",
    user="your_username",
    password="your_password",
    database="your_database"
)

# Checking if the connection is successful
if connection.is_connected():
    print("Connected to MySQL database")

# Perform database operations here

# Closing the connection
connection.close()
