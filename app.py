import cv2
import numpy as np
import matplotlib.pyplot as plt
import smtplib
import os
import requests
import streamlit as st
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

def send_email_alert(change_percentage, image_path):
    sender_email = "t1jit21cse2100029@jyothyit.ac.in"
    receiver_email = "tejasmbharadwajvishnu@gmail.com"
    app_password = "lzqg kouy jtfw mgnc"

    subject = "Alert: Unauthorized Construction Detected!"
    body = f"Unauthorized construction detected in the buffer zone! Change detected: {change_percentage:.2f}%"

    msg = MIMEMultipart()
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = receiver_email
    msg.attach(MIMEText(body, "plain"))

    with open(image_path, "rb") as attachment:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f"attachment; filename={os.path.basename(image_path)}")
        msg.attach(part)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, app_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        st.success("Email alert with image sent successfully!")
    except Exception as e:
        st.error(f"Error sending email: {e}")

def send_telegram_alert(change_percentage, image_path):
    bot_token = "8174600942:AAE-CSdjG1dwfHnRDX1ulw009_fybnAURIc"
    chat_id = "921645787"
    message = f"🚨 ALERT: Unauthorized construction detected! Change: {change_percentage:.2f}%"

    url_text = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    url_photo = f"https://api.telegram.org/bot{bot_token}/sendPhoto"

    try:
        requests.post(url_text, data={"chat_id": chat_id, "text": message})
    except Exception as e:
        st.error(f"Error sending Telegram message: {e}")

    try:
        with open(image_path, "rb") as image_file:
            requests.post(url_photo, data={"chat_id": chat_id}, files={"photo": image_file})
        st.success("Telegram alert with image sent successfully!")
    except Exception as e:
        st.error(f"Error sending Telegram image: {e}")

def generate_buffer_zone_mask(base_image, buffer_width=50):
    gray_base = cv2.cvtColor(base_image, cv2.COLOR_BGR2GRAY)
    _, water_mask = cv2.threshold(gray_base, 100, 255, cv2.THRESH_BINARY_INV)
    kernel = np.ones((buffer_width, buffer_width), np.uint8)
    buffer_zone_mask = cv2.dilate(water_mask, kernel, iterations=1)
    return buffer_zone_mask

def detect_changes(base_image, test_image, buffer_zone_mask, change_threshold=5.0):
    target_size = (min(base_image.shape[1], test_image.shape[1]), min(base_image.shape[0], test_image.shape[0]))
    base_image = cv2.resize(base_image, target_size)
    test_image = cv2.resize(test_image, target_size)
    buffer_zone_mask = cv2.resize(buffer_zone_mask, target_size)
    
    if len(buffer_zone_mask.shape) == 3:
        buffer_zone_mask = cv2.cvtColor(buffer_zone_mask, cv2.COLOR_BGR2GRAY)
    
    diff = cv2.absdiff(base_image, test_image)
    _, diff_thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
    overlap = cv2.bitwise_and(diff_thresh, buffer_zone_mask)
    change_percentage = (np.sum(overlap > 0) / np.sum(buffer_zone_mask > 0)) * 100
    return overlap, change_percentage

st.title("Unauthorized Construction Detection")
base_image_file = st.file_uploader("Upload Base Image", type=["png", "jpg", "jpeg"])
test_image_file = st.file_uploader("Upload Test Image", type=["png", "jpg", "jpeg"])

if base_image_file and test_image_file:
    base_file_bytes = base_image_file.read()
    test_file_bytes = test_image_file.read()

    base_image = cv2.imdecode(np.frombuffer(base_file_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
    test_image = cv2.imdecode(np.frombuffer(test_file_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)

    if base_image is None or test_image is None:
        st.error("Error: Could not decode one or both uploaded images. Please upload valid image files.")
    else:
        color_base_image = cv2.imdecode(np.frombuffer(base_file_bytes, np.uint8), cv2.IMREAD_COLOR)
        buffer_zone_mask = generate_buffer_zone_mask(color_base_image)
        overlap, change_percentage = detect_changes(base_image, test_image, buffer_zone_mask)

        st.image([base_image, test_image, overlap], caption=["Base Image", "Test Image", "Change Detection"], use_column_width=True, channels="GRAY")
        st.write(f"Change Detected: {change_percentage:.2f}%")

        if change_percentage > 5.0:
            change_image_path = "detected_change.jpg"
            cv2.imwrite(change_image_path, overlap)
            send_email_alert(change_percentage, change_image_path)
            send_telegram_alert(change_percentage, change_image_path)
