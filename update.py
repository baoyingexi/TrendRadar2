# coding=utf-8
import requests
from bs4 import BeautifulSoup
import json
import datetime
import re
import os
import urllib3
import xml.etree.ElementTree as ET

# 禁用安全警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ================= 配置区域 =================
# 您的中转站（你的代理）
PROXY_BASE = "http://baoyingege.dpdns.org"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

OUTPUT_DIR = "data"
OUTPUT_FILE = "data.json"
# ===========================================


def get_current_date_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def fetch_via_proxy(target_url: str) -> str | None:
    """通过中转站抓取目标页面，返回文本；抓不到返回 None。
    注意：不做任何“兜底猜测”，只返回真实响应文本。
    """
    try:
        print(f"🌍 [请求] {target_url}")
        payload = {"url": target_url}

        res = requests.get(
            PROXY_BASE,
            params=payload,
            headers=HEADERS,
            timeout=30,
            verify=False,
        )

        if res.status_code != 200:
            print(f"❌ 代理返回错误: {res.status_code}")
            return None

        # ✅ 不强制 gbk：交给 requests 自动识别
        res.encoding = res.apparent_encoding

        return res.text

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
        "alert": "",
    }

    html = fetch_via_proxy(target_url)
    if not html:
        return data

    try:
        soup = BeautifulSoup(html, "html.parser")

        # 抓取提示信息
        jart_con = soup.find("div", id="JartCon")
        if jart_con:
            text = jart_con.get_text()
            if "；" in text:
                parts = text.split("；")
                if len(parts) > 1:
                    data["alert"] = parts[1].strip().replace("。", "")
            date_match = re.search(r"(\d{4}年\d{1,2}月\d{1,2}日)", text)
            if date_match:
                data["updateDate"] = date_match.group(1)

        # 抓取价格
        all_rows = soup.find_all("tr")
        target_row_index = -1
        for i, row in enumerate(all_rows):
            if "92号汽油" in row.get_text(strip=True):
                target_row_index = i
                break

        if target_row_index != -1 and target_row_index + 1 < len(all_rows):
            cols = all_rows[target_row_index + 1].find_all(["td", "th"])
            if len(cols) >= 4:
                p92 = cols[1].get_text(strip=True)
                p95 = cols[2].get_text(strip=True)
                p98 = cols[3].get_text(strip=True)
                if any(ch.isdigit() for ch in p92):
                    data["prices"]["p92"] = p92
                if any(ch.isdigit() for ch in p95):
                    data["prices"]["p95"] = p95
                if any(ch.isdigit() for ch in p98):
                    data["prices"]["p98"] = p98

        print(f"✅ 油价成功: {data['prices']['p92']}")

    except Exception as e:
        print(f"❌ 油价解析错误: {e}")

    return data


# 2. 抓取双色球（严格：只取真实抓到的，不做任何兜底填充）
def get_lottery():
    print("\n>>> 正在获取双色球(严格模式：抓到什么就是什么)...")

    data = {"issue": "统计中...", "red": [], "blue": "--", "pool": ""}

    # 2.1 先尝试 XML（抓不到就算了，不再推断）
    xml_url = "https://kaijiang.500.com/static/info/kaijiang/xml/ssq.xml"
    xml_text = fetch_via_proxy(xml_url)

    if xml_text:
        # 不是 XML 就直接放弃该路径
        if "<?xml" in xml_text or "<row" in xml_text:
            try:
                start = xml_text.find("<?xml")
                if start != -1:
                    xml_text = xml_text[start:]

                root = ET.fromstring(xml_text)
                rows = root.findall(".//row")
                if rows:
                    latest = rows[0]
                    issue = latest.attrib.get("expect") or latest.attrib.get("issue") or ""
                    red = latest.attrib.get("red") or ""
                    blue = latest.attrib.get("blue") or ""

                    reds = [x for x in re.split(r"[,\s]+", red.strip()) if x]

                    if issue and re.fullmatch(r"\d{5}", issue):
                        data["issue"] = issue
                    if len(reds) >= 6:
                        data["red"] = reds[:6]
                    if blue:
                        data["blue"] = blue.strip()

                    print(f"✅ XML 抓到：期号={data['issue']} 红={data['red']} 蓝={data['blue']}")
                    return data
            except Exception as e:
                print(f"❌ XML 解析失败：{e}")
        else:
            print("❌ 拿到的不是 XML（严格模式：不再继续从该响应推断）")

    # 2.2 再尝试 HTML（只取能选到的内容，不猜期号、不补奖池）
    html_url = "https://kaijiang.500.com/ssq.shtml"
    html = fetch_via_proxy(html_url)
    if not html:
        return data

    try:
        soup = BeautifulSoup(html, "html.parser")

        # 期号：只在页面真实出现 “xxxxx期” 时才写入
        title_td = soup.select_one("td.table-title")
        if title_td:
            m = re.search(r"(\d{5})\s*期", title_td.get_text(strip=True))
            if m:
                data["issue"] = m.group(1)

        # 红球：只取页面真实出现的 span
        reds = [x.get_text(strip=True) for x in soup.select("span.ball-red-normal.ball")]
        if len(reds) >= 6:
            data["red"] = reds[:6]

        # 蓝球：只取页面真实出现的 span
        blue_el = soup.select_one("span.ball-blue-normal.ball")
        if blue_el:
            data["blue"] = blue_el.get_text(strip=True)

        # 奖池：严格模式，仅当页面文本确实匹配到才写入
        page_text = soup.get_text(" ", strip=True)
        pool_match = re.search(r"奖池滚存[^\d]*([\d,]+)", page_text)
        if pool_match:
            raw_money = pool_match.group(1).replace(",", "")
            data["pool"] = raw_money  # 严格模式：不做“换算成亿”的推断

        print(f"✅ HTML 抓到：期号={data['issue']} 红={data['red']} 蓝={data['blue']} 奖池={data['pool'] or '--'}")

    except Exception as e:
        print(f"❌ HTML 解析异常：{e}")

    return data


# 3. 抓取天气（直连）
def get_weather():
    print("\n>>> 正在获取天气...")
    url = "https://api.open-meteo.com/v1/forecast?latitude=42.26&longitude=118.96&current_weather=true&timezone=Asia%2FShanghai"
    try:
        res = requests.get(url, headers=HEADERS, timeout=15)
        d = res.json()
        current = d.get("current_weather", {})
        code = current.get("weathercode", 0)
        temp = current.get("temperature", "--")

        condition = "晴"
        if code in [1, 2, 3]:
            condition = "多云"
        elif code in [45, 48]:
            condition = "阴"
        elif code in [51, 53, 55, 61, 63, 65, 80, 81, 82]:
            condition = "雨"
        elif code in [71, 73, 75, 77, 85, 86]:
            condition = "雪"

        print(f"✅ 天气: {temp}°C {condition}")
        return {"city": "赤峰", "temp": str(temp), "condition": condition}
    except Exception:
        return {"city": "赤峰", "temp": "--", "condition": "未知"}


def main():
    print(f"=== 开始更新 [{get_current_date_str()}] ===")

    final_data = {
        "update_time": get_current_date_str(),
        "oil": get_oil_price(),
        "lottery": get_lottery(),
        "weather": get_weather(),
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)

    print("✅ 更新完成")


if __name__ == "__main__":
    main()
