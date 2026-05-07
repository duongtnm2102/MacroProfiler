import pandas as pd
import numpy as np
from datetime import timedelta

def get_closest_val(df, date_col, val_col, target_date):
    temp = df[df[date_col] <= target_date]
    if len(temp) == 0: return np.nan
    return temp.sort_values(date_col).iloc[-1][val_col]

def get_range_7d(df, date_col, val_col, target_date):
    temp = df[(df[date_col] > target_date - timedelta(days=7)) & (df[date_col] <= target_date)]
    if len(temp) == 0: return np.nan, np.nan, np.nan
    return temp.sort_values(date_col).iloc[-1][val_col], temp[val_col].min(), temp[val_col].max()

def process_macro_data(data_dict):
    """
    Xử lý 10 DataFrames gốc thành một chuỗi thống kê (Dashboard Stats) dùng cho báo cáo ngày.
    """
    try:
        df_sbv_omo = data_dict.get('SBV_OMO')
        df_sbv_policy = data_dict.get('SBV_Policy_Rates')
        df_us_policy = data_dict.get('US_Policy_Rates')
        df_fx = data_dict.get('SBV_Exchange_Rate')
        df_us_yield = data_dict.get('US_Yield_Curve')
        df_vn_yield = data_dict.get('SBV_Yield_Curve')
        df_sbv_ib = data_dict.get('SBV_Interbank_Rate')
        df_us_omo = data_dict.get('US_OMO')
        df_fedwatch = data_dict.get('FedWatch_Probabilities')
        
        if df_sbv_omo is None or df_sbv_omo.empty:
            return "Thiếu dữ liệu SBV_OMO để xác định mốc thời gian."
            
        # Format Date columns
        df_sbv_omo['Ngày'] = pd.to_datetime(df_sbv_omo['Ngày'], format="%d/%m/%Y", errors='coerce')
        T_date = df_sbv_omo['Ngày'].max()
        T = T_date
        T_1W = T - timedelta(days=7)
        T_1M = T - timedelta(days=30)
        T_1Y = T - timedelta(days=365)
        
        results = {}
        
        # 1. SBV Refinancing Rate
        if df_sbv_policy is not None and not df_sbv_policy.empty:
            df_sbv_policy = df_sbv_policy[df_sbv_policy['Loại lãi suất'].astype(str).str.contains('Lãi suất tái cấp vốn')].copy()
            df_sbv_policy['Ngày có hiệu lực'] = pd.to_datetime(df_sbv_policy['Ngày có hiệu lực'], format="%d/%m/%Y", errors='coerce')
            df_sbv_policy = df_sbv_policy.dropna(subset=['Ngày có hiệu lực']).sort_values('Ngày có hiệu lực')
            df_sbv_policy['Giá trị'] = pd.to_numeric(df_sbv_policy['Giá trị'], errors='coerce')
            df_sbv_policy['Giá trị'] = df_sbv_policy['Giá trị'].apply(lambda x: x*100 if x < 1 else x)
            df_sbv_policy.set_index('Ngày có hiệu lực', inplace=True)
            idx = pd.date_range(start=df_sbv_policy.index.min(), end=T_date)
            df_sbv_policy = df_sbv_policy.reindex(idx, method='ffill').reset_index()
            
            t_refin = get_closest_val(df_sbv_policy, 'index', 'Giá trị', T)
            _, min_refin, max_refin = get_range_7d(df_sbv_policy, 'index', 'Giá trị', T)
            results['SBV_Refinancing_Rate_T'] = f"{t_refin}% (L: {min_refin}% - H: {max_refin}%)"
            results['SBV_Refinancing_Rate_1W'] = get_closest_val(df_sbv_policy, 'index', 'Giá trị', T_1W)
            results['SBV_Refinancing_Rate_1M'] = get_closest_val(df_sbv_policy, 'index', 'Giá trị', T_1M)
            results['SBV_Refinancing_Rate_1Y'] = get_closest_val(df_sbv_policy, 'index', 'Giá trị', T_1Y)

        # 2. US Fed Funds Rate
        if df_us_policy is not None and not df_us_policy.empty:
            df_us_policy['Date'] = pd.to_datetime(df_us_policy['Date'], format="%d/%m/%Y", errors='coerce')
            t_ffr, min_ffr, max_ffr = get_range_7d(df_us_policy, 'Date', 'Fed Funds Rate', T)
            results['US_FFR_T'] = f"{t_ffr}% (L: {min_ffr}% - H: {max_ffr}%)"
            results['US_FFR_1W'] = get_closest_val(df_us_policy, 'Date', 'Fed Funds Rate', T_1W)
            results['US_FFR_1M'] = get_closest_val(df_us_policy, 'Date', 'Fed Funds Rate', T_1M)
            results['US_FFR_1Y'] = get_closest_val(df_us_policy, 'Date', 'Fed Funds Rate', T_1Y)

        # 3. FX Gap
        if df_fx is not None and not df_fx.empty:
            df_fx['Date'] = pd.to_datetime(df_fx['Date'], format="%d/%m/%Y", errors='coerce')
            df_fx['Black_Market_rate'] = pd.to_numeric(df_fx['Black_Market_rate'], errors='coerce')
            df_fx['VCB_rate'] = pd.to_numeric(df_fx['VCB_rate'], errors='coerce')
            df_fx['FX_Gap'] = df_fx['Black_Market_rate'] - df_fx['VCB_rate']
            df_fx = df_fx.dropna(subset=['FX_Gap']).sort_values('Date')
            t_fx, min_fx, max_fx = get_range_7d(df_fx, 'Date', 'FX_Gap', T)
            results['FX_Gap_T'] = f"{t_fx:.0f} (L: {min_fx:.0f} - H: {max_fx:.0f})" if not pd.isna(t_fx) else "N/A"
            results['FX_Gap_1W'] = get_closest_val(df_fx, 'Date', 'FX_Gap', T_1W)
            results['FX_Gap_1M'] = get_closest_val(df_fx, 'Date', 'FX_Gap', T_1M)
            results['FX_Gap_1Y'] = get_closest_val(df_fx, 'Date', 'FX_Gap', T_1Y)

        # 4. US Yield Spread (10Y-2Y)
        if df_us_yield is not None and not df_us_yield.empty:
            df_us_yield['Date'] = pd.to_datetime(df_us_yield['Date'], format="%d/%m/%Y", errors='coerce')
            df_us_yield['Spread'] = pd.to_numeric(df_us_yield['10Y'], errors='coerce') - pd.to_numeric(df_us_yield['2Y'], errors='coerce')
            df_us_yield = df_us_yield.dropna(subset=['Spread']).sort_values('Date')
            t_usy, min_usy, max_usy = get_range_7d(df_us_yield, 'Date', 'Spread', T)
            results['US_Yield_Spread_T'] = f"{t_usy:.2f}% (L: {min_usy:.2f}% - H: {max_usy:.2f}%)" if not pd.isna(t_usy) else "N/A"
            results['US_Yield_Spread_1W'] = get_closest_val(df_us_yield, 'Date', 'Spread', T_1W)
            results['US_Yield_Spread_1M'] = get_closest_val(df_us_yield, 'Date', 'Spread', T_1M)
            results['US_Yield_Spread_1Y'] = get_closest_val(df_us_yield, 'Date', 'Spread', T_1Y)

        # 5. VN Yield Spread (10Y-3M)
        if df_vn_yield is not None and not df_vn_yield.empty:
            df_vn_yield['Date'] = pd.to_datetime(df_vn_yield['Date'], format="%d/%m/%Y", errors='coerce')
            df_vn_yield['Spot_Rate_Annual_Pct'] = pd.to_numeric(df_vn_yield['Spot_Rate_Annual_Pct'], errors='coerce')
            df_vn_yield_10y = df_vn_yield[df_vn_yield['Term'] == '10 năm'][['Date', 'Spot_Rate_Annual_Pct']].rename(columns={'Spot_Rate_Annual_Pct': '10Y'})
            df_vn_yield_3m = df_vn_yield[df_vn_yield['Term'] == '3 tháng'][['Date', 'Spot_Rate_Annual_Pct']].rename(columns={'Spot_Rate_Annual_Pct': '3M'})
            df_vn_spread = pd.merge(df_vn_yield_10y, df_vn_yield_3m, on='Date', how='inner')
            df_vn_spread['Spread'] = df_vn_spread['10Y'] - df_vn_spread['3M']
            t_vny, min_vny, max_vny = get_range_7d(df_vn_spread, 'Date', 'Spread', T)
            results['VN_Yield_Spread_T'] = f"{t_vny:.2f}% (L: {min_vny:.2f}% - H: {max_vny:.2f}%)" if not pd.isna(t_vny) else "N/A"
            results['VN_Yield_Spread_1W'] = get_closest_val(df_vn_spread, 'Date', 'Spread', T_1W)
            results['VN_Yield_Spread_1M'] = get_closest_val(df_vn_spread, 'Date', 'Spread', T_1M)
            results['VN_Yield_Spread_1Y'] = get_closest_val(df_vn_spread, 'Date', 'Spread', T_1Y)

        # 6. SBV OMO Net 30D
        if df_sbv_omo is not None and not df_sbv_omo.empty:
            df_sbv_omo['Giá trị bơm ròng'] = pd.to_numeric(df_sbv_omo['Giá trị bơm ròng'], errors='coerce').fillna(0)
            df_sbv_omo_daily = df_sbv_omo.groupby('Ngày')['Giá trị bơm ròng'].sum().reset_index()
            df_sbv_omo_daily = df_sbv_omo_daily.set_index('Ngày').reindex(pd.date_range(df_sbv_omo_daily['Ngày'].min(), T)).fillna(0).reset_index().rename(columns={'index':'Ngày'})
            df_sbv_omo_daily['Rolling_30D'] = df_sbv_omo_daily['Giá trị bơm ròng'].rolling(window=30, min_periods=1).sum()
            t_omo, min_omo, max_omo = get_range_7d(df_sbv_omo_daily, 'Ngày', 'Rolling_30D', T)
            results['SBV_OMO_Net_T'] = f"{t_omo:,.0f} (L: {min_omo:,.0f} - H: {max_omo:,.0f})" if not pd.isna(t_omo) else "N/A"
            results['SBV_OMO_Net_1W'] = get_closest_val(df_sbv_omo_daily, 'Ngày', 'Rolling_30D', T_1W)
            results['SBV_OMO_Net_1M'] = get_closest_val(df_sbv_omo_daily, 'Ngày', 'Rolling_30D', T_1M)
            results['SBV_OMO_Net_1Y'] = get_closest_val(df_sbv_omo_daily, 'Ngày', 'Rolling_30D', T_1Y)

        # 7. SBV OMO Rate
        if df_sbv_omo is not None and not df_sbv_omo.empty:
            df_sbv_omo_rate = df_sbv_omo.dropna(subset=['Lãi suất trúng thầu bên mua']).copy()
            df_sbv_omo_rate['Lãi suất'] = pd.to_numeric(df_sbv_omo_rate['Lãi suất trúng thầu bên mua'], errors='coerce')
            df_sbv_omo_rate['Lãi suất'] = df_sbv_omo_rate['Lãi suất'].replace(0, np.nan).ffill()
            df_sbv_omo_rate = df_sbv_omo_rate.groupby('Ngày')['Lãi suất'].mean().reset_index()
            t_omor, min_omor, max_omor = get_range_7d(df_sbv_omo_rate, 'Ngày', 'Lãi suất', T)
            results['SBV_OMO_Rate_T'] = f"{t_omor:.2f}% (L: {min_omor:.2f}% - H: {max_omor:.2f}%)" if not pd.isna(t_omor) else "N/A"
            results['SBV_OMO_Rate_1W'] = get_closest_val(df_sbv_omo_rate, 'Ngày', 'Lãi suất', T_1W)
            results['SBV_OMO_Rate_1M'] = get_closest_val(df_sbv_omo_rate, 'Ngày', 'Lãi suất', T_1M)
            results['SBV_OMO_Rate_1Y'] = get_closest_val(df_sbv_omo_rate, 'Ngày', 'Lãi suất', T_1Y)

        # 8. SBV Interbank Rate (ON)
        if df_sbv_ib is not None and not df_sbv_ib.empty:
            df_sbv_ib['Date'] = pd.to_datetime(df_sbv_ib['Date'], format="%d/%m/%Y", errors='coerce')
            df_sbv_ib_on = df_sbv_ib[df_sbv_ib['Term'].astype(str).str.contains('Qua đêm', na=False, case=False)].copy()
            df_sbv_ib_on['Rate'] = pd.to_numeric(df_sbv_ib_on['Rate'], errors='coerce')
            t_ib, min_ib, max_ib = get_range_7d(df_sbv_ib_on, 'Date', 'Rate', T)
            results['SBV_IB_Rate_T'] = f"{t_ib}% (L: {min_ib}% - H: {max_ib}%)" if not pd.isna(t_ib) else "N/A"
            results['SBV_IB_Rate_1W'] = get_closest_val(df_sbv_ib_on, 'Date', 'Rate', T_1W)
            results['SBV_IB_Rate_1M'] = get_closest_val(df_sbv_ib_on, 'Date', 'Rate', T_1M)
            results['SBV_IB_Rate_1Y'] = get_closest_val(df_sbv_ib_on, 'Date', 'Rate', T_1Y)

        # 9. SBV Interbank Volume (5D Avg)
        if df_sbv_ib is not None and not df_sbv_ib.empty:
            df_sbv_ib['Volume'] = pd.to_numeric(df_sbv_ib['Volume'], errors='coerce')
            df_ib_vol_daily = df_sbv_ib.groupby('Date')['Volume'].sum().reset_index()
            df_ib_vol_daily['Vol_5D_Avg'] = df_ib_vol_daily['Volume'].rolling(window=5, min_periods=1).mean()
            t_vol, min_vol, max_vol = get_range_7d(df_ib_vol_daily, 'Date', 'Vol_5D_Avg', T)
            results['SBV_IB_Vol_T'] = f"{t_vol:,.0f} (L: {min_vol:,.0f} - H: {max_vol:,.0f})" if not pd.isna(t_vol) else "N/A"
            results['SBV_IB_Vol_1W'] = get_closest_val(df_ib_vol_daily, 'Date', 'Vol_5D_Avg', T_1W)
            results['SBV_IB_Vol_1M'] = get_closest_val(df_ib_vol_daily, 'Date', 'Vol_5D_Avg', T_1M)
            results['SBV_IB_Vol_1Y'] = get_closest_val(df_ib_vol_daily, 'Date', 'Vol_5D_Avg', T_1Y)

        # 10. US OMO Net 30D
        if df_us_omo is not None and not df_us_omo.empty:
            df_us_omo['Ngày'] = pd.to_datetime(df_us_omo['Ngày'], format="%d/%m/%Y", errors='coerce')
            df_us_omo['Giá trị bơm ròng'] = pd.to_numeric(df_us_omo['Giá trị bơm ròng'], errors='coerce').fillna(0)
            df_us_omo_daily = df_us_omo.groupby('Ngày')['Giá trị bơm ròng'].sum().reset_index()
            df_us_omo_daily = df_us_omo_daily.set_index('Ngày').reindex(pd.date_range(df_us_omo_daily['Ngày'].min(), T)).fillna(0).reset_index().rename(columns={'index':'Ngày'})
            df_us_omo_daily['Rolling_30D'] = df_us_omo_daily['Giá trị bơm ròng'].rolling(window=30, min_periods=1).sum()
            t_us_omo, min_us_omo, max_us_omo = get_range_7d(df_us_omo_daily, 'Ngày', 'Rolling_30D', T)
            results['US_OMO_Net_T'] = f"{t_us_omo:,.2f} (L: {min_us_omo:,.2f} - H: {max_us_omo:,.2f})" if not pd.isna(t_us_omo) else "N/A"
            results['US_OMO_Net_1W'] = get_closest_val(df_us_omo_daily, 'Ngày', 'Rolling_30D', T_1W)
            results['US_OMO_Net_1M'] = get_closest_val(df_us_omo_daily, 'Ngày', 'Rolling_30D', T_1M)
            results['US_OMO_Net_1Y'] = get_closest_val(df_us_omo_daily, 'Ngày', 'Rolling_30D', T_1Y)

        # Format Final Output String
        output = "--- DASHBOARD STATS ---\n"
        for k, v in results.items():
            output += f"{k}: {v}\n"
            
        output += "\n--- FEDWATCH PROBABILITIES ---\n"
        if df_fedwatch is not None and not df_fedwatch.empty:
            output += df_fedwatch.head(10).to_string()
            
        return output
    except Exception as e:
        return f"Lỗi trong quá trình tính toán data_processor: {e}"
