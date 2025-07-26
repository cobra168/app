from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore
from flask_cors import CORS
import os
import datetime

app = Flask(__name__)
CORS(app)

# Initialize Firebase Admin
cred = credentials.Certificate("firebase-key.json")  # Replace with your Firebase key
firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route('/')
def home():
    return '✅ Backend Server is Running!'

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Create Firebase user
        user = auth.create_user(email=email, password=password)
        
        # Create user document in Firestore
        user_data = {
            'email': email,
            'created_at': datetime.datetime.now().isoformat(),
            'notes': []
        }
        db.collection('users').document(user.uid).set(user_data)
        
        return jsonify({
            'uid': user.uid,
            'email': user.email
        }), 201

    except auth.EmailAlreadyExistsError:
        return jsonify({'error': 'Email already exists'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/save_note', methods=['POST'])
def save_note():
    try:
        data = request.json
        uid = data.get('uid')
        note = data.get('note')
        
        if not uid or not note:
            return jsonify({'error': 'UID and note are required'}), 400

        # Add note to user's document
        user_ref = db.collection('users').document(uid)
        user_ref.update({
            'notes': firestore.ArrayUnion([{
                'text': note,
                'timestamp': datetime.datetime.now().isoformat()
            }])
        })
        
        return jsonify({'success': True}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/notes', methods=['GET'])
def get_notes():
    try:
        uid = request.args.get('uid')
        if not uid:
            return jsonify({'error': 'UID is required'}), 400

        # Get user's notes
        user_doc = db.collection('users').document(uid).get()
        if not user_doc.exists:
            return jsonify({'error': 'User not found'}), 404

        user_data = user_doc.to_dict()
        return jsonify({'notes': user_data.get('notes', [])}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
