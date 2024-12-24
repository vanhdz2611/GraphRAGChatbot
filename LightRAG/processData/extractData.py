import os
import re
import textract
from urllib.parse import urlparse
from langchain_community.document_loaders import SeleniumURLLoader
import time

def crawl_to_txt(url, output_folder):
    start_time = time.time()
    timeout=60
    loader = SeleniumURLLoader([url])
    try:
        doc = loader.load()
        if time.time() - start_time > timeout:
            print(f"Cannot crawl {url} due to time out.")
            return
        page_content = doc[0].page_content
        
        if page_content:
            parsed_url = urlparse(url)
            path = parsed_url.path
            file_name = re.sub(r'\W+', '_', path.split("/")[-1]) + ".txt"

            output_path = os.path.join(output_folder, file_name)
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as file:
                file.write(page_content)
            
            print(f"File saved to {output_path}")
        else:
            print("No content found to save.")
    except Exception as e:
        print(f"Error when crawl {url}: {e}")

def convert_to_txt(input_file_path, output_folder):
    try:
        text = textract.process(input_file_path)
        
        file_name = os.path.basename(input_file_path)
        file_name_without_extension = os.path.splitext(file_name)[0]
        
        valid_file_name = re.sub(r'\W+', '_', file_name_without_extension) + ".txt"
        
        output_file_path = os.path.join(output_folder, valid_file_name)
        os.makedirs(os.path.dirname(output_file_path), exist_ok=True)

        with open(output_file_path, 'wb') as f:
            f.write(text)
        print(f"File saved to {output_file_path}")
    except Exception as e:
        print(f"Error: {e}")

