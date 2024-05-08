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