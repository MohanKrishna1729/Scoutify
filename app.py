import streamlit as st
import hashlib
import json
import time
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from urllib.parse import quote
from pymongo import MongoClient
from datetime import datetime
import io

mongodb_uri = st.secrets["MONGODB"]["uri"]
scoutify_folder_id = st.secrets["GOOGLE_DRIVE"]["scoutify_folder_id"]
profile_pic_folder_id = st.secrets["GOOGLE_DRIVE"]["profile_pic_dir"]
service_account_info = st.secrets["SERVICE_ACCOUNT"]

# Initialize MongoDB client
client = MongoClient(mongodb_uri)
db = client['scoutify']
users_collection = db['users']
chats_collection = db['chats']

# Initialize session state if not already set
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ''
if 'profile' not in st.session_state:
    st.session_state['profile'] = {}
if 'choice' not in st.session_state:
    st.session_state['choice'] = 'Login'
if 'account_type' not in st.session_state:
    st.session_state['account_type'] = ''

def reload_uploaded_videos():
    global uploaded_videos
    user = users_collection.find_one({"username": st.session_state['username']})
    uploaded_videos = user.get('profile', {}).get('uploaded_videos', [])

# Authenticate and initialize Google Drive service globally
credentials = service_account.Credentials.from_service_account_info(service_account_info, scopes=['https://www.googleapis.com/auth/drive'])
drive_service = build('drive', 'v3', credentials=credentials)

# Add a background image and logo
st.markdown(
    """
    <style>
    .stApp {
        background: url('https://i.imgur.com/cBjQ0mv.png') no-repeat center center fixed;
        background-size: cover;
        height: 100vh;
        font-family: 'Arial', sans-serif;
        padding: 20px;
    }
    h1, h2, h3 {
        color: #ffffff;
        text-shadow: 2px 2px 4px #000000;
    }
    .stButton>button {
        background-color: #007bff;
        color: white;
        border-radius: 8px;
        padding: 10px 20px;
        border: none;
        font-size: 16px;
        margin: 10px 0;
    }
    .stButton>button:hover {
        background-color: #0056b3;
    }
    .profile-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
        margin: 20px 0;
    }
    @media (max-width: 600px) {
        .stButton>button {
            width: 100%;
            font-size: 14px;
        }
    }
    .logo {
        position: left;
        display: block;
        margin: 0 auto 20px auto;
        width: 100px;
    }
    /* Custom CSS for sidebar hover effect */
    .sidebar {
        position: fixed;
        left: -250px;
        top: 0;
        height: 100%;
        width: 250px;
        background-color: #111;
        transition: 0.3s;
        z-index: 1000;
    }
    .sidebar:hover {
        left: 0;
    }
    .sidebar-content {
        padding: 20px;
    }
    .main-content {
        margin-left: 0;
        transition: margin-left 0.3s;
    }
    .sidebar:hover + .main-content {
        margin-left: 250px;
    }
    </style>
    <img src="https://i.imgur.com/TlGCEkL.png" class="logo">
    """, unsafe_allow_html=True
)

# Sidebar menu with icons (conditionally include Login and Register)
if st.session_state['logged_in']:
    if st.session_state['account_type'] == "Trainer":
        menu = ["Home", "Profile", "Upload Video", "Chat", "Feed", "Logout"]
        icons = ["🏠", "👤", "📹", "💬", "📺", "🚪"]
    else:
        menu = ["Home", "Profile", "Upload Video", "Chat", "Logout"]
        icons = ["🏠", "👤", "📹", "💬", "🚪"]
else:
    menu = ["Login", "Register", "Home", "Profile", "Upload Video", "Chat", "Logout"]
    icons = ["🔑", "📝", "🏠", "👤", "📹", "💬", "🚪"]

# choice = st.sidebar.selectbox("Select a page", menu, format_func=lambda x: f"{icons[menu.index(x)]} {x}", index=menu.index(st.session_state['choice']))
st.markdown('<div class="sidebar"><div class="sidebar-content">', unsafe_allow_html=True)
choice = st.selectbox("Select a page", menu, format_func=lambda x: f"{icons[menu.index(x)]} {x}", index=menu.index(st.session_state['choice']))
st.markdown('</div></div>', unsafe_allow_html=True)


# Update session state with the current choice
st.session_state['choice'] = choice

# Function to programmatically change the sidebar selection
def change_choice(new_choice):
    st.session_state['choice'] = new_choice

# Handle logout
if choice == "Logout":
    if st.session_state['logged_in']:
        st.session_state['logged_in'] = False
        del st.session_state['username']
        st.success("You have logged out successfully.")
        change_choice('Login')
        time.sleep(1)  # Add a delay to show the success message before redirecting
        st.rerun()  # Trigger a page refresh
        
    else:
        st.warning("You are not logged in.")

# Home page
elif choice == "Home":
    if not st.session_state['logged_in']:
        st.warning("You must be logged in to view this page.")
    else:
        # st.title("Scoutify")
        st.subheader("**Welcome to Scoutify!**\n**This platform connects rural athletes in India with scouts, coaches, and academics.**")
        
        # Display uploaded videos for logged-in users
        reload_uploaded_videos()
        username = st.session_state['username']
        if uploaded_videos:
            st.write("**Your uploaded videos:**")
            for index, video in enumerate(uploaded_videos):
                st.write(f"**Video {index + 1}: {video['name']}**")
                st.video(video['link'])
                
                # Display a small "Delete" button for each video
                if st.button(f"Delete Video {index + 1}", key=video['id']):
                    # Remove the video link from the user's profile
                    users_collection.update_one(
                        {"username": username},
                        {"$pull": {"profile.uploaded_videos": {"id": video['id']}}}
                    )

                    # Delete the video from Google Drive
                    drive_service.files().delete(fileId=video['id']).execute()
                    st.success(f"Video {index + 1} deleted successfully!")
                    
                    # Trigger a page refresh to update the video list
                    st.session_state['refresh'] = True
                    st.rerun()
                    
        else:
            st.write("**You have not uploaded any videos yet.**")

# Profile page
elif choice == "Profile":
    if not st.session_state['logged_in']:
        st.warning("Login to view or update your profile.")
    else:
        st.header("Your Profile")
        username = st.session_state['username']

        # Load the profile from MongoDB
        user = users_collection.find_one({"username": username})
        profile = user.get('profile', {})
        st.session_state['profile'] = profile  # Sync session state with stored data

        # Display existing profile
        if profile:
            st.write(f"Name: {profile.get('name', '')}")
            st.write(f"Sport: {profile.get('sport', '')}")
            st.write(f"Age: {profile.get('age', '')}")
            st.write(f"Location: {profile.get('location', '')}")
            profile_pic_id = profile.get('profile_pic_id', '')
            profile_pic_name = profile.get('profile_pic_name', '')
            if profile_pic_id:
                profile_pic_url = f"https://scoutify.24h55a6214.workers.dev/1:/{profile_pic_name}"
                st.image(profile_pic_url, width=150)
                # Add delete button
                if st.button("Delete Profile Picture"):
                    drive_service.files().delete(fileId=profile_pic_id).execute()
                    users_collection.update_one(
                        {"username": username},
                        {"$unset": {"profile.profile_pic_id": ""}}
                    )
                    st.success("Profile picture deleted!")
            else:
                st.info("No profile picture uploaded.")

        # Update profile form
        with st.form("profile_form"):
            name = st.text_input("Name", st.session_state['profile'].get('name', ''))
            sport = st.text_input("Sport", st.session_state['profile'].get('sport', ''))
            age = st.number_input("Age", 5, 100, st.session_state['profile'].get('age', 18))
            location = st.text_input("Location", st.session_state['profile'].get('location', ''))
            profile_picture = st.file_uploader("Upload Profile Picture", type=["jpg", "jpeg", "png"])

            if st.form_submit_button("Update"):
                # Save updates to session state and MongoDB
                st.session_state['profile'] = {"name": name, "sport": sport, "age": age, "location": location}
                users_collection.update_one(
                    {"username": username},
                    {"$set": {"profile": st.session_state['profile']}}
                )

                if profile_picture:
                    # Upload the profile picture to Google Drive
                    file_metadata = {'name': profile_picture.name, 'parents': [profile_pic_folder_id]}
                    media = MediaIoBaseUpload(io.BytesIO(profile_picture.read()), mimetype=profile_picture.type)
                    file = drive_service.files().create(body=file_metadata, media_body=media, fields='id, name').execute()
                    profile_pic_id = file.get('id')
                    profile_pic_name = file.get('name')
                    users_collection.update_one(
                        {"username": username},
                        {"$set": {"profile.profile_pic_id": profile_pic_id, "profile.profile_pic_name": profile_pic_name}}
                    )
                st.success("Profile updated successfully!")
                st.rerun()  # Refresh the profile page to reflect the changes

# Register page
elif choice == "Register":
    if st.session_state['logged_in']:
        st.warning("You are already registered and logged in.")
    else:
        st.title("Register")
        with st.form("register_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            password_confirm = st.text_input("Confirm Password", type="password")
            account_type = st.selectbox("Account Type", ["User", "Trainer"])
            if st.form_submit_button("Register"):
                if users_collection.find_one({"username": username}):
                    st.warning("Username already exists!")
                elif password != password_confirm:
                    st.warning("Passwords do not match!")
                else:
                    hashed_password = hashlib.sha256(password.encode()).hexdigest()
                    users_collection.insert_one({'username': username, 'password': hashed_password, 'profile': {}, 'account_type': account_type})
                    st.success(f"Account created for {username}!")
                    change_choice('Login')  # Redirect to Login page after registration
                    st.rerun()  # Trigger a page refresh

# Login page
elif choice == "Login":
    if st.session_state['logged_in']:
        st.warning("You are already logged in.")
        st.write("Welcome, " + st.session_state['username'] + "!")
    else:
        st.title("Login")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                user = users_collection.find_one({"username": username})
                if not user:
                    st.warning("Username does not exist!")
                else:
                    hashed_password = hashlib.sha256(password.encode()).hexdigest()
                    if user['password'] == hashed_password:
                        st.success(f"Welcome back, {username}!")
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = username
                        st.session_state['account_type'] = user['account_type']
                        change_choice('Home')  # Redirect to Home page after login
                        st.rerun()  # Trigger a page refresh
                    else:
                        st.warning("Incorrect password!")

# Chat page
elif choice == "Chat":
    if not st.session_state['logged_in']:
        st.warning("You must be logged in to chat.")
    else:
        st.title("Chat")
        st.write("Chat with trainers or users!")

        # Select a user or trainer to chat with
        account_type = st.session_state['account_type']
        if account_type == "User":
            trainers = users_collection.find({"account_type": "Trainer"})
            chat_with = st.selectbox("Select a trainer to chat with", [trainer['username'] for trainer in trainers])
        else:
            users = users_collection.find({"account_type": "User"})
            chat_with = st.selectbox("Select a user to chat with", [user['username'] for user in users])

        # Display chat messages
        if chat_with:
            chat_messages = chats_collection.find({"$or": [
                {"sender": st.session_state['username'], "receiver": chat_with},
                {"sender": chat_with, "receiver": st.session_state['username']}
            ]}).sort("timestamp")

            for message in chat_messages:
                st.write(f"**{message['sender']}**: {message['message']}")

            # Send a new message
            new_message = st.text_input("Type your message", placeholder="Enter your message here. Markdown is enabled.")
            if st.button("Send"):
                chats_collection.insert_one({
                    "sender": st.session_state['username'],
                    "receiver": chat_with,
                    "message": new_message,
                    "timestamp": datetime.now()
                })
                st.success("Message sent!")
                st.rerun()  # Refresh the chat page to display the new message

# Upload Video page
elif choice == "Upload Video":
    if not st.session_state['logged_in']:
        st.warning("You must be logged in to upload videos.")
    else:
        st.title("Upload Video")
        st.write("Upload videos showcasing your sports talent!")
        video_files = st.file_uploader("Choose video files", type=["mp4", "avi", "mov"], accept_multiple_files=True)
        if video_files:
            progress_bar = st.progress(0)
            total_files = len(video_files)
            for i, video_file in enumerate(video_files):
                # Upload the file to Google Drive
                file_metadata = {'name': video_file.name, 'parents': [scoutify_folder_id]}
                media = MediaIoBaseUpload(io.BytesIO(video_file.read()), mimetype=video_file.type)
                file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()

                # Get the file ID and create a custom URL
                file_id = file.get('id')
                encoded_file_name = quote(video_file.name)
                custom_url = f"https://scoutify.24h55a6214.workers.dev/0:/{encoded_file_name}"

                # Update the user's profile with the video URL and file ID
                username = st.session_state['username']
                users_collection.update_one(
                    {"username": username},
                    {"$push": {"profile.uploaded_videos": {'id': file_id, 'link': custom_url, 'name': video_file.name}}}
                )

                # Update progress bar
                progress_bar.progress((i + 1) / total_files)

            st.success("Videos uploaded successfully!")

# Feed page (for trainers)
elif choice == "Feed":
    if not st.session_state['logged_in'] or st.session_state['account_type'] != "Trainer":
        st.warning("You must be logged in as a trainer to view this page.")
    else:
        st.title("Feed")
        st.write("All users' uploaded videos:")

        # Fetch all users' uploaded videos
        all_videos = users_collection.aggregate([
            {"$match": {"profile.uploaded_videos": {"$exists": True}}},
            {"$project": {"username": 1, "profile.uploaded_videos": 1}}
        ])

        for user in all_videos:
            username = user['username']
            uploaded_videos = user['profile']['uploaded_videos']
            if uploaded_videos:
                st.write(f"Videos uploaded by {username}:")
                for index, video in enumerate(uploaded_videos):
                    st.write(f"Video {index + 1}: {video['name']}")
                    st.video(video['link'])
