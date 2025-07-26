from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore
from flask_cors import CORS
import os
import datetime
from functools import wraps

# Initialize Flask app
app = Flask(__name__)
CORS(app, supports_credentials=True)

# Initialize Firebase Admin
cred = credentials.Certificate("firebase-key.json")  # Make sure this file exists
firebase_admin.initialize_app(cred)
db = firestore.client()

# Helper function for authentication
def firebase_authenticated(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authorization header missing or invalid'}), 401
            
        token = auth_header.split('Bearer ')[1]
        try:
            decoded_token = auth.verify_id_token(token)
            request.uid = decoded_token['uid']
            return f(*args, **kwargs)
        except Exception as e:
            return jsonify({'error': str(e)}), 401
    return wrapper

@app.route('/')
def home():
    return jsonify({'status': 'running', 'service': 'NLH Music API'})

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        user_data = data.get('userData', {})
        
        # Validation
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400
        
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400

        # Create Firebase user
        user = auth.create_user(
            email=email,
            password=password,
            display_name=user_data.get('fullName', '')
        )

        # Prepare user document
        user_doc = {
            'uid': user.uid,
            'email': email,
            'createdAt': datetime.datetime.now().isoformat(),
            'lastLogin': datetime.datetime.now().isoformat(),
            **{k: v for k, v in user_data.items() if k not in ['password']}
        }

        # Save to Firestore
        db.collection('users').document(user.uid).set(user_doc)

        # Create custom token for immediate login
        custom_token = auth.create_custom_token(user.uid)
        
        return jsonify({
            'success': True,
            'token': custom_token.decode('utf-8'),
            'user': user_doc
        }), 201

    except auth.EmailAlreadyExistsError:
        return jsonify({'error': 'Email already in use'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Note: Actual authentication happens client-side with Firebase SDK
        # Here we just verify the user exists and return a custom token
        user = auth.get_user_by_email(email)
        
        # Get user data from Firestore
        user_doc = db.collection('users').document(user.uid).get()
        if not user_doc.exists:
            return jsonify({'error': 'User data not found'}), 404
            
        user_data = user_doc.to_dict()
        
        # Update last login
        db.collection('users').document(user.uid).update({
            'lastLogin': datetime.datetime.now().isoformat()
        })

        # Create custom token
        custom_token = auth.create_custom_token(user.uid)
        
        return jsonify({
            'success': True,
            'token': custom_token.decode('utf-8'),
            'user': user_data
        }), 200

    except auth.UserNotFoundError:
        return jsonify({'error': 'User not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/verify_token', methods=['POST'])
@firebase_authenticated
def verify_token():
    try:
        # Get user data
        user_doc = db.collection('users').document(request.uid).get()
        if not user_doc.exists:
            return jsonify({'error': 'User data not found'}), 404
            
        return jsonify({
            'success': True,
            'user': user_doc.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/user', methods=['GET'])
@firebase_authenticated
def get_user():
    try:
        user_doc = db.collection('users').document(request.uid).get()
        if not user_doc.exists:
            return jsonify({'error': 'User not found'}), 404
            
        return jsonify({
            'success': True,
            'user': user_doc.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/user/stats', methods=['GET', 'POST'])
@firebase_authenticated
def user_stats():
    try:
        if request.method == 'GET':
            # Get user stats
            stats_doc = db.collection('user_stats').document(request.uid).get()
            return jsonify({
                'success': True,
                'stats': stats_doc.to_dict() if stats_doc.exists else {}
            }), 200
            
        elif request.method == 'POST':
            # Update user stats
            stats = request.json.get('stats')
            if not stats:
                return jsonify({'error': 'Stats data required'}), 400
                
            db.collection('user_stats').document(request.uid).set(stats, merge=True)
            return jsonify({'success': True}), 200
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/user/activity', methods=['POST'])
@firebase_authenticated
def track_activity():
    try:
        activity_data = request.json
        if not activity_data:
            return jsonify({'error': 'Activity data required'}), 400
            
        # Update stats
        stats_ref = db.collection('user_stats').document(request.uid)
        
        # Increment songs played
        stats_ref.set({
            'songsPlayed': firestore.Increment(1),
            'lastActivity': datetime.datetime.now().isoformat()
        }, merge=True)
        
        # Add to recent activities
        activity = {
            **activity_data,
            'timestamp': datetime.datetime.now().isoformat()
        }
        
        stats_ref.update({
            'recentActivities': firestore.ArrayUnion([activity])
        })
        
        return jsonify({'success': True}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/user/profile', methods=['PUT'])
@firebase_authenticated
def update_profile():
    try:
        profile_data = request.json
        if not profile_data:
            return jsonify({'error': 'Profile data required'}), 400
            
        # Update profile in Firestore
        db.collection('users').document(request.uid).update(profile_data)
        
        # Get updated profile
        user_doc = db.collection('users').document(request.uid).get()
        
        return jsonify({
            'success': True,
            'user': user_doc.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True
