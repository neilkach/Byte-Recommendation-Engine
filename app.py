from flask import Flask, jsonify, request
import mysql.connector
import os
import openai
from dotenv import load_dotenv
import random
import requests
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": "*"}})

load_dotenv()

# Database connection parameters from environment variables defined in .env file
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')  
DB_PASSWORD = os.getenv('DB_PASSWORD')  
DB_NAME = os.getenv('DB_NAME')  
openai.api_key = os.getenv('OPENAI_API_KEY')
menu_api_key = os.getenv('MENU_API_KEY')
firebase_api_key = os.getenv('FIREBASE_API_KEY')

# Establish a database connection
def get_db_connection():
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    return conn

def get_firestore_connection():
    # Initialize Firestore connection with the Admin SDK
    try:
        # If you're using service account credentials
        cred = credentials.ApplicationDefault('cumulonimbus-439521-8a1a8993a810.json')
        firebase_admin.initialize_app(cred, {
            'projectId': project_id,
        })
        
        print("Connected to Firestore!")
        return firestore.client()
    except Exception as e:
        print(f"Failed to connect to Firestore: {e}")
        return None  

def get_menu(date=None,meal_time=None,line_type=None, dining_hall=None):
    url = 'https://menu-data-api2-656384740055.us-central1.run.app/api/objects'

    headers = {
        'X-API-Key':menu_api_key
    }

    params = {}
    if date:
        params['date'] = date
    if meal_time:
        params['meal_time'] = meal_time
    if line_type:
        params['line_type'] = line_type
    if dining_hall:
        params['dining_hall'] = dining_hall

    print(f"Making request with headers: {headers}")
    print(f"Parameters: {params}")

    response = requests.get(url, headers=headers, params=params)
    print(f"Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")

    if response.status_code == 200:
        return response.json()
    else:
        return None  

# Get recommendation from recommendation table
@app.route('/records/<int:id>', methods=['GET'])
def get_record(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM recommendations WHERE id = %s', (id,))
    record = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if record:
        return jsonify(record)
    else:
        return jsonify({'error': 'Record not found'}), 404

# Insert recommendation into RDS table
@app.route('/records', methods=['POST'])
def create_record():
    new_record = request.get_json()
    rec = new_record.get('recommendation')
    
    if not id or not name:
        return jsonify({'error': 'ID and Name are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO recommendations (recommendation) VALUES (%s)', (rece))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': 'Record created successfully'}), 201
    
# Fetch meals and get a recommendation from OpenAI model (actual recommendation feature)
@app.route('/recommend', methods=['GET'])
def recommend_meal():
    # user ID from request
    uid = request.args.get('uid')
    
    now = datetime.utcnow()
    # Format the date in the specified format
    formatted_date = now.strftime("%a, %d %b %Y 00:00:00 GMT")

    # same for user ratings
    user_reviews = fs_client.collection('userRatings').document(uid).get()
    user_reviews_dicts = [review.to_dict() for review in user_reviews]
    user_reviews_dicts.sort(key = lambda x: x['lastUpdated'])
    
    bfast_options = get_menu(date=formatted_date, meal_time='breakfast')
    lunch_options = get_menu(date=formatted_date, meal_time='lunch')
    dinner_options = get_menu(date=formatted_date, meal_time='dinner')
    
    for (b, l, d) in zip(bfast_options, lunch_options, dinner_options):
        relevant_global.append(global_reviews.document(b['dining_hall'] + '-' + b['food_item']).get())
        relevant_global.append(global_reviews.document(l['dining_hall'] + '-' + l['food_item']).get())
        relevant_global.append(global_reviews.document(d['dining_hall'] + '-' + d['food_item']).get())

    user_review_prompt = "Consider my past personal reviews: " + user_reviews_dicts.join(' ; ')
    global_review_prompt = "Consider my past global reviews: " + global_review_prompt.join(' ; ')
    meal_option_prompt = "Breakfast: " + bfast_options + '; Lunch: ' + lunch_options + '; Dinner: ' + dinner_options

    main_prompt = (
        "Based on the following meals available in the database, recommend a specific dining hall + line_type (and all its including foods) for each meal time:\n\n"
        f"{meal_option_prompt}\n\n"
        "Please provide meal recommendations in the same format as the options are given for Breakfast, Lunch, and Dinner."
    )

    # Query OpenAI for a recommendation
    try:
        client = OpenAI()
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful meal recommendation assistant."},
                 {"role": "system", "content": global_review_prompt},
                 {"role": "system", "content": user_review_prompt}
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        recommendation = completion.choices[0].message
        lunch_rec_index = recommendation.find('Lunch recommendation: ')
        dinner_rec_index = recommendation.find('Dinner recommendation: ')
        
        breakfast = recommendation[:lunch_rec_index]
        lunch = recommendation[lunch_rec_index:dinner_rec_index]
        dinner = recommendation[dinner_rec_index:]
        
        #insert into past recs table
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO recommendations (recommendation) VALUES (%s)', (breakfast))
        cursor.execute('INSERT INTO recommendations (recommendation) VALUES (%s)', (lunch))
        cursor.execute('INSERT INTO recommendations (recommendation) VALUES (%s)', (dinner))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        return jsonify({'error': 'Error interacting with OpenAI', 'details': str(e)}), 500

    return jsonify({'Breakfast recommendation': breakfast, 'Lunch recommendation': lunch,
                    'Dinner recommendation': dinner})
    
# Fetch a hardcoded meal recommendation just for UI testing purposes (since OpenAPI calls cost money)
@app.route('/recommend_special', methods=['GET'])
def hardcode():
    now = datetime.utcnow()
    # Format the date in the specified format
    formatted_date = now.strftime("%a, %d %b %Y 00:00:00 GMT")

    breakfast = get_menu(date = formatted_date, meal_time = 'breakfast', line_type = 'Main Line', dining_hall = 'Ferris')
    lunch = get_menu(date = formatted_date, meal_time = 'lunch', line_type = 'Flame', dining_hall = 'Hewitt')
    dinner = get_menu(date = formatted_date, meal_time = 'dinner', line_type = 'Main Line', dining_hall = 'John Jay')
    
    #post recommendation to databse
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO recommendations (recommendation) VALUES (%s)', (breakfast))
    cursor.execute('INSERT INTO recommendations (recommendation) VALUES (%s)', (lunch))
    cursor.execute('INSERT INTO recommendations (recommendation) VALUES (%s)', (dinner))
    conn.commit()
    cursor.close()
    conn.close()


    return jsonify({'Breakfast recommendation': breakfast, 'Lunch recommendation': lunch,
                    'Dinner recommendation': dinner})

if __name__ == '__main__':
    fs_client = get_firestore_connection()
    #get global Ratings from firestore backend once
    global_reviews = fs_client.collection('globalRatings')
    app.run(host='0.0.0.0', port=3000)  # Expose the API on port 80