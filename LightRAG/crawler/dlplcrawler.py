import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin
import os
import re
from concurrent.futures import ThreadPoolExecutor

class DLPLCrawler:
    def __init__(self, url, output_folder):
        self.url = url
        self.header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        self.output_folder = output_folder
        self.visited_links = set()

    def crawl_to_html(self, url):
        try:
            response = requests.get(url, headers=self.header)
            if response.status_code == 200:
                return response.content
            else:
                print(f"Không thể truy cập {url}. Mã trạng thái: {response.status_code}")
                return None
        except Exception as e:
            print(f"Lỗi khi crawl {url}: {e}")
            return None
        

    def extract_links(self, html_content, base_url, link_class):
        soup = BeautifulSoup(html_content, "html.parser")
        links = set()
        
        # Kiểm tra và in cấu trúc đầy đủ của widget_posts_section
        # Tìm tất cả các phần tử widget_posts
        # Tìm tất cả các phần tử widget_posts
        widget_posts_sections = soup.find_all("div", class_="widget_posts")

        # Biến để đếm số lượng liên kết đã lấy
        links_count = 0
        max_links = 10  # Giới hạn tối đa 10 liên kết

        # Duyệt qua từng phần tử để kiểm tra tiêu đề
        for widget_posts_section in widget_posts_sections:
            widget_title = widget_posts_section.find("h2", class_="widget-title")
            
            if widget_title:
                title_text = widget_title.get_text(strip=True)
                print(f"Tiêu đề trong widget-posts: {title_text}")
                
                # Kiểm tra nếu tiêu đề là "Văn bản Được hướng dẫn"
                if "Văn bản Được hướng dẫn" in title_text:
                    # Nếu tiêu đề phù hợp, lấy tất cả các liên kết
                    for tag in widget_posts_section.find_all("a", href=True):
                        # Kiểm tra nếu đã đạt đến giới hạn 10 liên kết
                        if links_count >= max_links:
                            break  # Dừng vòng lặp khi đã lấy đủ số lượng liên kết
                        
                        href = tag["href"]
                        full_url = urljoin(base_url, href)
                        links.add(full_url)
                        links_count += 1
                        print(f"Đã lấy liên kết: {full_url}")
                        
                # Nếu đã lấy đủ liên kết, thoát khỏi vòng lặp
                if links_count >= max_links:
                    break
            else:
                print("Không tìm thấy widget-title trong widget_posts")


        # Trích xuất các liên kết từ class legal-doc-title hoặc legal_doc_content
        for tag in soup.find_all("div", class_=link_class):
            a_tag = tag.find("a", href=True)
            if a_tag:
                href = a_tag["href"]
                full_url = urljoin(base_url, href)
                links.add(full_url)

        return list(links)

    def crawl_and_save(self, url):
        """
        Crawl nội dung từ bài viết chính và lưu vào file.
        """
        try:
            response = requests.get(url, headers=self.header)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                content_div = soup.find("div", class_="legal_doc_content")
                title_tag = soup.find("title")
                title = title_tag.get_text(strip=True) if title_tag else "no_title"

                if content_div:
                    content = content_div.get_text(separator="\n", strip=True)
                    sanitized_title = re.sub(r'\W+', '_', title)[:100]
                    file_name = f"{sanitized_title}.txt"
                    file_path = os.path.join(self.output_folder, file_name)

                    with open(file_path, "w", encoding="utf-8") as file:
                        file.write(content)

                    print(f"Đã lưu bài viết từ {url} vào {file_path}")
                else:
                    print(f"Không tìm thấy nội dung tại {url}")
            else:
                print(f"Không thể truy cập {url}. Mã trạng thái: {response.status_code}")
        except Exception as e:
            print(f"Lỗi khi crawl {url}: {e}")

    def is_main_page(self, url):
        """
        Kiểm tra xem URL có phải là trang chủ hay không.
        Trang chủ có số dấu '/' <= 3
        """
        parsed_url = urlparse(url)
        return len(parsed_url.path.split('/')) <= 3

    def crawl_links_to_txt(self):
        """
        Crawl các liên kết từ trang chủ hoặc bài viết chính và xử lý nội dung từng bài viết.
        """
        html_content = self.crawl_to_html(self.url)
        if not html_content:
            print("Không thể thực hiện crawl vì lỗi tải trang.")
            return

        links = []
        if self.is_main_page(self.url):
            # Extract links from the main page
            links = self.extract_links(html_content, self.url, "legal-doc-title")  # Trang chủ
            print(f"Đã tìm thấy {len(links)} liên kết từ trang chủ.")
        else:
            # Extract links from the article page
            links = self.extract_links(html_content, self.url, "legal_doc_content")  # Bài viết chính
            print(f"Đã tìm thấy {len(links)} liên kết từ bài viết chính.")

        # Start crawling and saving links
        with ThreadPoolExecutor(max_workers=12) as executor:
            executor.map(self.crawl_and_save, links)

if __name__ == "__main__":
    url = "https://dulieuphapluat.vn/van-ban/tai-nguyen-moi-truong-van-ban/cong-van-5400byt-dp-nam-2024-trien-khai-bien-phap-phong-chong-dich-benh-va-ve-sinh-moi-truong-trong-va-sau-mua-lu-va-ngap-lut-do-bo-y-te-ban-hanh-1200539.html"
    output_folder = "/mnt/dunghd/LightRAG/output9"

    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    crawler = DLPLCrawler(url, output_folder)
    crawler.crawl_links_to_txt()
