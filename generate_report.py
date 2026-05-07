import os
from data_loader import get_all_data
from agents import economist_agent
from email_utils import send_daily_report

def main():
    print("Bắt đầu tiến trình tạo báo cáo Vĩ mô tự động...")
    
    # 1. Tải toàn bộ dữ liệu mới nhất
    print("Đang tải dữ liệu từ Google Sheets/Drive...")
    data_dict = get_all_data()
    data_context = "Dữ liệu mới nhất đã được tải. Các bảng dữ liệu hiện có: " + str(list(data_dict.keys()))
    
    # 2. Đọc file prompt
    prompt_path = "prompt.txt"
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            prompt_content = f.read()
    else:
        print("Lỗi: Không tìm thấy file prompt.txt")
        return
        
    # 3. Tạo báo cáo qua AI
    print("Đang chạy Economist AI để phân tích chiến lược...")
    report_md = economist_agent(prompt_content, data_context)
    
    # 4. Gửi email
    print("Đang định dạng HTML và gửi Email...")
    send_daily_report(report_md)
    print("Tiến trình hoàn thành!")

if __name__ == "__main__":
    main()
