import requests
import sys
import os
import asyncio, aiohttp
from urllib.parse import unquote, quote
import httplib2

class Parser:
    def __init__(self):
        self.request = Request()
        self.requests = Requests()
        self.html_files_catlog_name = 'html_files'

    def save_html(self, txt, file_name):
        if self.html_files_catlog_name not in os.listdir():
            os.mkdir('html_files')
        with open(f'{self.html_files_catlog_name}/{file_name}', 'w', encoding='utf8') as file:
            file.write(txt)

    def save_image(self, url, image_name):
        h = httplib2.Http('.cache')
        response, content = h.request(url)
        with open(f"{image_name}", 'wb') as out:
            out.write(content)


class Request:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:74.0) Gecko/20100101 Firefox/74.0'
        }

    def get(self, url, headers=None):
        if headers is None:
            response = requests.get(url, headers=self.headers)
        else:
            response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response
        elif response.status_code == 403:
            return None
        else:
            print(url)
            print(response.status_code)
            sys.exit()


class Requests(Request):
    def __init__(self):
        super().__init__()

    def get(self, urls, headers=None):
        if headers is None:
            headers = [self.headers for _ in range(len(urls))]
        data = asyncio.run(req(urls, headers))
        return data


async def fetch_content(url, session, headers):
    async with session.get(url, headers=headers) as response:
        data = await response.text()
        return data


async def req(urls, headers):
    tasks = []
    async with aiohttp.ClientSession() as session:
        for i in range(0, len(urls)):
            task = asyncio.create_task(fetch_content(urls[i], session, headers[i]))
            tasks.append(task)
        data = await asyncio.gather(*tasks)
        return data


if __name__ == '__main__':
    parser = Parser()
    pages = parser.requests.get(['https://www.oddsportal.com', 'https://www.oddsportal.com/soccer/africa/africa-cup-of-nations-u17/nigeria-guinea-phI9AlJb/'])
    parser.save_html(pages[0], '1.html')
    parser.save_html(pages[1], '2.html')
