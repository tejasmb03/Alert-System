import os
import cv2
import numpy as np
import matplotlib.pyplot as plt
import smtplib
from email.mime.text import MIMEText
import requests
import streamlit as st

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
        print("Email alert sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

def send_telegram_alert(change_percentage, alert_image_path):
    bot_token = "your_telegram_bot_token"
    chat_id = "your_chat_id"
    message = f"\U0001F6A8 ALERT: Unauthorized construction detected! Change: {change_percentage:.2f}%"
    
    url_text = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    params_text = {"chat_id": chat_id, "text": message}
    
    try:
        response = requests.get(url_text, params=params_text)
        response_data = response.json()
        
        if not response_data.get("ok"):
            print("Telegram message not sent. Check bot token and chat ID.")
            return
        
        url_photo = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        with open(alert_image_path, "rb") as photo:
            requests.post(url_photo, data={"chat_id": chat_id}, files={"photo": photo})
        print("Telegram alert sent successfully with image!")
    except Exception as e:
        print(f"Error sending Telegram alert: {e}")

def generate_buffer_zone_mask(base_image_path, buffer_zone_mask_path, buffer_width=50):
    if not os.path.exists(base_image_path):
        print(f"Error: {base_image_path} not found.")
        return False
    
    base_image = cv2.imread(base_image_path)
    if base_image is None:
        print("Error: Base image could not be loaded. Check the file format.")
        return False
    
    gray_base = cv2.cvtColor(base_image, cv2.COLOR_BGR2GRAY)
    _, water_mask = cv2.threshold(gray_base, 100, 255, cv2.THRESH_BINARY_INV)
    
    kernel = np.ones((buffer_width, buffer_width), np.uint8)
    buffer_zone_mask = cv2.dilate(water_mask, kernel, iterations=1)
    
    cv2.imwrite(buffer_zone_mask_path, buffer_zone_mask)
    print("Buffer zone mask generated successfully!")
    return True

def detect_changes(base_image_path, test_image_path, buffer_zone_mask_path, alert_image_path, change_threshold=5.0, email=None):
    if not all(os.path.exists(p) for p in [base_image_path, test_image_path, buffer_zone_mask_path]):
        print("Error: One or more image files not found. Check the file paths.")
        return
    
    base_image = cv2.imread(base_image_path)
    test_image = cv2.imread(test_image_path)
    buffer_zone_mask = cv2.imread(buffer_zone_mask_path, cv2.IMREAD_GRAYSCALE)
    
    if base_image is None or test_image is None:
        print("Error: Unable to load one or more images. Check file formats.")
        return
    
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
        print(f"ALERT: Unauthorized construction detected in buffer zone! Change: {change_percentage:.2f}%")
        if email:
            send_email_alert(change_percentage, email)
        send_telegram_alert(change_percentage, alert_image_path)
    else:
        print("No unauthorized construction detected.")
    
    plt.figure(figsize=(12,6))
    plt.subplot(1,3,1)
    plt.title("Base Image")
    plt.imshow(cv2.cvtColor(base_image, cv2.COLOR_BGR2RGB))
    plt.axis("off")
    
    plt.subplot(1,3,2)
    plt.title("Test Image")
    plt.imshow(cv2.cvtColor(test_image, cv2.COLOR_BGR2RGB))
    plt.axis("off")
    
    plt.subplot(1,3,3)
    plt.title("Change Detection")
    plt.imshow(overlap, cmap='hot')
    plt.axis("off")
    
    plt.show()

# Example file paths
base_image_path = "base_image.jpg"
test_image_path = "test_image.jpg"
buffer_zone_mask_path = "buffer_zone_mask.jpg"
alert_image_path = "alert_image.jpg"

generate_buffer_zone_mask(base_image_path, buffer_zone_mask_path)
detect_changes(base_image_path, test_image_path, buffer_zone_mask_path, alert_image_path)
