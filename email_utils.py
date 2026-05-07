import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
import markdown

def send_daily_report(markdown_content: str):
    """
    Gửi báo cáo qua email bằng cấu hình SMTP của Gmail.
    """
    sender_email = os.environ.get("GMAIL_SENDER")
    sender_password = os.environ.get("GMAIL_APP_PASSWORD") # Mật khẩu ứng dụng (App Password)
    receiver_email = os.environ.get("GMAIL_RECEIVER") # Email nhận (có thể trùng email gửi)
    
    if not sender_email or not sender_password or not receiver_email:
        print("Cảnh báo: Chưa cấu hình thông tin Email (GMAIL_SENDER, GMAIL_APP_PASSWORD, GMAIL_RECEIVER). Bỏ qua gửi mail.")
        return False
        
    subject = "📊 Báo cáo Vĩ mô: Longitudinal Strategic Macro-Profiler"
    
    # Chuyển đổi Markdown thành HTML để hiển thị đẹp trong email
    html_content = markdown.markdown(markdown_content, extensions=['tables'])
    
    # Tạo HTML bao bọc có style cơ bản
    email_body = f"""
    <html>
      <head>
        <style>
          body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
          table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
          th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
          th {{ background-color: #f2f2f2; }}
          h1, h2, h3 {{ color: #2c3e50; }}
        </style>
      </head>
      <body>
        {html_content}
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email

    part1 = MIMEText(markdown_content, "plain")
    part2 = MIMEText(email_body, "html")

    msg.attach(part1)
    msg.attach(part2)

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print("✅ Đã gửi báo cáo qua email thành công!")
        return True
    except Exception as e:
        print(f"❌ Lỗi khi gửi email: {e}")
        return False
