from flask import Flask, request, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app)  # Enable cross-origin requests

# Home route to verify server is running
@app.route('/')
def home():
    return "✅ Server is running!"

# Initialize Firebase Admin SDK
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)
db = firestore.client()

# Register a new user
@app.route('/register', methods=['POST'])
def register():
    data = request.json
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify(error="Missing email or password"), 400
    try:
        user = auth.create_user(email=email, password=password)
        return jsonify(uid=user.uid, email=user.email), 201
    except Exception as e:
        return jsonify(error=str(e)), 400

# Login endpoint (not implemented server-side)
@app.route('/login', methods=['POST'])
def login():
    return jsonify(error="Use client-side Firebase SDK for login"), 501

# Save a note for the user
@app.route('/save_note', methods=['POST'])
def save_note():
    data = request.json
    uid = data.get("uid")
    note = data.get("note")
    if not uid or not note:
        return jsonify(error="Missing uid or note"), 400
    db.collection("notes").add({"uid": uid, "note": note})
    return jsonify(success=True), 200

# Get all notes for a user
@app.route('/notes', methods=['GET'])
def get_notes():
    uid = request.args.get("uid")
    if not uid:
        return jsonify(error="Missing uid"), 400
    notes_ref = db.collection("notes").where("uid", "==", uid)
    notes = [doc.to_dict() for doc in notes_ref.stream()]
    return jsonify(notes=notes), 200

# Run server on Render
if __name__ == '__main__':
    app.run(port=10000, host="0.0.0.0")
