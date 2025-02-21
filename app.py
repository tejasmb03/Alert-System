import cv2
import numpy as np
import smtplib
import os
import requests
import streamlit as st
from skimage.metrics import structural_similarity as ssim
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

def send_email_alert(change_percentage, image_path, receiver_email):
    sender_email = "t1jit21cse2100029@jyothyit.ac.in"
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
        st.success("Email alert with message and image sent successfully!")
    except Exception as e:
        st.error(f"Error sending email: {e}")

def send_telegram_alert(change_percentage, image_path):
    bot_token = "8174600942:AAE-CSdjG1dwfHnRDX1ulw009_fybnAURIc"
    chat_id = "921645787"
    message = f"\U0001F6A8 ALERT: Unauthorized construction detected! Change: {change_percentage:.2f}%"
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

def detect_changes(base_image, test_image):
    base_gray = cv2.cvtColor(base_image, cv2.COLOR_BGR2GRAY)
    test_gray = cv2.cvtColor(test_image, cv2.COLOR_BGR2GRAY)
    
    (score, diff) = ssim(base_gray, test_gray, full=True)
    diff = (diff * 255).astype("uint8")
    
    thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY_INV)[1]
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if len(contours) == 0:
        return None, 0.0
    
    for c in contours:
        (x, y, w, h) = cv2.boundingRect(c)
        cv2.rectangle(base_image, (x, y), (x + w, y + h), (0, 0, 255), 2)
    
    change_percentage = (np.sum(thresh > 0) / thresh.size) * 100
    
    output_path = "detected_change.jpg"
    cv2.imwrite(output_path, base_image)
    return base_image, change_percentage, output_path

def reset_session():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

st.set_page_config(layout="wide")
st.title("Unauthorized Construction Detection")

col1, col2, col3 = st.columns(3)
with col1:
    base_image_file = st.file_uploader("Upload Base Image", type=["png", "jpg", "jpeg"], key="base")
with col2:
    test_image_file = st.file_uploader("Upload Test Image", type=["png", "jpg", "jpeg"], key="test")
with col3:
    receiver_email = st.text_input("Enter recipient email for alerts:", key="email")

st.markdown("<h6 style='font-size: 20px; font-weight: bold; background-color: white; padding: 10px;'>Select Alert Method:</h6>", unsafe_allow_html=True)

alert_method = st.radio("Select Alert Method:", ["None", "Email", "Telegram", "Both"], index=0, key="alert_method")

done_clicked = st.button("Done")

if done_clicked:
    if not base_image_file or not test_image_file:
        st.error("Please upload both images before proceeding.")
    elif not receiver_email:
        st.error("Please enter a recipient email address.")
    elif alert_method == "None":
        st.error("Please select an alert method.")
    else:
        base_file_bytes = base_image_file.read()
        test_file_bytes = test_image_file.read()
        base_image = cv2.imdecode(np.frombuffer(base_file_bytes, np.uint8), cv2.IMREAD_COLOR)
        test_image = cv2.imdecode(np.frombuffer(test_file_bytes, np.uint8), cv2.IMREAD_COLOR)
        
        result_image, change_percentage, output_path = detect_changes(base_image, test_image)
        
        if result_image is None:
            st.success("No unauthorized construction detected.")
        else:
            col1.image(base_image, caption="Base Image", use_column_width=True)
            col2.image(test_image, caption="Test Image", use_column_width=True)
            col3.image(result_image, caption=f"Detected Changes: {change_percentage:.2f}%", use_column_width=True)
            
            if alert_method == "Email":
                send_email_alert(change_percentage, output_path, receiver_email)
            elif alert_method == "Telegram":
                send_telegram_alert(change_percentage, output_path)
            elif alert_method == "Both":
                send_email_alert(change_percentage, output_path, receiver_email)
                send_telegram_alert(change_percentage, output_path)
    
if st.button("Clear and Restart", type="primary"):
    reset_session()
