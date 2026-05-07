# Longitudinal Strategic Macro-Profiler (Replica)

Hệ thống phân tích vĩ mô tự động 100% Online, Miễn phí, sử dụng AI (Groq API) với kiến trúc Multi-Agent và giao diện Chat tương tác (Streamlit).

## 🚀 Hướng dẫn Triển khai (Deployment)

### BƯỚC 1: Đẩy mã nguồn lên GitHub
1. Đăng nhập [GitHub](https://github.com/) và tạo một Repository mới (ví dụ: `MacroProfiler`).
2. Upload toàn bộ các file trong thư mục này lên Repository vừa tạo.

### BƯỚC 2: Thiết lập Tự động gửi Email lúc 8:00 AM (GitHub Actions)
Hệ thống sử dụng GitHub Actions để tự động thức dậy lúc 8h sáng, gọi AI phân tích và gửi báo cáo qua Email cho bạn. Để bảo mật thông tin, bạn cần lưu cấu hình vào Secrets.
1. Tại giao diện Repository của bạn trên GitHub, vào mục **Settings** -> **Secrets and variables** -> **Actions**.
2. Nhấn **New repository secret** và thêm lần lượt các biến sau:
   - `GROQ_API_KEY`: API Key của Groq (Tạo miễn phí tại console.groq.com)
   - `GMAIL_SENDER`: Email dùng để gửi (VD: email_cua_ban@gmail.com)
   - `GMAIL_APP_PASSWORD`: Mật khẩu ứng dụng 16 ký tự của Gmail (Lấy ở mục Bảo mật 2 lớp tài khoản Google)
   - `GMAIL_RECEIVER`: Email nhận báo cáo (có thể giống email gửi)
   - `SBV_OMO_CSV_URL`: Link tải trực tiếp file CSV từ Google Drive/Sheets.
   - `SBV_INTERBANK_CSV_URL`: (Tương tự)
   - `SBV_EXCHANGE_CSV_URL`: (Tương tự)
   - `SBV_FEDWATCH_CSV_URL`: (Tương tự)
   - `SBV_YIELD_CSV_URL`: (Tương tự)
   - `US_POLICY_CSV_URL`: (Tương tự)
   - `US_OMO_CSV_URL`: (Tương tự)
   - `US_YIELD_CSV_URL`: (Tương tự)

### BƯỚC 3: Triển khai Giao diện Web (Streamlit Cloud)
Giao diện này cho phép bạn truy cập ứng dụng trên Điện thoại để nhắn tin với AI, vẽ biểu đồ mà không cần mở laptop.
1. Truy cập [Streamlit Community Cloud](https://share.streamlit.io/).
2. Đăng nhập bằng tài khoản GitHub của bạn.
3. Nhấn **New app**, chọn Repository `MacroProfiler` vừa tạo, mục Main file path điền `app.py`.
4. Trước khi nhấn Deploy, nhấn vào **Advanced settings** và dán toàn bộ các cấu hình ở Bước 2 vào khung **Secrets** theo format:
```toml
GROQ_API_KEY = "your_groq_api_key"
GMAIL_SENDER = "your_email"
GMAIL_APP_PASSWORD = "your_password"
# (Và các link CSV tương tự)
```
5. Nhấn **Deploy!** 

Bây giờ hệ thống của bạn đã hoạt động trực tuyến 24/7!
