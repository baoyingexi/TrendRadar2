# coding=utf-8
import requests
from bs4 import BeautifulSoup
import json
import datetime
import re
import os
import urllib3

# 禁用安全警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= 配置区域 =================
# 您的中转站
PROXY_BASE = "http://baoyingege.dpdns.org"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
}

OUTPUT_DIR = "data"
OUTPUT_FILE = "data.json"
# ===========================================

def get_current_date_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def fetch_via_proxy(target_url):
    try:
        print(f"🌍 [请求] {target_url}")
        payload = {'url': target_url}
        
        # 发送请求
        res = requests.get(PROXY_BASE, params=payload, headers=HEADERS, timeout=30, verify=False)
        
        # 🔥【关键修复】针对 500.com 强制使用 GBK 编码，否则中文乱码正则会失效！
        if "500.com" in target_url:
            res.encoding = 'gbk'
        else:
            res.encoding = res.apparent_encoding 
            
        if res.status_code == 200:
            return res.text
        else:
            print(f"❌ 代理返回错误: {res.status_code}")
            return None
    except Exception as e:
        print(f"❌ 代理连接失败: {e}")
        return None

# 1. 抓取油价
def get_oil_price():
    print("\n>>> 正在获取油价...")
    target_url = "http://www.huangjinjiage.cn/oil/chifeng.html"
    
    data = {
        "updateDate": datetime.datetime.now().strftime("%Y年%m月%d日"),
        "prices": {"p92": "--", "p95": "--", "p98": "--"},
        "alert": ""
    }

    html = fetch_via_proxy(target_url)
    if not html: return data

    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # 抓取提示信息
        jart_con = soup.find('div', id='JartCon')
        if jart_con:
            text = jart_con.get_text()
            if "；" in text:
                parts = text.split("；")
                if len(parts) > 1:
                    data["alert"] = parts[1].strip().replace("。", "")
            date_match = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日)', text)
            if date_match: data["updateDate"] = date_match.group(1)

        # 抓取价格
        all_rows = soup.find_all('tr')
        target_row_index = -1
        for i, row in enumerate(all_rows):
            if "92号汽油" in row.get_text(strip=True):
                target_row_index = i
                break
        
        if target_row_index != -1 and target_row_index + 1 < len(all_rows):
            cols = all_rows[target_row_index + 1].find_all(['td', 'th'])
            if len(cols) >= 4:
                p92 = cols[1].get_text(strip=True)
                p95 = cols[2].get_text(strip=True)
                p98 = cols[3].get_text(strip=True)
                if any(char.isdigit() for char in p92): data["prices"]["p92"] = p92
                if any(char.isdigit() for char in p95): data["prices"]["p95"] = p95
                if any(char.isdigit() for char in p98): data["prices"]["p98"] = p98
                print(f"✅ 油价成功: {p92}")

    except Exception as e:
        print(f"❌ 油价解析错误: {e}")
    return data

# 2. 抓取双色球 (修正版)
def get_lottery():
    print("\n>>> 正在获取双色球(500彩票网)...")
    target_url = "http://kaijiang.500.com/ssq.shtml"
    
    data = {
        "issue": "统计中...", "red": [], "blue": "--", "pool": ""
    }

    html = fetch_via_proxy(target_url)
    if not html: return data

    try:
        soup = BeautifulSoup(html, 'html.parser')
        page_text = soup.get_text() # 获取纯文本
        
        # 红球
        red_balls = soup.find_all('li', class_='ball_red')
        if red_balls: data["red"] = [b.get_text(strip=True) for b in red_balls[:6]]
        
        # 蓝球
        blue_ball = soup.find('li', class_='ball_blue')
        if blue_ball: data["blue"] = blue_ball.get_text(strip=True)
            
        # 🔥【关键修复】正则允许"第"和数字之间有空格 (\s*)
        issue_match = re.search(r'第\s*(\d{5})\s*期', page_text)
        if issue_match:
            data["issue"] = issue_match.group(1)
            print(f"✅ 抓到期号: {data['issue']}")

        # 🔥【关键修复】奖池匹配更宽松
        pool_match = re.search(r"奖池滚存[^\d]*([\d,]+)", page_text)
        if pool_match:
            raw_money = pool_match.group(1).replace(",", "")
            try:
                data["pool"] = f"{float(raw_money)/100000000:.2f}亿"
            except:
                data["pool"] = raw_money
            print(f"✅ 抓到奖池: {data['pool']}")

    except Exception as e:
        print(f"❌ 双色球解析异常: {e}")
    return data

# 3. 抓取天气
def get_weather():
    print("\n>>> 正在获取天气...")
    url = "https://api.open-meteo.com/v1/forecast?latitude=42.26&longitude=118.96&current_weather=true&timezone=Asia%2FShanghai"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        d = res.json()
        current = d.get('current_weather', {})
        code = current.get('weathercode', 0)
        temp = current.get('temperature', '--')
        
        # 映射天气描述
        condition = "晴"
        if code in [1, 2, 3]: condition = "多云"
        elif code in [45, 48]: condition = "阴"
        elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]: condition = "雨"
        elif code in [71, 73, 75, 77, 85, 86]: condition = "雪"
        
        print(f"✅ 天气: {temp}°C {condition}")
        return {"city": "赤峰", "temp": str(temp), "condition": condition}
    except:
        return {"city": "赤峰", "temp": "--", "condition": "未知"}

def main():
    print(f"=== 开始更新 [{get_current_date_str()}] ===")
    final_data = {
        "update_time": get_current_date_str(),
        "oil": get_oil_price(),
        "lottery": get_lottery(),
        "weather": get_weather()
    }
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(os.path.join(OUTPUT_DIR, OUTPUT_FILE), "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    print("\n✅ 更新完成")

if __name__ == "__main__":
    main()
