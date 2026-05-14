import os
from dotenv import load_dotenv

# Load env variables (for local testing)
load_dotenv()

def call_gemini(system_msg, content, model="gemini-3-flash-preview", use_google_search=False, api_key_name="GEMINI_API_KEY_1"):
    """
    Hàm gọi API Gemini (Google AI Studio) có hỗ trợ Google Search Grounding.
    """
    try:
        from google import genai
        from google.genai import types
        # Khởi tạo client, tự động lấy API KEY từ tên biến môi trường
        client = genai.Client(api_key=os.environ.get(api_key_name))
        
        # Gộp chung System Prompt và User Content
        full_prompt = f"--- LỆNH HỆ THỐNG ---\n{system_msg}\n\n--- DỮ LIỆU ĐẦU VÀO ---\n{content}"
        
        if use_google_search:
            config = types.GenerateContentConfig(
                tools=[{"google_search": {}}],
                temperature=0.4
            )
            response = client.models.generate_content(model=model, contents=full_prompt, config=config)

        else:
            response = client.models.generate_content(model=model, contents=full_prompt)
            
        return response.text
    except Exception as e:
        return f"Lỗi gọi Gemini API: {e}"


def get_search_context():
    """
    Dùng thư viện duckduckgo_search để lấy thông tin mới nhất từ internet.
    Hỗ trợ cho AI không có quyền truy cập internet (để không bịa data).
    """
    try:
        from duckduckgo_search import DDGS
        ddgs = DDGS()
        queries = [
            "Chỉ đạo tín dụng ngân hàng nhà nước thủ tướng mới nhất", 
            "US CPI YoY inflation rate latest", 
            "Federal Reserve FOMC minutes latest"
        ]
        search_text = "\n--- THÔNG TIN CẬP NHẬT TỪ INTERNET (DÙNG ĐỂ PHÂN TÍCH SOFT DATA) ---\n"
        search_text += "Lưu ý: TUYỆT ĐỐI dùng thông tin dưới đây để viết báo cáo. NẾU KHÔNG CÓ, HÃY GHI LÀ 'KHÔNG CÓ THÔNG TIN', CẤM BỊA ĐẶT PHÁT BIỂU CHÍNH TRỊ.\n\n"
        
        for q in queries:
            search_text += f"Kết quả tìm kiếm cho '{q}':\n"
            results = ddgs.text(q, max_results=2)
            for r in results:
                search_text += f"- {r.get('title', '')}: {r.get('body', '')}\n"
        return search_text
    except Exception as e:
        return f"\n--- THÔNG TIN INTERNET ---\nKhông thể truy cập internet. Tác vụ tính Real Rate hãy dùng CPI = 2.4%. Về chính trị: Xin ghi 'Không có dữ liệu mới cập nhật', tuyệt đối không tự bịa.\n"

def data_analyst_agent(chat_history_text):
    """
    Agent phân tích dữ liệu đa năng dựa trên kiến trúc ReAct (Reasoning and Acting).
    Nó sẽ đọc câu hỏi, tự sinh code Python lấy dữ liệu, chờ kết quả và phân tích.
    """
    system_msg = '''Bạn là Data Analyst Agent chuyên về Kinh tế Vĩ mô.
Quy tắc hoạt động (ReAct Loop):
1. Khi được hỏi một câu phức tạp cần số liệu, HÃY VIẾT CODE Python để tính toán. Đặt code vào block ```python ... ```.
2. LUÔN LUÔN dùng `print()` để in kết quả ra màn hình. Tôi sẽ lấy kết quả in ra đó mớm lại cho bạn ở bước tiếp theo dưới dạng "KẾT QUẢ CHẠY MÃ HỆ THỐNG".
3. Chỉ vẽ biểu đồ bằng `st.pyplot(fig)` nếu người dùng CÓ YÊU CẦU vẽ. Nếu không, chỉ cần in số liệu để phân tích chữ.
4. NẾU BẠN NHÌN THẤY "KẾT QUẢ CHẠY MÃ HỆ THỐNG" trong lịch sử chat, nghĩa là code của bạn vừa chạy xong. Dựa vào kết quả đó, hãy đưa ra NHẬN XÉT VÀ PHÂN TÍCH CUỐI CÙNG bằng lời văn. ĐỪNG sinh thêm code nữa trừ khi kết quả bị lỗi.

Cấu trúc biến `data_dict` (luôn có sẵn, không cần đọc từ file):
- 'SBV_Exchange_Rate': Date, USD_VND_Rate, Black_Market_rate, VCB_rate
- 'SBV_Interbank_Rate': Date, Term, Rate, Volume
- 'SBV_OMO': Ngày, Loại hình giao dịch, Kỳ hạn, Số TV tham gia, Số TV trúng thầu, Khối lượng mua trúng thầu, Lãi suất trúng thầu bên mua, Khối lượng mua đáo hạn, Khối lượng bán trúng thầu, Lãi suất trúng thầu bên bán, Khối lượng bán đáo hạn, Tổng bơm, Tổng hút, Giá trị bơm ròng
- 'SBV_Yield_Curve': Date, Term, Spot_Rate_Continuous_Pct, Par_Yield_Pct, Spot_Rate_Annual_Pct
- 'SBV_Policy_Rates': Loại lãi suất, Giá trị, Văn bản quyết định, Ngày có hiệu lực
- 'US_Exchange_Rate': Date, Broad Trade-Weighted Dollar Index
- 'US_Interbank_Rates': Date, EFFR, OBFR, SOFR
- 'US_OMO': Ngày, Loại hình giao dịch...
- 'US_Policy_Rates': Date, Fed Funds Rate, Bank Prime Loan
- 'US_Yield_Curve': Date, 1M, 3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y
- 'FedWatch_Probabilities': MEETING DATE, 275-300...

Các thư viện đã import: `pd` (pandas), `np` (numpy), `plt` (matplotlib.pyplot), `st` (streamlit).
Ví dụ truy cập: `df = data_dict['US_Policy_Rates']`
'''
    return call_gemini(system_msg, chat_history_text, model="gemini-3-flash-preview")

def generate_strategic_report(prompt_content, data_context):
    """
    Chức năng cố định: Dựa vào data và system prompt để viết Báo cáo.
    """
    system_msg = f"""Bạn là Chuyên gia Phân tích Chiến lược Vĩ mô.
Dưới đây là bộ chỉ dẫn (System Instructions) của bạn:
{prompt_content}

---
BÁO CÁO PHẢI TUÂN THỦ NGHIÊM NGẶT FORMAT VÀ NỘI DUNG ĐƯỢC YÊU CẦU TRONG CHỈ DẪN TRÊN.
Hãy sử dụng Markdown để trình bày báo cáo rõ ràng, dễ đọc. TUYỆT ĐỐI KHÔNG bịa đặt trích dẫn chính trị.
"""
    search_context = get_search_context()
    full_context = f"Đây là số liệu thô và thống kê mới nhất được lấy từ cơ sở dữ liệu:\n{data_context}\n{search_context}\n\nHãy viết bản báo cáo vĩ mô đầy đủ theo đúng hướng dẫn."
    
    # Sử dụng bộ não siêu khủng Gemini 3 Flash Preview cho việc làm Báo cáo Vĩ mô (Key 1)
    return call_gemini(system_msg, full_context, model="gemini-3-flash-preview", api_key_name="GEMINI_API_KEY_1")

def build_chart_prompt(chart_name):
    return f"""Bạn là Chuyên gia Kinh tế Vĩ mô cấp cao (Chief Economist) của VN McWatch.
Dưới đây là bộ dữ liệu lịch sử hoàn chỉnh của {chart_name}, xuất từ ngày xa nhất có thể.
NHIỆM VỤ CỦA BẠN:
1. So sánh đặc điểm, xu hướng, và mặt bằng số liệu của 2 thời kỳ: TRƯỚC năm 2025 và TỪ NĂM 2025 ĐẾN NAY.
2. NGHIÊN CỨU KHỦNG HOẢNG: Nhận diện các "đỉnh" (peaks) biến động mạnh nhất. BẮT BUỘC SỬ DỤNG TÌM KIẾM GOOGLE để đối chiếu thời gian các đỉnh này với các cuộc khủng hoảng/biến động kinh tế toàn cầu & Việt Nam (Ví dụ: Covid-19, Fed tăng lãi suất 2022...). Phân tích nguyên nhân đằng sau các đỉnh đó.
3. Trình bày trực tiếp bằng HTML tĩnh (chỉ dùng <p>, <ul>, <li>, <strong>, <em>, <h3>, <h4>). KHÔNG dùng markdown. KHÔNG có thẻ bọc ```html. Báo cáo cần mang giọng văn của các tổ chức tài chính Phố Wall.
"""

def clean_html(text):
    text = text.strip()
    if text.startswith("```html"): text = text[7:]
    if text.startswith("```"): text = text[3:]
    if text.endswith("```"): text = text[:-3]
    return text.strip()

def analyze_chart_interbank(df_ib):
    if df_ib.empty: return "<p>Không có dữ liệu Liên ngân hàng.</p>"
    data_str = df_ib.to_csv(index=False)
    system_msg = build_chart_prompt("Thị trường Liên Ngân Hàng (Interbank) - Lãi suất & Khối lượng")
    res = call_gemini(system_msg, data_str, model="gemini-3-flash-preview", use_google_search=True, api_key_name="GEMINI_API_KEY_2")
    return clean_html(res)

def analyze_chart_omo(df_omo):
    if df_omo.empty: return "<p>Không có dữ liệu OMO.</p>"
    data_str = df_omo.to_csv(index=False)
    system_msg = build_chart_prompt("Nghiệp vụ Thị trường mở (OMO) - Bơm/Hút thanh khoản")
    res = call_gemini(system_msg, data_str, model="gemini-3-flash-preview", use_google_search=True, api_key_name="GEMINI_API_KEY_3")
    return clean_html(res)

def analyze_chart_yield(df_us_yc, df_vn_yc):
    s = "--- US YIELD CURVE ---\n" + (df_us_yc.to_csv(index=False) if not df_us_yc.empty else "No data")
    s += "\n--- VN YIELD CURVE ---\n" + (df_vn_yc.to_csv(index=False) if not df_vn_yc.empty else "No data")
    system_msg = build_chart_prompt("Đường cong Lợi suất (Yield Curve) Việt Nam và Mỹ")
    res = call_gemini(system_msg, s, model="gemini-3-flash-preview", use_google_search=True, api_key_name="GEMINI_API_KEY_4")
    return clean_html(res)

def analyze_chart_fx(df_fx, df_us_fx):
    s = "--- TỶ GIÁ VN (Central, VCB, Black Market) ---\n" + (df_fx.to_csv(index=False) if not df_fx.empty else "No data")
    s += "\n--- CHỈ SỐ DXY (Mỹ) ---\n" + (df_us_fx.to_csv(index=False) if not df_us_fx.empty else "No data")
    system_msg = build_chart_prompt("Tỷ giá Ngoại hối (Exchange Rates) và Chỉ số DXY")
    res = call_gemini(system_msg, s, model="gemini-3-flash-preview", use_google_search=True, api_key_name="GEMINI_API_KEY_5")
    return clean_html(res)
