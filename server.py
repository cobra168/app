from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore
from flask_cors import CORS
import os
import json

app = Flask(__name__)
CORS(app)  # Enable cross-origin requests

# Initialize Firebase Admin with your key
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

@app.route('/')
def home():
    return '✅ Backend Server is Running!'

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    user_data = data.get("userData", {})
    
    if not email or not password:
        return jsonify(error="Missing email or password"), 400
    
    try:
        # Create Firebase auth user
        user = auth.create_user(email=email, password=password)
        
        # Store additional user data in Firestore
        user_ref = db.collection("users").document(user.uid)
        user_ref.set({
            "email": email,
            **user_data,
            "createdAt": firestore.SERVER_TIMESTAMP
        })
        
        return jsonify({
            "uid": user.uid,
            "email": user.email,
            "userData": user_data
        }), 201
        
    except Exception as e:
        return jsonify(error=str(e)), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    
    if not email or not password:
        return jsonify(error="Missing email or password"), 400
    
    try:
        # This is just for demo - in production, use Firebase client SDK for login
        # Here we're just verifying the user exists and returning a mock token
        user = auth.get_user_by_email(email)
        
        # Get user data from Firestore
        user_doc = db.collection("users").document(user.uid).get()
        user_data = user_doc.to_dict() if user_doc.exists else {}
        
        # In a real app, you would generate a proper JWT token here
        mock_token = f"mock-token-{user.uid}"
        
        return jsonify({
            "token": mock_token,
            "user": {
                "uid": user.uid,
                "email": user.email,
                **user_data
            }
        }), 200
        
    except Exception as e:
        return jsonify(error=str(e)), 401

@app.route('/save_user_stats', methods=['POST'])
def save_user_stats():
    data = request.json
    uid = data.get("uid")
    stats = data.get("stats")
    
    if not uid or not stats:
        return jsonify(error="Missing uid or stats"), 400
    
    try:
        db.collection("user_stats").document(uid).set(stats, merge=True)
        return jsonify(success=True), 200
    except Exception as e:
        return jsonify(error=str(e)), 400

@app.route('/get_user_stats', methods=['GET'])
def get_user_stats():
    uid = request.args.get("uid")
    
    if not uid:
        return jsonify(error="Missing uid"), 400
    
    try:
        stats_doc = db.collection("user_stats").document(uid).get()
        if stats_doc.exists:
            return jsonify(stats=stats_doc.to_dict()), 200
        else:
            return jsonify(stats={}), 200
    except Exception as e:
        return jsonify(error=str(e)), 400

@app.route('/save_note', methods=['POST'])
def save_note():
    data = request.json
    uid = data.get("uid")
    note = data.get("note")
    if not uid or not note:
        return jsonify(error="Missing uid or note"), 400
    db.collection("notes").add({"uid": uid, "note": note})
    return jsonify(success=True), 200

@app.route('/notes', methods=['GET'])
def get_notes():
    uid = request.args.get("uid")
    if not uid:
        return jsonify(error="Missing uid"), 400
    notes_ref = db.collection("notes").where("uid", "==", uid)
    notes = [doc.to_dict() for doc in notes_ref.stream()]
    return jsonify(notes=notes), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
