from flask import Flask, render_template, Response, request, redirect, url_for, session
from facenet_pytorch import MTCNN
from deepface import DeepFace
import cv2
import time
import mysql.connector
import base64
from database import create_user, authenticate_user, get_user_age

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Set a secret key for session management

# MySQL connection configuration
mysql_connection = mysql.connector.connect(
    host="127.0.0.1",
    port="3307",
    user="root",
    password="",
    database="database"
)

# Define the timeout duration (15 minutes)
TIMEOUT_DURATION = 1 * 60

# Global variable to track whether the video feed has finished
video_feed_finished = False

def insert_result_into_database(username, result):
    cursor = mysql_connection.cursor()

    try:
        # Check if the username exists in the user table
        cursor.execute("SELECT username FROM user WHERE username = %s", (username,))
        user_row = cursor.fetchone()

        if user_row:
            # Define the MySQL query to insert the result
            insert_query = "INSERT INTO face_recognition_results (username, age, gender, emotion) VALUES (%s, %s, %s, %s)"

            # Check if result is a list
            if isinstance(result, list):
                for res in result:
                    age = res.get('age')
                    gender = res.get('dominant_gender')
                    dominant_emotion = res.get('dominant_emotion')

                    # Check if all values are present
                    if age is not None and gender is not None and dominant_emotion is not None:
                        # Convert age to int if applicable
                        try:
                            age = int(age)
                        except ValueError:
                            age = None

                        # Convert gender and dominant_emotion to strings
                        gender = str(gender)
                        dominant_emotion = str(dominant_emotion)

                        # Insert data into the database
                        if age is not None:
                            values = (username, age, gender, dominant_emotion)
                            cursor.execute(insert_query, values)
                            mysql_connection.commit()
                        else:
                            print("Invalid age value, skipping insertion")
                    else:
                        print("Missing required data in result, skipping insertion")
            else:
                # Handle the case when result is not a list (assume it's a single dictionary)
                age = result.get('age')
                gender = result.get('gender')
                dominant_emotion = result.get('dominant_emotion')

                # Check if all values are present
                if age is not None and gender is not None and dominant_emotion is not None:
                    # Convert age to int if applicable
                    try:
                        age = int(age)
                    except ValueError:
                        age = None

                    # Convert gender and dominant_emotion to strings
                    gender = str(gender)
                    dominant_emotion = str(dominant_emotion)

                    # Insert data into the database
                    if age is not None:
                        values = (username, age, gender, dominant_emotion)
                        cursor.execute(insert_query, values)
                        mysql_connection.commit()
                    else:
                        print("Invalid age value, skipping insertion")
                else:
                    print("Missing required data in result, skipping insertion")
        else:
            print("User not found, skipping insertion")
    except mysql.connector.Error as err:
        print(f"Error inserting result into database: {err}")
    finally:
        cursor.close()


def save_image_to_database(username, image_data):
    cursor = mysql_connection.cursor()

    try:
        # Define the MySQL query to insert the image data
        insert_query = "INSERT INTO captured_images (username, base64_data, jpeg_data) VALUES (%s, %s, %s)"

        # Encode the image data as base64
        image_data_base64 = base64.b64encode(image_data).decode('utf-8')

        # Insert the username, base64, and JPEG data into the database
        cursor.execute(insert_query, (username, image_data_base64, image_data))
        mysql_connection.commit()
        print("Image saved to database successfully!")
    except mysql.connector.Error as err:
        print(f"Error saving image to database: {err}")
    finally:
        cursor.close()


def save_base64_and_image_to_database(base64_data, jpeg_data):
    cursor = mysql_connection.cursor()

    try:
        # Define the MySQL query to insert both Base64 and JPEG data
        insert_query = "INSERT INTO images (base64_data, jpeg_data) VALUES (%s, %s)"

        # Insert data into the database
        cursor.execute(insert_query, (base64_data, jpeg_data))
        mysql_connection.commit()
        print("Data saved to database successfully!")
    except mysql.connector.Error as err:
        print(f"Error saving data to database: {err}")
    finally:
        cursor.close()

def save_base64_image_and_convert_to_jpeg(base64_data):
    # Decode Base64 data back to binary
    binary_data = base64.b64decode(base64_data)
    
    # Convert binary data to JPEG format
    jpeg_data = binary_data  # In this example, we're keeping the binary data as is
    
    # Save both Base64 and JPEG data to the database
    save_base64_and_image_to_database(base64_data, jpeg_data)

def calculate_age_difference(username):
    cursor = mysql_connection.cursor()

    try:
        # Check if the username exists in the user table
        cursor.execute("SELECT age_input FROM user WHERE username = %s", (username,))
        user_age_row = cursor.fetchone()

        if user_age_row:
            user_age = user_age_row[0]  # Extract the user's age from the result
        else:
            print("User age not found")
            return

        # Retrieve the detected ages from the face recognition result table
        cursor.execute("SELECT age FROM face_recognition_results WHERE username = %s ORDER BY username DESC LIMIT 1", (username,))


        detected_age_rows = cursor.fetchall()

        if detected_age_rows:
            for detected_age_row in detected_age_rows:
                detected_age = detected_age_row[0]  # Extract the detected age from the result

                # Calculate the age difference
                age_difference = user_age - detected_age

                # Insert the age difference into the 'age_test' table along with the username as foreign key
                insert_query = "INSERT INTO maetest (username, age_difference) VALUES (%s, %s)"
                cursor.execute(insert_query, (username, age_difference))
                mysql_connection.commit()

            print("Age differences calculated and saved to 'age_test' table successfully!")
        else:
            print("Detected ages not found for the user")

    except mysql.connector.Error as err:
        print(f"Error calculating age differences: {err}")
    finally:
        cursor.close()




# Define a global variable to track whether the video feed has finished
def detect_faces(username):
    global video_feed_finished

    video_capture = cv2.VideoCapture(2)  # Access the webcam (change to the appropriate device index if necessary)

    start_time = time.time()  # Record the start time
    while True:
        _, frame = video_capture.read()  # Read a frame from the webcam

        # Check if 5 seconds have elapsed
        if time.time() - start_time > 5:
            # Set the flag to indicate that the video feed is finished
            video_feed_finished = True
            # Stop processing frames after 5 seconds
            break

        # Perform face recognition using FaceNet model of DeepFace
        result = DeepFace.analyze(frame, detector_backend='mtcnn')

        # Insert the result into the MySQL database
        insert_result_into_database(username, result)

        calculate_age_difference(username)

        # Save the image to the database
        save_image_to_database(username, cv2.imencode('.jpg', frame)[1].tobytes())

        # Process the result as needed
        # For example, you can print the result to the console
        print(result)

        # Encode the analyzed frame as JPEG
        ret, jpeg = cv2.imencode('.jpg', frame)
        frame_bytes = jpeg.tobytes()

        # Yield the frame bytes as a response
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    video_capture.release()

# Route for video feed
@app.route('/video_feed')
def video_feed():
    global video_feed_finished

    # Check if the video feed is finished
    if video_feed_finished:
        # If finished, redirect to the login page
        return redirect(url_for('login'))

    # Start the face detection process
    return render_template('index.html')

@app.route('/video_feed2')
def video_feed2():
    global video_feed_finished

    # Reset the timer by updating the session variable with the current time
    session['main_page_access_time'] = time.time()

    # Check if the video feed is finished
    if video_feed_finished:
        # If finished, redirect to the main page
        return redirect(url_for('main'))

    # Start the face detection process
    return render_template('index2.html')

@app.route('/video_feed3')
def video_feed3():
    global video_feed_finished

    # Reset the timer by updating the session variable with the current time
    session['kids_page_access_time'] = time.time()

    # Check if the video feed is finished
    if video_feed_finished:
        # If finished, redirect to the login page
        return redirect(url_for('kids'))

    # Start the face detection process
    return render_template('index3.html')

@app.route('/video_feed_data', methods=['POST'])
def video_feed_data():
    if request.method == 'POST':
        username = request.form['username']
        return Response(detect_faces(username), mimetype='multipart/x-mixed-replace; boundary=frame')
    else:
        return "Method not allowed"

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    global video_feed_finished

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if authenticate_user(username, password):
            age_input = get_user_age(username)
            if age_input is None:
                return "User age not found"
            if age_input <= 12:
                session['kids_page_access_time'] = time.time()
                return redirect(url_for('kids'))
            else:
                session['main_page_access_time'] = time.time()
                return redirect(url_for('main'))
        else:
            return "Invalid username or password"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    global video_feed_finished

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        age_input = request.form['age_input']
        email = request.form['email']
        create_user(username, password, age_input, email)
        
        # Reset the video_feed_finished flag to False
        video_feed_finished = False
        
        return redirect(url_for('video_feed'))  # Redirect to the video feed page after successful registration
    
    return render_template('register.html')

# Function to reset the timer for the main page


@app.route('/main', methods=['GET', 'POST'])
def main():
    global video_feed_finished
    
    # Reset the flag indicating whether the video feed has finished
    video_feed_finished = False
        
    # Check if the timeout duration has been reached
    if 'main_page_access_time' in session and time.time() - session['main_page_access_time'] > TIMEOUT_DURATION:
        
        return redirect(url_for('video_feed2'))

    return render_template('main.html')

@app.route('/kids')
def kids():
    global video_feed_finished
    
    video_feed_finished = False
    
    # Check if the timeout duration has been reached
    if 'kids_page_access_time' in session and time.time() - session['kids_page_access_time'] > TIMEOUT_DURATION:
        
        return redirect(url_for('video_feed3'))

    return render_template('kids.html')

if __name__ == '__main__':
    app.run(debug=True)