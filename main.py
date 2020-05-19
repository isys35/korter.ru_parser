import requests
from bs4 import BeautifulSoup
import sys
from urllib.parse import quote

def save_file(txt: str, file_name: str):
    with open(file_name, 'w', encoding='utf8') as file:
        file.write(txt)


class NewBuildingsData:
    MAIN_PAGE = 'https://korter.ru/'
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:76.0) Gecko/20100101 Firefox/76.0'
    }

    def get_cities_urls(self):
        resp = requests.get(self.MAIN_PAGE, headers=self.HEADERS)
        if resp.status_code != 200:
            print(resp)
            sys.exit()
        soup = BeautifulSoup(resp.text, 'lxml')
        city_urls = [self.MAIN_PAGE + quote(city_block['href'][1:]) for city_block in soup.select('.SeoLink__StyledWrapper-sc-7zimy-0')
                     if 'новостройки' in city_block['href']]
        return city_urls



def main():
    parser = NewBuildingsData()
    parser.get_cities_urls()


if __name__ == '__main__':
    main()