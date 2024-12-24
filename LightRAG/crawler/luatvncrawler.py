import requests
from bs4 import BeautifulSoup
from langchain_community.document_loaders import SeleniumURLLoader
import time
from urllib.parse import urlparse
import re
import os
from concurrent.futures import ThreadPoolExecutor

class LuatvnCrawler:
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
        for a_tag in soup.find_all("a", href=True):
            href = a_tag["href"]

            if not a_tag.has_attr("class") and href.endswith(".html") and not href.startswith("https") and href.count("/") >= 2:
                links.add(href)

        print(f"Đã trích xuất {len(links)} đường dẫn từ nội dung HTML")
        print(list(links))
        return list(links)
    
    
    def crawl_links_to_txt(self):
        links = self.extract_links()
        links.insert(0, self.url)
        if not links:
            print("Không có link nào để crawl.")
            return
        os.makedirs(self.output_folder, exist_ok=True)
        n = 0  # Biến đếm số lượng link đã xử lý

        def crawl_and_save(link):
            nonlocal n
                
            full_url = link if link == self.url else "https://luatvietnam.vn" + link
            start_time = time.time()
            try:
                loader = SeleniumURLLoader([full_url])
                doc = loader.load()
                if time.time() - start_time > 60:
                    print(f"Timeout: Cannot crawl {full_url} as it exceeded 60 seconds.")
                    return
                if doc:
                    page_content = doc[0].page_content
                    if page_content:
                        parsed_url = urlparse(full_url)
                        path = parsed_url.path
                        file_name = re.sub(r'\W+', '_', path.split("/")[-1]) + ".txt"
                        file_path = os.path.join(self.output_folder, file_name)

                        with open(file_path, "w", encoding="utf-8") as file:
                            file.write(page_content)
                            n += 1
                            print(n)
                        print(f"Đã crawl dữ liệu từ {full_url} và lưu vào {file_path}")
                    else:
                        print(f"No content found for {full_url}.")
                else:
                    print(f"Không thể crawl nội dung từ {full_url} bằng SeleniumURLLoader.")
            except Exception as e:
                print(f"Lỗi khi crawl {full_url}: {e}")

        # Sử dụng ThreadPoolExecutor để crawl song song
        with ThreadPoolExecutor(max_workers=12) as executor:
            executor.map(crawl_and_save, links)


if __name__ == "__main__":
    url = "https://luatvietnam.vn/can-bo/quyet-dinh-1555-qd-ttg-2024-bo-nhiem-dai-ta-do-quoc-an-giu-chuc-pho-tu-lenh-quan-chung-hai-quan-379298-d1.html"
    output_folder = "/home/vanh/Project_BA/data_crawler"

    crawler = LuatvnCrawler(url, output_folder)
    crawler.crawl_links_to_txt()