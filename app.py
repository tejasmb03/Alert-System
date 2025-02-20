import cv2
import numpy as np
import matplotlib.pyplot as plt
import smtplib
from email.mime.text import MIMEText
import requests
import streamlit as st
from tensorflow.keras.applications import MobileNetV2

# Load pre-trained MobileNetV2 model for object detection
model = MobileNetV2(weights="imagenet")

def send_email_alert(change_percentage):
    sender_email = "your_email@gmail.com"
    receiver_email = "recipient_email@gmail.com"
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

def send_telegram_alert(change_percentage, alert_image_path):
    bot_token = "your_telegram_bot_token"
    chat_id = "your_chat_id"
    message = f"🚨 ALERT: Unauthorized construction detected! Change: {change_percentage:.2f}%"
    
    url_text = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params_text = {"chat_id": chat_id, "text": message}
    
    try:
        response = requests.get(url_text, params=params_text)
        response_data = response.json()
        
        if not response_data.get("ok"):
            st.error("Telegram message not sent. Check bot token and chat ID.")
            return
        
        url_photo = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        with open(alert_image_path, "rb") as photo:
            requests.post(url_photo, data={"chat_id": chat_id}, files={"photo": photo})
        st.success("Telegram alert sent successfully with image!")
    except Exception as e:
        st.error(f"Error sending Telegram alert: {e}")

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

def detect_changes(base_image_path, test_image_path, buffer_zone_mask_path, alert_image_path, change_threshold=5.0):
    base_image = cv2.imread(base_image_path)
    test_image = cv2.imread(test_image_path)
    buffer_zone_mask = cv2.imread(buffer_zone_mask_path, cv2.IMREAD_GRAYSCALE)
    
    if base_image is None:
        st.error("Error: Base image could not be loaded. Please check the file.")
        return
    if test_image is None:
        st.error("Error: Test image could not be loaded. Please check the file.")
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
        send_email_alert(change_percentage)
        send_telegram_alert(change_percentage, alert_image_path)
    else:
        st.success("No unauthorized construction detected.")
    
    st.image([base_image, test_image, overlap], caption=["Base Image", "Test Image", "Change Detection"], width=300)

st.title("Unauthorized Construction Detection System")
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
    
    detect_changes(base_path, test_path, mask_path, alert_path)
