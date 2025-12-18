import requests
from bs4 import BeautifulSoup
import json
import datetime
import re
import time
import os  # 新增：用于处理文件夹路径

# ================= 配置区域 =================
# 模拟浏览器头信息，防止被反爬
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

# 赤峰天气代码 (中国天气网标准代码)
CITY_CODE = "101080601" 

# 输出文件夹名称
OUTPUT_DIR = "data"
# ===========================================

def get_current_date():
    """获取当前日期字符串"""
    return datetime.datetime.now().strftime("%m月%d日")

# ------------------------------------------------------
# 1. 抓取油价
# ------------------------------------------------------
def get_oil_price():
    print("正在获取油价信息...")
    url = "http://www.huangjinjiage.cn/oil/chifeng.html" 
    
    data = {
        "updateDate": get_current_date(),
        "prices": {"p92": "--", "p95": "--", "p98": "--"},
        "alert": "暂无数据"
    }

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')

        # [解析日期]
        jart_con = soup.find('div', id='JartCon')
        if jart_con:
            p_text = jart_con.find('p').get_text()
            date_match = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日)', p_text)
            if date_match:
                data["updateDate"] = date_match.group(1)
            
            if "下一个油价调整日" in p_text:
                parts = p_text.split("；")
                if len(parts) > 1:
                    data["alert"] = parts[1].strip()

        # [解析表格]
        table = soup.find('table', class_='bx')
        if table:
            rows = table.find_all('tr')
            if len(rows) >= 2:
                headers = [th.get_text(strip=True) for th in rows[0].find_all('th')]
                values = [td.get_text(strip=True) for td in rows[1].find_all('td')]

                price_map = {}
                for i, name in enumerate(headers):
                    if i < len(values):
                        price_map[name] = values[i]

                data["prices"]["p92"] = price_map.get("92号汽油", "--")
                data["prices"]["p95"] = price_map.get("95号汽油", "--")
                data["prices"]["p98"] = price_map.get("98号汽油", "--")

    except Exception as e:
        print(f"油价获取失败: {e}")
    
    return data

# ------------------------------------------------------
# 2. 抓取双色球
# ------------------------------------------------------
def get_lottery():
    print("正在获取双色球信息...")
    url = "https://www.cwl.gov.cn/ygkj/kjgg/"
    
    data = {
        "issue": "最新期", 
        "red": [], 
        "blue": "00",
        "pool": "统计中..."
    }

    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.encoding = 'utf-8'
        soup = BeautifulSoup(r.text, 'html.parser')

        ssq_area = soup.find('div', class_='notice-item ssq')
        if ssq_area:
            # 获取期号
            title_div = ssq_area.find('div', class_='notice-content-title')
            if title_div:
                raw_text = title_div.get_text()
                match = re.search(r'第(\d+)期', raw_text)
                if match:
                    data["issue"] = match.group(1)

            # 获取球号
            qiu_div = ssq_area.find('div', class_='qiu')
            if qiu_div:
                nums = []
                containers = qiu_div.find_all('div', class_='lotteryNumContainer')
                for container in containers:
                    num_div = container.find('div', class_='lotteryNum')
                    if num_div:
                        nums.append(num_div.get_text(strip=True))
                
                if len(nums) >= 7:
                    data["red"] = nums[:6]
                    data["blue"] = nums[-1]

            # 获取奖池
            pool_div = ssq_area.find('div', class_='pool-money')
            if pool_div:
                 data["pool"] = pool_div.get_text(strip=True)
            
    except Exception as e:
        print(f"双色球获取失败: {e}")

    return data

# ------------------------------------------------------
# 3. 抓取天气 (无图标版)
# ------------------------------------------------------
def get_weather():
    print("正在获取天气信息...")
    url = f"http://www.weather.com.cn/data/cityinfo/{CITY_CODE}.html"
    
    try:
        r = requests.get(url, headers=HEADERS, timeout=5)
        r.encoding = 'utf-8'
        res_json = r.json()
        info = res_json['weatherinfo']
        
        return {
            "city": info['city'],
            "temp": f"{info['temp1']} ~ {info['temp2']}",
            "condition": info['weather']
        }
    except Exception as e:
        print(f"天气获取失败: {e}")
        return {"city": "赤峰", "temp": "--", "condition": "未知"}

# ------------------------------------------------------
# 主程序入口
# ------------------------------------------------------
def main():
    print("=== 开始全量更新数据 ===")
    
    final_data = {
        "update_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "oil": get_oil_price(),
        "lottery": get_lottery(),
        "weather": get_weather()
    }
    
    # --- 关键修改：处理文件夹路径 ---
    # 1. 检查是否存在 'data' 文件夹，不存在则创建
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"已自动创建文件夹: {OUTPUT_DIR}")
    
    # 2. 拼接完整路径: data/data.json
    file_path = os.path.join(OUTPUT_DIR, "data.json")
    
    # 3. 保存文件
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(final_data, f, ensure_ascii=False, indent=4)
        print(f"\n✅ 数据更新成功！")
        print(f"📂 文件已保存至: {os.path.abspath(file_path)}")
        # 打印结果供确认
        # print(json.dumps(final_data, ensure_ascii=False, indent=4))
    except Exception as e:
        print(f"\n❌ 文件写入失败: {e}")

if __name__ == "__main__":
    main()