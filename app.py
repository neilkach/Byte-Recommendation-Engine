from flask import Flask, jsonify, request
import mysql.connector
import os
import openai
from dotenv import load_dotenv
import random
import requests

app = Flask(__name__)

load_dotenv()

# Database connection parameters from environment variables defined in .env file
DB_HOST = os.getenv('DB_HOST')
DB_USER = os.getenv('DB_USER')  
DB_PASSWORD = os.getenv('DB_PASSWORD')  
DB_NAME = os.getenv('DB_NAME')  
openai.api_key = os.getenv('OPENAI_API_KEY')
menu_api_key = os.getenv('MENU_API_KEY')

# Establish a database connection
def get_db_connection():
    conn = mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )
    return conn

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

# Fetch meals and get a recommendation
@app.route('/recommend', methods=['GET'])
def recommend_meal():
    return get_menu()
    # Optional query parameters for filtering (e.g., category or calorie range)
    # category = request.args.get('category')  # e.g., "Vegetarian"
    # max_calories = request.args.get('max_calories')  # e.g., "500"

    # Query meals from the database
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    id = random.randint(1,2)
    
    query = f"SELECT * FROM meals where id = {id}"
    filters = []
    params = []

    # if category:
    #     filters.append("category = %s")
    #     params.append(category)
    # if max_calories:
    #     filters.append("calories <= %s")
    #     params.append(max_calories)

    # if filters:
    #     query += " WHERE " + " AND ".join(filters)
    
    cursor.execute(query, params)
    meals = cursor.fetchall()
    cursor.close()
    connection.close()
    
    return jsonify(meals)

    if not meals:
        return jsonify({'error': 'No meals found for the given criteria.'}), 404

    # Prepare a prompt for OpenAI
    meal_descriptions = "\n".join(
        f"{meal['date']} - {meal['main_dish']}: {meal['side']})"
        for meal in meals
    )
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

    # Return the recommendation
    return jsonify({'recommendation': recommendation})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)  # Expose the API on port 80