import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urlparse
import re
import os
from concurrent.futures import ThreadPoolExecutor
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

class VbplvnCrawler:
    def __init__(self, url, output_folder):
        self.url = url
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        self.output_folder = output_folder

    def crawl_to_html(self):
        response = requests.get(self.url, headers=self.header)
        if response.status_code == 200:
            print("Crawl HTML thành công")
            return response.content
        else:
            print(f"Không thể truy cập trang web. Mã trạng thái: {response.status_code}")
            return None

    def extract_links(self):
        html_content = self.crawl_to_html()
        if html_content is None:
            print("Không thể thực hiện trích xuất link do lỗi crawl HTML.")
            return []

        soup = BeautifulSoup(html_content, "html.parser")
        links = set()
        for a_tag in soup.find_all("a", class_="toanvan", href=True):
            href = a_tag["href"]
            links.add(href)

        print(f"Đã trích xuất {len(links)} đường dẫn từ nội dung HTML")
        return list(links)
    
    
    def crawl_links_to_txt(self):
        links = self.extract_links()
        links.insert(0, self.url)
        if not links:
            print("Không có link nào để crawl.")
            return
        os.makedirs(self.output_folder, exist_ok=True)
        print(links)

        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Kích hoạt chế độ không hiển thị giao diện

        resolved_links = set()

        def resolve_final_url(link):
            driver = webdriver.Chrome(options=chrome_options)
            driver.get(link)
            final_url = driver.current_url
            driver.quit()
            return final_url
        
        def crawl_and_save(link):
            nonlocal resolved_links
            full_url = link if link == self.url else "https://vbpl.vn" + link
            full_url = resolve_final_url(full_url)
            if not full_url or full_url in resolved_links:  # Bỏ qua nếu link trùng
                print(f"Bỏ qua link trùng lặp: {full_url}")
                return
            resolved_links.add(full_url)
            try:
                response = requests.get(full_url, headers=self.header, timeout=60)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, "html.parser")
                    content_div = soup.find("div", class_="fulltext")

                    if content_div:
                        content = content_div.get_text(separator="\n", strip=True)
                        parsed_url = urlparse(full_url)
                        path = parsed_url.path
                        query = parsed_url.query
                        file_name = re.sub(r'\W+', '_', path.strip('/').replace('/', '_'))
                        if query:
                            query_part = re.sub(r'\W+', '_', query)
                            file_name += f"_{query_part}"

                        file_name += ".txt"
                        file_path = os.path.join(self.output_folder, file_name)

                        with open(file_path, "w", encoding="utf-8") as file:
                            file.write(f"link văn bản: {full_url}\n")
                            file.write(content)

                        print(f"Đã crawl dữ liệu từ {full_url} và lưu vào {file_path}")
                    else:
                        print(f"Không tìm thấy nội dung trong thẻ class='fulltext' tại {full_url}.")
                else:
                    print(f"Không thể truy cập {full_url}. Mã trạng thái: {response.status_code}")
            except Exception as e:
                print(f"Lỗi khi crawl {full_url}: {e}")

        # Sử dụng ThreadPoolExecutor để crawl song song
        with ThreadPoolExecutor(max_workers=12) as executor:
            executor.map(crawl_and_save, links)


if __name__ == "__main__":
    url = "https://vbpl.vn/nganhangnhanuoc/Pages/vbpq-toanvan.aspx?ItemID=126820&dvid=326"
    output_folder = "/home/vanh/Project_BA/LightRAG/assets/test1"

    crawler = VbplvnCrawler(url, output_folder)
    crawler.crawl_links_to_txt()
