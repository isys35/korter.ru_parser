import requests
from bs4 import BeautifulSoup
import sys
from urllib.parse import quote
import re


def save_file(txt: str, file_name: str):
    with open(file_name, 'w', encoding='utf8') as file:
        file.write(txt)


def load_file(file_name: str):
    with open(file_name, 'r', encoding='utf8') as file:
        return file.read()


class NewBuildingsData:
    MAIN_PAGE = 'https://korter.ru/'
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:76.0) Gecko/20100101 Firefox/76.0'
    }

    def get_cities_urls(self):
        resp = requests.get(self.MAIN_PAGE, headers=self.HEADERS)
        soup = BeautifulSoup(resp.text, 'lxml')
        city_urls = [self.MAIN_PAGE + quote(city_block['href'][1:]) for city_block in soup.select('.SeoLink__StyledWrapper-sc-7zimy-0')
                     if 'новостройки' in city_block['href']]
        return city_urls

    def get_newbuildings_urls(self, url_city):
        resp = requests.get(url_city,headers=self.HEADERS)
        newbuildings_urls = self.parsing_newbuildings_urls(resp.text)
        max_page = self.get_max_page(resp.text)
        page = 1
        if max_page:
            while page != max_page:
                page += 1
                resp_page = requests.get(url_city + f'?page={page}', headers=self.HEADERS)
                max_page = self.get_max_page(resp_page.text)
                newbuildings_urls.extend(self.parsing_newbuildings_urls(resp_page.text))
        return newbuildings_urls

    def get_max_page(self, resp_text):
        soup = BeautifulSoup(resp_text, 'lxml')
        max_page = soup.select('.Pagination__StyledPaginationButton-fz9lk2-0')[-2].text
        return int(max_page)

    def parsing_newbuildings_urls(self, resp_text):
        soup = BeautifulSoup(resp_text, 'lxml')
        url_blocks = soup.select('.Link__StyledLink-sc-1qa6dyr-0.jPkwaa.buildingCard__StyledAction-sc-1t8cw05-9.esqEyb')
        new_buildings_urls = [self.MAIN_PAGE + quote(new_building['href'][1:]) for new_building in url_blocks]
        return new_buildings_urls

    def get_building_layouts(self, new_building_url):
        url = new_building_url + quote('/планировки')
        resp = requests.get(url, headers=self.HEADERS)
        soup = BeautifulSoup(resp.text, 'lxml')
        layouts_urls = [self.MAIN_PAGE + quote(layout['href'].replace(self.MAIN_PAGE,'')) for layout in soup.select('.LayoutCard__StyledImage-sc-1j6xc9t-0.bOLFEI')]
        layouts = []
        for layout_url in layouts_urls:
            resp_layout = requests.get(layout_url, headers=self.HEADERS)
            layouts.append(self.parsing_layout(resp_layout.text))

        return layouts

    @staticmethod
    def parsing_layout(resp_text):
        soup = BeautifulSoup(resp_text, 'lxml')
        layout_page_info = {}
        for element in soup.select('.KeyValue__StyledKeyValue-gwnrbl-0.bKluVn'):
            layout_page_info[element.select('div')[0].text] = element.select('div')[1].text
        img_src = 'https:' + soup.select_one('.gallery__StyledMainImage-sc-7sqsts-5.hWNlQd')['src']
        price = soup.select_one('.mainInfo__StyledPrice-sc-1k2gfo5-6.hIhsZO')
        layout = {'img_src': img_src, 'layout_name': layout_page_info['Планировка'],
                  'residential_complex': layout_page_info['Жилой комплекс'],
                  'area': float(layout_page_info['Площадь'].replace(' м2', ''))}
        if price:
            price_search = re.findall('\d+', price.text)
            price = int(''.join(price_search))
            layout['price'] = price
        return layout


def main():
    parser = NewBuildingsData()
    cities = parser.get_cities_urls()
    new_buildings_urls = []
    for city in cities:
        print(city)
        new_buildings_urls.extend(parser.get_newbuildings_urls(city))
    print(len(new_buildings_urls))
    layouts = []
    for new_building_url in new_buildings_urls:
        layouts.extend(parser.get_building_layouts(new_building_url))


if __name__ == '__main__':
    # main()
    parser = NewBuildingsData()
    parser.get_building_layouts('https://korter.ru/%D0%B6%D0%BA-nova-park-%D0%B5%D0%BA%D0%B0%D1%82%D0%B5%D1%80%D0%B8%D0%BD%D0%B1%D1%83%D1%80%D0%B3')