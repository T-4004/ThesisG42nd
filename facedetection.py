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
TIMEOUT_DURATION = 60 * 60

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
        cursor.execute("SELECT age FROM face_recognition_results WHERE username = %s ORDER BY insertion_timestamp DESC LIMIT 1", (username,))

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

            print("Age differences calculated and saved to 'maetest' table successfully!")
        else:
            print("Detected ages not found for the user")

    except mysql.connector.Error as err:
        print(f"Error calculating age differences: {err}")
    finally:
        cursor.close()

#asdgfjhsfjsvjjsdcsahd shfjsaj jshdfikas  sfsk sdvgksdv s,dvgksdgfsdkjgfk s,kdfgksadgfk gkgfksgfkabdvgwsgf sdfgsgfsjbdcshdg skdfg kdgsfg ksdgfksgdfkshgeugbasdgvgsdgfvksjf sdkjfskgfksgjdgcskdgfs skdfgjuksjdgfk sdfkjk sjkfsk skdjbfksjflkhajsbvhjbkusgkfg ksgfkgsdnbsdjhfgjks sdkjgfsbdhsbdjhgfsahb sdhfgsgfkbsKBD ksludgfksbdafsabdhsgdfkb jhksfgksjadgfksa nbsdfgskugfsbfsabdf ksgfksabfsabdkgfugwefh sdagjfksagrfusegargvhsbdgfwukegfsdba sudfgkwugefkbsndgbfsuadgfkash sadjgbfuwaegriu sajdgfuiysgf


# Define a global variable to track whether the video feed has finished
def detect_faces(username):
    global video_feed_finished

    video_capture = cv2.VideoCapture(0)  # Access the webcam (change to the appropriate device index if necessary)

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

#for the app.route video
def generate_frames(): 
    camera=cv2.VideoCapture(0) 
    while True:       
        
        ## read the camera frame
        success,frame=camera.read()
        if not success:
            break
        else:
            ret,buffer=cv2.imencode('.jpg',frame)
            frame=buffer.tobytes()

        yield(b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/video')
def video():
    return Response(generate_frames(),mimetype='multipart/x-mixed-replace; boundary=frame')



# Route for video feed here where it redirect to the index.html
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
    session['button1_access_time'] = time.time()
    session['button2_access_time'] = time.time()
    session['button3_access_time'] = time.time()

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

#video feed data and generate video feed are the one
@app.route('/video_feed_data', methods=['GET','POST'])
def video_feed_data():
    
    global video_feed_finished
    
    if video_feed_finished:
        # If finished, redirect to the login page
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        username = request.form['username']
        return generate_video_feed(username) 
    

@app.route('/generate_video_feed')
def generate_video_feed(username):
    

    # Assuming detect_faces returns a sequence of frame data
    for frame_data in detect_faces(username):
        # Build the frame with some HTML design or styling
        frame = b'<html><head><title>Registration Complete</title>'
        frame += b'<style>'
        frame += b'body { font-family: Arial, sans-serif; margin: 0; padding: 0; display: flex;'
        frame += b' flex-direction: column; align-items: center; height: 100vh; background:'
        frame += b' linear-gradient(135deg, skyblue, white); overflow: hidden; position: relative; }'
        frame += b'.art-container { position: absolute; top: 0; left: 0; width: 100%; height:'
        frame += b' 100%; pointer-events: none; z-index: -1; } .art-shape { position: absolute;'
        frame += b' border-radius: 50%; animation: move 15s linear infinite alternate; }'
        frame += b'@keyframes move { 0% { transform: translate(-50%, -50%) scale(1); }'
        frame += b'100% { transform: translate(-50%, -50%) scale(1.5); } } button { width:'
        frame += b' 100%; background-color: #007bff; color: #fff; border: none; padding: 12px;'
        frame += b' border-radius: 10px; cursor: pointer; transition: background-color 0.3s ease;'
        frame += b' font-size: 18px; margin-bottom: 10px; } button:hover { background-color:'
        frame += b' #0056b3; }'
        frame += b'</style>'
        frame += b'</head><body>'
        frame += b'<div class="art-container">'
        frame += b'<div class="art-shape"></div>'
        frame += b'</div>'
        frame += b'<h1>Registration Complete</h1>'
        frame += b'<form action="/login" method="get">'
        frame += b'<button type="submit">Go to Login</button>'
        frame += b'</form>'
        frame += b'</div></body></html>'

        # Yield the frame
        yield frame

    # Return the response after generating all frames
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

#video feed data and generate video feed are the one
@app.route('/video_feed_data2', methods=['GET','POST'])
def video_feed_data2():
    
    
    global video_feed_finished
    
    # Reset the timer by updating the session variable with the current time
    session['main_page_access_time'] = time.time()
    session['button1_access_time'] = time.time()
    session['button2_access_time'] = time.time()
    session['button3_access_time'] = time.time()
    
    if video_feed_finished:
        # If finished, redirect to the login page
        return redirect(url_for('main'))
    
    if request.method == 'POST':
        username = request.form['username']
        return generate_video_feed2(username) 
    

@app.route('/generate_video_feed2')
def generate_video_feed2(username):
    # Assuming detect_faces returns a sequence of frame data
    for frame_data in detect_faces(username):
        # Build the frame with some HTML design or styling
        frame = b'<html><head><title>Detection Complete</title>'
        frame += b'<style>'
        frame += b'body { font-family: Arial, sans-serif; margin: 0; padding: 0; display: flex;'
        frame += b' flex-direction: column; align-items: center; height: 100vh; background:'
        frame += b' linear-gradient(135deg, skyblue, white); overflow: hidden; position: relative; }'
        frame += b'.art-container { position: absolute; top: 0; left: 0; width: 100%; height:'
        frame += b' 100%; pointer-events: none; z-index: -1; } .art-shape { position: absolute;'
        frame += b' border-radius: 50%; animation: move 15s linear infinite alternate; }'
        frame += b'@keyframes move { 0% { transform: translate(-50%, -50%) scale(1); }'
        frame += b'100% { transform: translate(-50%, -50%) scale(1.5); } } button { width:'
        frame += b' 100%; background-color: #007bff; color: #fff; border: none; padding: 12px;'
        frame += b' border-radius: 10px; cursor: pointer; transition: background-color 0.3s ease;'
        frame += b' font-size: 18px; margin-bottom: 10px; } button:hover { background-color:'
        frame += b' #0056b3; }'
        frame += b'</style>'
        frame += b'</head><body>'
        frame += b'<div class="art-container">'
        frame += b'<div class="art-shape"></div>'
        frame += b'</div>'
        frame += b'<h1>Detection Complete</h1>'
        frame += b'<form action="/main" method="get">'
        frame += b'<button type="submit">Go Back to Main Page</button>'
        frame += b'</form>'
        frame += b'</div></body></html>'

        # Yield the frame
        yield frame

    # Return the response after generating all frames
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')




#the here will start
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
            if age_input <= -11:
                session['kids_page_access_time'] = time.time()
                return redirect(url_for('kids'))
            else:
                session['main_page_access_time'] = time.time()
                session['button1_access_time'] = time.time()
                session['button2_access_time'] = time.time()
                session['button3_access_time'] = time.time()
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
        
        # Check if username is already taken
        error_message = create_user(username, password, age_input, email)
        if error_message:
            return render_template('regidup.html', error=error_message)  # Render the register template with error message

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

@app.route('/kids', methods=['GET', 'POST'])
def kids():
    global video_feed_finished
    
    video_feed_finished = False
    
    # Check if the timeout duration has been reached
    if 'kids_page_access_time' in session and time.time() - session['kids_page_access_time'] > TIMEOUT_DURATION:
        
        return redirect(url_for('video_feed3'))

    return render_template('kids.html')


@app.route('/button1')
def button1():
    global video_feed_finished
    
    # Reset the flag indicating whether the video feed has finished
    video_feed_finished = False
        
    # Check if the timeout duration has been reached
    if 'button1_access_time' in session and time.time() - session['button1_access_time'] > TIMEOUT_DURATION:
        
        return redirect(url_for('video_feed2'))
    
    return render_template('G Page.html')

@app.route('/button2')
def button2():
    global video_feed_finished
    
    # Reset the flag indicating whether the video feed has finished
    video_feed_finished = False
        
    # Check if the timeout duration has been reached
    if 'button2_access_time' in session and time.time() - session['button2_access_time'] > TIMEOUT_DURATION:
        
        return redirect(url_for('video_feed2'))    
    
    return render_template('PG Page.html')

@app.route('/button3')
def button3():
    global video_feed_finished
    
    # Reset the flag indicating whether the video feed has finished
    video_feed_finished = False
        
    # Check if the timeout duration has been reached
    if 'button3_access_time' in session and time.time() - session['button3_access_time'] > TIMEOUT_DURATION:
        
        return redirect(url_for('video_feed2'))    
    
    return render_template('SPG Page.html')

@app.route('/TandC')
def TandC():
    return render_template('Terms.html')

@app.route('/TandCmain')
def TandCmain():
    return render_template('Terms1.html')


if __name__ == '__main__':
    app.run(debug=True)
    
      
