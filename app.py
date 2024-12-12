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

app = Flask(__name__)

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

# Get a record by ID
@app.route('/records/<int:id>', methods=['GET'])
def get_record(id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT * FROM test_table WHERE id = %s', (id,))
    record = cursor.fetchone()
    cursor.close()
    conn.close()
    
    if record:
        return jsonify(record)
    else:
        return jsonify({'error': 'Record not found'}), 404

# Insert a new record
@app.route('/records', methods=['POST'])
def create_record():
    new_record = request.get_json()
    id = new_record.get('id')
    name = new_record.get('name')
    
    if not id or not name:
        return jsonify({'error': 'ID and Name are required'}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO test_table (id, name) VALUES (%s, %s)', (id, name))
    conn.commit()
    cursor.close()
    conn.close()

    return jsonify({'message': 'Record created successfully'}), 201

def get_menu(date=None):
    url = 'https://menu-data-api2-656384740055.us-central1.run.app/api/objects'

    headers = {
        'X-API-Key':menu_api_key
    }

    params = {}
    if date:
        params['date'] = date

    print(f"Making request with headers: {headers}")
    print(f"Parameters: {params}")

    response = requests.get(url, headers=headers, params=params)
    print(f"Status Code: {response.status_code}")
    print(f"Response Text: {response.text}")

    if response.status_code == 200:
        return response.json()
    else:
        return None
    
# Fetch a random meal recommendation
@app.route('/recommend_special', methods=['GET'])
def hardcode():
    now = datetime.utcnow()
    # Format the date in the specified format
    formatted_date = now.strftime("%a, %d %b %Y 00:00:00 GMT")
    
    # options = get_menu(formatted_date)
    # meal_times = ['breakfast', 'lunch', 'dinner']
    # breakfast, lunch, dinner = [], [], []
    # for time in meal_time:
    #     breakfast.append(get_menu(date=formatted_date, meal_time=time))
    #     lunch.append(option)
    #     dinner.append(option)
    # r = min(len(breakfast), len(lunch), len(dinner))
    # random_meal = random.randint(0,r)
    
    breakfast = get_menu(date = formatted_date, meal_time = 'breakfast', line_type = 'Main line')
    lunch = get_menu(date = formatted_date, meal_time = 'lunch', line_type = 'Flame')
    dinner = get_menu(date = formatted_date, meal_time = 'dinner', line_type = 'Main line')
    print(breakfast, lunch, dinner)
    return jsonify({'Breakfast recommendation': breakfast, 'Lunch recommendation': lunch,
                    'Dinner recommendation': dinner})

# Fetch meals and get a recommendation
@app.route('/recommend', methods=['GET'])
def recommend_meal():
    uid = request.args.get('uid')
    # fs_client = get_firestore_connection()

    # same for user ratings
    user_reviews = fs_client.collection('userRatings').document(uid).get()
    print(user_reviews)
    user_reviews_dicts = [review.to_dict() for review in user_reviews]
    print(user_reviews_dicts)
    user_reviews_dicts.sort(key = lambda x: x['lastUpdated'])

    # if not meals:
    #     return jsonify({'error': 'No meals found for the given criteria.'}), 404

    # # Prepare a prompt for OpenAI
    # meal_descriptions = "\n".join(
    #     f"{meal['date']} - {meal['main_dish']}: {meal['side']})"
    #     for meal in meals
    # )
    prompt = (
        "Based on the following meals available in the database, recommend a meal for today:\n\n"
        f"{meal_descriptions}\n\n"
        "Please provide a single meal recommendation and explain why it might be a good choice."
    )

    # Query OpenAI for a recommendation
    try:
        client = OpenAI()
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful meal recommendation assistant."},
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        recommendation = completion.choices[0].message
    except Exception as e:
        return jsonify({'error': 'Error interacting with OpenAI', 'details': str(e)}), 500

    return jsonify({'Breakfast recommendation': breakfast[random_meal], 'Lunch recommendation': lunch[random_meal],
                    'Dinner recommendation': dinner[random_meal]})

if __name__ == '__main__':
    fs_client = get_firestore_connection()
    #get global Ratings from firestore backend once
    global_reviews = fs_client.collection('globalRatings')
    app.run(host='0.0.0.0', port=3000)  # Expose the API on port 80