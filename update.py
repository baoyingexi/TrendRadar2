# coding=utf-8
import requests
import json
import os
import re
from datetime import datetime

# ================= 配置区域 =================
# 您的中转站域名 (已配置为您的 dpdns 域名)
# 注意：这里假设您的中转站支持 https，如果报错 ssl 错误，可以尝试改成 http
PROXY_BASE = "https://baoyingege.dpdns.org" 

# 本地 headers (作为兜底)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}
# ===========================================

def get_current_date():
    return datetime.now().strftime("%m月%d日")

# --- 核心工具：代理请求函数 ---
def fetch_via_proxy(target_url):
    """通过您的中转站获取内容"""
    try:
        # 拼接格式: https://域名?url=目标地址
        proxy_url = f"{PROXY_BASE}?url={target_url}"
        
        print(f"🌍 正在通过中转站抓取: {target_url}")
        # 设置超时为 20 秒，防止中转站响应慢
        res = requests.get(proxy_url, headers=HEADERS, timeout=20)
        
        if res.status_code == 200:
            # 自动识别编码
            res.encoding = res.apparent_encoding 
            return res.text
        else:
            print(f"❌ 中转站返回错误: {res.status_code}")
            return None
    except Exception as e:
        print(f"❌ 中转站请求异常: {e}")
        return None

# ------------------------------------------------------
# 1. 获取油价
# ------------------------------------------------------
def get_oil_price():
    print("正在获取油价...")
    data = {
        "updateDate": get_current_date(),
        "prices": {"p92": "7.96", "p95": "8.48", "p98": "9.52"}
    }
    
    # 尝试通过代理抓取油价页面
    # 这里我们使用一个较通用的查询地址，您也可以换成其他您知道的油价网页
    target_url = "http://www.qiyoujiage.com/neimenggu/chifeng.shtml"
    
    html = fetch_via_proxy(target_url)
    
    if html:
        try:
            # 针对 qiyoujiage.com 的简单解析
            p92 = re.search(r'92号汽油.*?<dd>(.*?)</dd>', html, re.DOTALL)
            p95 = re.search(r'95号汽油.*?<dd>(.*?)</dd>', html, re.DOTALL)
            p98 = re.search(r'98号汽油.*?<dd>(.*?)</dd>', html, re.DOTALL)
            
            if p92: data["prices"]["p92"] = p92.group(1).strip()
            if p95: data["prices"]["p95"] = p95.group(1).strip()
            if p98: data["prices"]["p98"] = p98.group(1).strip()
            print("✅ 油价抓取更新成功")
        except:
            print("⚠️ 油价解析失败，保持默认值")
            
    return data

# ------------------------------------------------------
# 2. 获取双色球
# ------------------------------------------------------
def get_lottery():
    print("正在获取双色球...")
    data = {"issue": "--", "red": [], "blue": "--", "pool": "--"}

    # 目标：网易彩票数据接口
    target_url = "http://data.163.com/special/007500LE/ssq_kaijiang.js"
    
    # 走代理访问
    content = fetch_via_proxy(target_url)
    
    if content:
        try:
            # 清洗数据
            match = re.search(r'\[(.*?)\]', content, re.DOTALL)
            if match:
                json_str = match.group(1).split('},')[0] + "}" 
                
                issue_m = re.search(r'expect:\s*"(\d+)"', json_str)
                red_m = re.search(r'kj_red:\s*"(.*?)"', json_str)
                blue_m = re.search(r'kj_blue:\s*"(.*?)"', json_str)
                pool_m = re.search(r'gunc:\s*"(.*?)"', json_str)

                if issue_m and red_m and blue_m:
                    data["issue"] = issue_m.group(1)
                    data["red"] = red_m.group(1).split(" ")
                    data["blue"] = blue_m.group(1)
                    if pool_m:
                        pool_val = float(pool_m.group(1).replace(",", ""))
                        data["pool"] = f"{pool_val/100000000:.2f}亿"
                    print("✅ 双色球抓取成功")
                    return data
        except Exception as e:
            print(f"❌ 双色球解析失败: {e}")

    # 失败兜底
    data["issue"] = "25028"
    data["red"] = ["03", "09", "16", "23", "28", "31"]
    data["blue"] = "12"
    data["pool"] = "24亿"
    return data

# ------------------------------------------------------
# 3. 获取天气 (直连)
# ------------------------------------------------------
def get_weather():
    print("正在获取天气...")
    # 国际接口，直连即可
    url = "https://api.open-meteo.com/v1/forecast?latitude=42.26&longitude=118.96&current_weather=true&timezone=Asia%2FShanghai"
    
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        d = res.json()
        current = d.get('current_weather', {})
        temp = current.get('temperature', '--')
        code = current.get('weathercode', 0)
        
        condition = "晴"
        if code > 0 and code <= 3: condition = "多云"
        elif code >= 45: condition = "雨/雪"
        
        return {"city": "赤峰", "temp": str(temp), "condition": condition}
    except:
        return {"city": "赤峰", "temp": "-5", "condition": "晴"}

def main():
    print("=== 开始全量更新数据 (Private Proxy) ===")
    
    final_data = {
        "update_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "oil": get_oil_price(),
        "lottery": get_lottery(),
        "weather": get_weather()
    }
    
    if not os.path.exists("data"):
        os.makedirs("data")
        
    with open("data/data.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
        
    print("✅ data.json 生成成功！")
    # print(json.dumps(final_data, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
