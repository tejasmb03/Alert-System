import cv2
import numpy as np
import matplotlib.pyplot as plt
import smtplib
from email.mime.text import MIMEText
import requests
import streamlit as st
from tensorflow.keras.applications import MobileNetV2
import bcrypt
import json

# Load pre-trained MobileNetV2 model for object detection
model = MobileNetV2(weights="imagenet")

# User authentication system
def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed.encode())

def load_users():
    try:
        with open("users.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open("users.json", "w") as f:
        json.dump(users, f)

users = load_users()

st.title("Unauthorized Construction Detection System")
menu = st.sidebar.selectbox("Menu", ["Login", "Register", "Detection"])

def send_email_alert(change_percentage, receiver_email):
    sender_email = "your_email@gmail.com"
    app_password = "your_app_password"
    
    subject = "Alert: Unauthorized Construction Detected!"
    body = f"Unauthorized construction detected in the buffer zone! Change detected: {change_percentage:.2f}%"
    
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        st.success("Email alert sent successfully!")
    except Exception as e:
        st.error(f"Error sending email: {e}")

def generate_buffer_zone_mask(base_image_path, buffer_zone_mask_path, buffer_width=50):
    base_image = cv2.imread(base_image_path)
    if base_image is None:
        st.error("Error: Base image could not be loaded. Check the file path.")
        return False
    
    gray_base = cv2.cvtColor(base_image, cv2.COLOR_BGR2GRAY)
    _, water_mask = cv2.threshold(gray_base, 100, 255, cv2.THRESH_BINARY_INV)
    
    kernel = np.ones((buffer_width, buffer_width), np.uint8)
    buffer_zone_mask = cv2.dilate(water_mask, kernel, iterations=1)
    
    cv2.imwrite(buffer_zone_mask_path, buffer_zone_mask)
    st.success("Buffer zone mask generated successfully!")
    return True

def detect_changes(base_image_path, test_image_path, buffer_zone_mask_path, alert_image_path, change_threshold=5.0, email=None):
    base_image = cv2.imread(base_image_path)
    test_image = cv2.imread(test_image_path)
    buffer_zone_mask = cv2.imread(buffer_zone_mask_path, cv2.IMREAD_GRAYSCALE)
    
    if base_image is None or test_image is None:
        st.error("Error: One or more images could not be loaded. Please check the files.")
        return
    if buffer_zone_mask is None:
        st.warning("Buffer zone mask is missing. Generating now...")
        if not generate_buffer_zone_mask(base_image_path, buffer_zone_mask_path):
            return
        buffer_zone_mask = cv2.imread(buffer_zone_mask_path, cv2.IMREAD_GRAYSCALE)
    
    target_size = (min(base_image.shape[1], test_image.shape[1]), min(base_image.shape[0], test_image.shape[0]))
    base_image = cv2.resize(base_image, target_size)
    test_image = cv2.resize(test_image, target_size)
    buffer_zone_mask = cv2.resize(buffer_zone_mask, target_size)
    
    base_gray = cv2.cvtColor(base_image, cv2.COLOR_BGR2GRAY)
    test_gray = cv2.cvtColor(test_image, cv2.COLOR_BGR2GRAY)
    
    diff = cv2.absdiff(base_gray, test_gray)
    _, diff_thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
    
    overlap = cv2.bitwise_and(diff_thresh, buffer_zone_mask)
    change_percentage = (np.sum(overlap > 0) / np.sum(buffer_zone_mask > 0)) * 100
    
    cv2.imwrite(alert_image_path, overlap)
    
    if change_percentage > change_threshold:
        st.error(f"ALERT: Unauthorized construction detected in buffer zone! Change: {change_percentage:.2f}%")
        if email:
            send_email_alert(change_percentage, email)
    else:
        st.success("No unauthorized construction detected.")
    
    st.image([base_image, test_image, overlap], caption=["Base Image", "Test Image", "Change Detection"], width=300)

if menu == "Register":
    new_user = st.text_input("Enter new username")
    new_password = st.text_input("Enter password", type="password")
    email = st.text_input("Enter email for alerts")
    if st.button("Register"):
        if new_user in users:
            st.warning("Username already exists.")
        else:
            users[new_user] = {"password": hash_password(new_password), "email": email}
            save_users(users)
            st.success("User registered successfully!")

elif menu == "Login":
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        if username in users and check_password(password, users[username]["password"]):
            st.success("Login successful!")
            st.session_state["logged_in"] = True
            st.session_state["username"] = username
        else:
            st.error("Invalid username or password.")

elif menu == "Detection":
    if "logged_in" in st.session_state and st.session_state["logged_in"]:
        base_image = st.file_uploader("Upload Base Image", type=["jpg", "png", "jpeg"])
        test_image = st.file_uploader("Upload Test Image", type=["jpg", "png", "jpeg"])
        if base_image and test_image:
            base_path = "base_image.jpg"
            test_path = "test_image.jpg"
            mask_path = "buffer_zone_mask.jpg"
            alert_path = "alert_image.jpg"
            with open(base_path, "wb") as f:
                f.write(base_image.getbuffer())
            with open(test_path, "wb") as f:
                f.write(test_image.getbuffer())
            detect_changes(base_path, test_path, mask_path, alert_path, email=users[st.session_state["username"]]["email"])
    else:
        st.warning("Please log in first.")
