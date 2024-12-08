from flask import Flask, jsonify, request
import mysql.connector
import os

app = Flask(__name__)

# Database connection parameters from environment variables
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_USER = os.getenv('DB_USER', 'admin')  # replace with your RDS username
DB_PASSWORD = os.getenv('DB_PASSWORD', 'yourpassword')  # replace with your RDS password
DB_NAME = os.getenv('DB_NAME', 'mydatabase')  # replace with your RDS database name

# Establish a database connection
def get_db_connection():
    print(DB_HOST)
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)  # Expose the API on port 80