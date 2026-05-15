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
    Sử dụng Google Search Grounding tách biệt thông qua model gemini-2.5-pro để lấy thông tin.
    """
    system_msg = "Bạn là trợ lý tìm kiếm thông tin Vĩ mô chuyên nghiệp."
    prompt = """HÃY SỬ DỤNG GOOGLE SEARCH ĐỂ TÌM KIẾM VÀ TÓM TẮT NGẮN GỌN CÁC THÔNG TIN SAU (CHỈ LẤY THÔNG TIN MỚI NHẤT):
1. Chỉ đạo tín dụng của Ngân hàng Nhà nước hoặc Thủ tướng mới nhất.
2. Tỷ lệ lạm phát US CPI YoY mới nhất.
3. Biên bản họp FOMC của Federal Reserve mới nhất.
Tuyệt đối không bịa đặt số liệu hoặc phát biểu nếu không tìm thấy."""
    return call_gemini(system_msg, prompt, model="gemini-2.5-pro", use_google_search=True, api_key_name="GEMINI_API_KEY_1")

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
    full_context = f"Đây là số liệu thô và thống kê mới nhất được lấy từ cơ sở dữ liệu:\n{data_context}\n\n--- KẾT QUẢ TÌM KIẾM INTERNET ---\n{search_context}\n\nHãy viết bản báo cáo vĩ mô đầy đủ theo đúng hướng dẫn."
    
    # Sử dụng bộ não siêu khủng Gemini 3.0 Flash cho việc làm Báo cáo Vĩ mô (Key 1)
    return call_gemini(system_msg, full_context, model="gemini-3.0-flash", api_key_name="GEMINI_API_KEY_1", use_google_search=False)

def get_crisis_search_context(chart_name, api_key_name):
    system_msg = "Bạn là trợ lý tìm kiếm dữ kiện lịch sử kinh tế."
    prompt = f"Hãy sử dụng Google Search để tìm và liệt kê nhanh các sự kiện khủng hoảng kinh tế toàn cầu và Việt Nam trong quá khứ có tác động mạnh đến {chart_name}. Chỉ nêu tên sự kiện, thời gian diễn ra và lý do ngắn gọn."
    return call_gemini(system_msg, prompt, model="gemini-2.5-pro", use_google_search=True, api_key_name=api_key_name)

def build_chart_prompt(chart_name, crisis_context):
    return f"""Bạn là Chuyên gia Kinh tế Vĩ mô cấp cao (Chief Economist) của VN McWatch.
Dưới đây là bộ dữ liệu lịch sử hoàn chỉnh của {chart_name}, xuất từ ngày xa nhất có thể.
NHIỆM VỤ CỦA BẠN:
1. So sánh đặc điểm, xu hướng, và mặt bằng số liệu của 2 thời kỳ: TRƯỚC năm 2025 và TỪ NĂM 2025 ĐẾN NAY.
2. NGHIÊN CỨU KHỦNG HOẢNG: Nhận diện các "đỉnh" (peaks) biến động mạnh nhất. Dựa vào Bối cảnh Khủng hoảng dưới đây để đối chiếu thời gian các đỉnh này với các sự kiện kinh tế:
--- BỐI CẢNH KHỦNG HOẢNG ---
{crisis_context}
---
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
    crisis_ctx = get_crisis_search_context("Thị trường Liên Ngân Hàng", "GEMINI_API_KEY_2")
    data_str = df_ib.to_csv(index=False)
    system_msg = build_chart_prompt("Thị trường Liên Ngân Hàng (Interbank) - Lãi suất & Khối lượng", crisis_ctx)
    res = call_gemini(system_msg, data_str, model="gemini-2.5-pro", use_google_search=False, api_key_name="GEMINI_API_KEY_2")
    return clean_html(res)

def analyze_chart_omo(df_omo):
    if df_omo.empty: return "<p>Không có dữ liệu OMO.</p>"
    crisis_ctx = get_crisis_search_context("Nghiệp vụ Thị trường mở (OMO)", "GEMINI_API_KEY_3")
    data_str = df_omo.to_csv(index=False)
    system_msg = build_chart_prompt("Nghiệp vụ Thị trường mở (OMO) - Bơm/Hút thanh khoản", crisis_ctx)
    res = call_gemini(system_msg, data_str, model="gemini-2.5-pro", use_google_search=False, api_key_name="GEMINI_API_KEY_3")
    return clean_html(res)

def analyze_chart_yield(df_us_yc, df_vn_yc):
    crisis_ctx = get_crisis_search_context("Đường cong Lợi suất (Yield Curve) Việt Nam và Mỹ", "GEMINI_API_KEY_4")
    s = "--- US YIELD CURVE ---\n" + (df_us_yc.to_csv(index=False) if not df_us_yc.empty else "No data")
    s += "\n--- VN YIELD CURVE ---\n" + (df_vn_yc.to_csv(index=False) if not df_vn_yc.empty else "No data")
    system_msg = build_chart_prompt("Đường cong Lợi suất (Yield Curve) Việt Nam và Mỹ", crisis_ctx)
    res = call_gemini(system_msg, s, model="gemini-2.5-pro", use_google_search=False, api_key_name="GEMINI_API_KEY_4")
    return clean_html(res)

def analyze_chart_fx(df_fx, df_us_fx):
    crisis_ctx = get_crisis_search_context("Tỷ giá Ngoại hối (Exchange Rates) và Chỉ số DXY", "GEMINI_API_KEY_5")
    s = "--- TỶ GIÁ VN (Central, VCB, Black Market) ---\n" + (df_fx.to_csv(index=False) if not df_fx.empty else "No data")
    s += "\n--- CHỈ SỐ DXY (Mỹ) ---\n" + (df_us_fx.to_csv(index=False) if not df_us_fx.empty else "No data")
    system_msg = build_chart_prompt("Tỷ giá Ngoại hối (Exchange Rates) và Chỉ số DXY", crisis_ctx)
    res = call_gemini(system_msg, s, model="gemini-2.5-pro", use_google_search=False, api_key_name="GEMINI_API_KEY_5")
    return clean_html(res)
