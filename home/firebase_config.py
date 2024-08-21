import firebase_admin
from firebase_admin import credentials, storage

# Path to your Firebase Admin SDK JSON file
cred = credentials.Certificate('home/config/serviceAccountKey.json')  # Update this path

# Initialize Firebase app
firebase_admin.initialize_app(cred, {
    'storageBucket': 'social-app-50633.appspot.com'
})

# Get the Firebase Storage bucket
bucket = storage.bucket()
