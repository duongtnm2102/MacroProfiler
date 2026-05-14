import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
import os
import markdown

def send_daily_report(markdown_content: str, pdf_path: str = None):
    """
    Gửi báo cáo qua email bằng cấu hình SMTP của Gmail, đính kèm file PDF nếu có.
    """
    sender_email = os.environ.get("GMAIL_SENDER")
    sender_password = os.environ.get("GMAIL_APP_PASSWORD")
    receiver_email = os.environ.get("GMAIL_RECEIVER")
    
    if not sender_email or not sender_password or not receiver_email:
        print("Cảnh báo: Chưa cấu hình thông tin Email. Bỏ qua gửi mail.")
        return False
        
    subject = "📊 Báo cáo Vĩ mô: VN McWatch Institutional Report"
    
    html_content = markdown.markdown(markdown_content, extensions=['tables'])
    
    email_body = f"""
    <html>
      <head>
        <style>
          body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
          h3 {{ color: #2c3e50; }}
        </style>
      </head>
      <body>
        <h3>Kính gửi Quý Khách hàng / Ban Lãnh đạo,</h3>
        <p>Hệ thống AI VN McWatch đã hoàn tất phân tích thị trường ngày hôm nay.</p>
        <p>Vui lòng xem <b>file PDF đính kèm</b> để đọc bản báo cáo chuyên sâu đầy đủ nhất bao gồm phân tích biểu đồ.</p>
        <hr>
        <h4>Tóm tắt nhanh (Executive Summary):</h4>
        {html_content}
      </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email

    part1 = MIMEText("Vui lòng xem file PDF đính kèm.", "plain")
    part2 = MIMEText(email_body, "html")

    msg.attach(part1)
    msg.attach(part2)

    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
            pdf_attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
            msg.attach(pdf_attachment)

    try:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        server.quit()
        print("✅ Đã gửi báo cáo (kèm PDF) qua email thành công!")
        return True
    except Exception as e:
        print(f"❌ Lỗi khi gửi email: {e}")
        return False

