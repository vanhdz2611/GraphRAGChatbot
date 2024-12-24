import scrapy
from scrapy.crawler import CrawlerProcess
from urllib.parse import urljoin
import os

class MicCrawler:
    def __init__(self, base_url, output_folder):
        self.base_url = base_url
        self.output_folder = output_folder
        self.process = CrawlerProcess()

    def get_links(self, response):
        """
        Hàm lấy tất cả các liên kết từ trang web.
        """
        if "van-ban-phap-luat.htm" in response.url:

            # Home page: Extract links from the 'box-table'
            hrefs = response.xpath('.//div[@class="box-table"]//a[@class="view-more"]/@href').getall()
            new_urls = [urljoin(response.url, href) for href in hrefs]
            print(f"Found {len(new_urls)} links on the homepage.")
            return new_urls
        else:
            # Post page: Extract links from the 'nd' class
            nd_links = response.xpath('.//div[@class="nd"]//a/@href').getall()
            print(f"Found {len(nd_links)} links on the post page.")
            return [urljoin(response.url, link) for link in nd_links]

    def crawl_links_to_txt(self):
        class MicSpider(scrapy.Spider):
            name = "mic"
            start_urls = [self.base_url]

            def __init__(self, output_folder, *args, **kwargs):
                super(MicSpider, self).__init__(*args, **kwargs)
                self.output_folder = output_folder  # Lưu output_folder vào spider

            def parse(self, response):
                # Gọi hàm get_links từ đối tượng MicCrawler
                links = crawler.get_links(response)

                # In ra tất cả các liên kết
                print(f"Links found: {links}")

                # Crawl nội dung của trang chính (home page) trước
                self.save_page_content(response)

                # Tiến hành crawl mỗi liên kết
                for url in links:
                    print(f"Crawling URL: {url}")  # In ra URL đang crawl
                    yield scrapy.Request(url=url, callback=self.save_link_content)

            def save_page_content(self, response):
                """
                Hàm lưu nội dung của trang chính.
                """
                print(f"Processing home page: {response.url}")  # In ra URL trang chính
                content = response.xpath('.//div[@id="vbct2"]//text()').getall()
                content = '\n'.join(content).strip()

                if not content:
                    print(f"No content found on {response.url}")  # In ra nếu không có nội dung
                    return

                # Save content to a file for the current page (home page)
                filename = response.url.split("/")[-1] + ".txt"
                if not os.path.exists(self.output_folder):
                    os.makedirs(self.output_folder)

                file_path = os.path.join(self.output_folder, filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                print(f"Content saved to {file_path}")  # Để kiểm tra xem đã lưu thành công chưa
                #yield {'content': content}

            def save_link_content(self, response):
                """
                Hàm lưu nội dung từ mỗi liên kết.
                """
                print(f"Processing {response.url}")  # In ra URL đang xử lý
                content = response.xpath('.//div[@id="vbct2"]//text()').getall()
                content = '\n'.join(content).strip()

                if not content:
                    print(f"No content found on {response.url}")  # In ra nếu không có nội dung
                    return

                # Save content from the link to a file
                filename = response.url.split("/")[-1] + ".txt"
                if not os.path.exists(self.output_folder):
                    os.makedirs(self.output_folder)

                file_path = os.path.join(self.output_folder, filename)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                print(f"Content saved to {file_path}")  # Để kiểm tra xem đã lưu thành công chưa
                #yield {'content': content}

        # Start the crawling process
        self.process.crawl(MicSpider, output_folder=self.output_folder)
        self.process.start()

if __name__ == "__main__":
    # Specify the base URL and output folder
    base_url = "https://mic.gov.vn/van-ban-phap-luat/25036.htm"
    output_folder = "output9"

    # Create an instance of MicCrawler
    crawler = MicCrawler(base_url, output_folder)

    # Start the crawling process
    print(f"Starting crawl for {base_url}. Data will be saved in '{output_folder}' directory.")
    crawler.crawl_links_to_txt()
    print("Crawling completed.")
