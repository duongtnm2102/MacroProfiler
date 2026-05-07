import os
import pandas as pd
import streamlit as st

@st.cache_data(ttl=3600) # Cache dữ liệu 1 giờ để tránh load đi load lại
def load_csv_from_url(url: str, filename_for_debug: str = "") -> pd.DataFrame:
    """
    Tải file CSV từ Google Drive hoặc Google Sheets URL.
    Bạn có thể thiết lập URL trong Streamlit Secrets.
    """
    try:
        if not url:
            return pd.DataFrame()
        # Đọc trực tiếp từ URL bằng Pandas
        df = pd.read_csv(url)
        return df
    except Exception as e:
        print(f"Lỗi khi tải file {filename_for_debug}: {e}")
        return pd.DataFrame()

def get_all_data():
    """
    Tải toàn bộ các file CSV cần thiết.
    Các đường link sẽ được định nghĩa trong file .env (chạy local) 
    hoặc Streamlit Secrets (chạy trên cloud).
    """
    data_dict = {}
    
    # Danh sách các biến môi trường chứa URL của file
    # Ví dụ: SBV_OMO_CSV_URL="https://docs.google.com/spreadsheets/d/xxx/export?format=csv"
    urls = {
        "SBV_OMO": os.environ.get("SBV_OMO_CSV_URL", ""),
        "SBV_Interbank_Rate": os.environ.get("SBV_INTERBANK_CSV_URL", ""),
        "SBV_Exchange_Rate": os.environ.get("SBV_EXCHANGE_CSV_URL", ""),
        "SBV_Policy_and_FedWatch": os.environ.get("SBV_FEDWATCH_CSV_URL", ""),
        "SBV_Yield_Curve": os.environ.get("SBV_YIELD_CSV_URL", ""),
        "US_Policy_Rates": os.environ.get("US_POLICY_CSV_URL", ""),
        "US_OMO": os.environ.get("US_OMO_CSV_URL", ""),
        "US_Yield_Curve": os.environ.get("US_YIELD_CSV_URL", "")
    }
    
    for name, url in urls.items():
        if url:
            data_dict[name] = load_csv_from_url(url, name)
            
    return data_dict
