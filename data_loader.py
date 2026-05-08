import os
import pandas as pd
import streamlit as st
import requests
import io

@st.cache_data(ttl=3600)
def load_csv_from_url(url: str, filename_for_debug: str = "") -> pd.DataFrame:
    try:
        if not url: return pd.DataFrame()
        # Tự động convert link Google Drive sang dạng download trực tiếp
        if "drive.google.com/file/d/" in url:
            file_id = url.split("/file/d/")[1].split("/")[0]
            url = f"https://drive.google.com/uc?id={file_id}&export=download"
        return pd.read_csv(url)
    except Exception as e:
        print(f"Lỗi khi tải file {filename_for_debug}: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_combined_csv(url: str):
    """
    Hàm xử lý tách riêng file gộp SBV Policy và FedWatch
    """
    try:
        if not url: return pd.DataFrame(), pd.DataFrame()
        
        # Tự động convert link Google Drive sang dạng download trực tiếp
        if "drive.google.com/file/d/" in url:
            file_id = url.split("/file/d/")[1].split("/")[0]
            url = f"https://drive.google.com/uc?id={file_id}&export=download"
            
        response = requests.get(url)
        response.raise_for_status()
        lines = response.text.splitlines()
        
        split_idx = -1
        for i, line in enumerate(lines):
            if "FEDWATCH" in line.upper():
                split_idx = i
                break
                
        if split_idx == -1:
            return pd.read_csv(io.StringIO(response.text), on_bad_lines='skip'), pd.DataFrame()
            
        # Lấy phần SBV Policy (trước split_idx)
        sbv_lines = [line for line in lines[:split_idx] if line.strip() and not line.startswith("--- SHEET:")]
        
        # Tìm dòng có chữ MEETING DATE làm header cho FedWatch
        fedwatch_start = split_idx
        for i in range(split_idx, len(lines)):
            if "MEETING DATE" in lines[i].upper():
                fedwatch_start = i
                break
                
        fedwatch_lines = [line for line in lines[fedwatch_start:] if line.strip()]
        
        df_sbv = pd.read_csv(io.StringIO("\n".join(sbv_lines)), on_bad_lines='skip')
        df_fed = pd.read_csv(io.StringIO("\n".join(fedwatch_lines)), on_bad_lines='skip')
        
        # Lọc bỏ các cột trống (Unnamed) do dư dấu phẩy
        df_sbv = df_sbv.loc[:, ~df_sbv.columns.str.contains('^Unnamed')]
        df_fed = df_fed.loc[:, ~df_fed.columns.str.contains('^Unnamed')]
        
        return df_sbv, df_fed
    except Exception as e:
        print(f"Lỗi khi xử lý file gộp: {e}")
        return pd.DataFrame(), pd.DataFrame()

def get_all_data():
    """
    Tải toàn bộ file CSV
    """
    data_dict = {}
    
    # 1. Các file thông thường
    urls = {
        "SBV_OMO": os.environ.get("SBV_OMO_CSV_URL", ""),
        "SBV_Interbank_Rate": os.environ.get("SBV_INTERBANK_CSV_URL", ""),
        "SBV_Exchange_Rate": os.environ.get("SBV_EXCHANGE_CSV_URL", ""),
        "SBV_Yield_Curve": os.environ.get("SBV_YIELD_CSV_URL", ""),
        "US_Policy_Rates": os.environ.get("US_POLICY_CSV_URL", ""),
        "US_OMO": os.environ.get("US_OMO_CSV_URL", ""),
        "US_Yield_Curve": os.environ.get("US_YIELD_CSV_URL", ""),
        "US_Exchange_Rate": os.environ.get("US_EXCHANGE_CSV_URL", ""),
        "US_Interbank_Rates": os.environ.get("US_INTERBANK_CSV_URL", "")
    }
    
    for name, url in urls.items():
        if url:
            data_dict[name] = load_csv_from_url(url, name)
            
    # 2. Xử lý riêng file gộp
    combined_url = os.environ.get("SBV_FEDWATCH_CSV_URL", "")
    if combined_url:
        df_sbv, df_fed = load_combined_csv(combined_url)
        data_dict["SBV_Policy_Rates"] = df_sbv
        data_dict["FedWatch_Probabilities"] = df_fed
        
    return data_dict
