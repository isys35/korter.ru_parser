import requests
from bs4 import BeautifulSoup
import sys
from urllib.parse import quote, unquote
import re
import xlwt, xlrd
import time
import os


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
    EXCEL_FILE_NAME = 'data.xls'
    IMG_CATALOG = 'img'

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
            layout = self.parsing_layout(resp_layout.text)
            layout['url'] = url
            layouts.append(layout)
        return layouts

    @staticmethod
    def parsing_layout(resp_text):
        soup = BeautifulSoup(resp_text, 'lxml')
        layout_page_info = {}
        for element in soup.select('.KeyValue__StyledKeyValue-gwnrbl-0.bKluVn'):
            layout_page_info[element.select('div')[0].text] = element.select('div')[1].text
        image_block = soup.select_one('.gallery__StyledMainImage-sc-7sqsts-5')
        if not image_block:
            save_file(resp_text,'eror_imag.html')
        img_src = 'https:' + image_block['src']
        price = soup.select_one('.mainInfo__StyledPrice-sc-1k2gfo5-6.hIhsZO')
        try:
            area = float(layout_page_info['Площадь'].replace(' м2', ''))
        except ValueError:
            area = None
        layout = {'img_src': img_src, 'layout_name': layout_page_info['Планировка'],
                  'residential_complex': layout_page_info['Жилой комплекс'],
                  'area': area}
        if price:
            price_search = re.findall('\d+', price.text)
            price = int(''.join(price_search))
            layout['price'] = price
        print(layout)
        return layout

    def save_layouts(self, layouts):
        try:
            rb = xlrd.open_workbook(self.EXCEL_FILE_NAME)
        except FileNotFoundError:
            self.create_xls_file()
            rb = xlrd.open_workbook(self.EXCEL_FILE_NAME)
        wb = xlwt.Workbook()
        ws = wb.add_sheet('sheet')
        sheet = rb.sheet_by_index(0)
        rows = sheet.nrows
        for rownum in range(rows):
            row = sheet.row_values(rownum)
            for colnum in range(len(row)):
                ws.write(rownum, colnum, row[colnum])
        for layout in layouts:
            ws.write(rows + layouts.index(layout), 0, unquote(layout['url']))
            ws.write(rows + layouts.index(layout), 1, layout['layout_name'])
            ws.write(rows + layouts.index(layout), 2, layout['area'])
            if 'price' in layout:
                ws.write(rows + layouts.index(layout), 3, layout['price'])
            self.save_image(layout)
        wb.save(self.EXCEL_FILE_NAME)

    def save_image(self, layout):
        resp = requests.get(layout['img_src'], self.HEADERS)
        try:
            if layout['residential_complex'].replace('/', '_') not in os.listdir(path=self.IMG_CATALOG):
                os.mkdir(f"{self.IMG_CATALOG}/{layout['residential_complex'].replace('/','_')}")
            image_name = re.search(r'/(\d+.\w+)', layout['img_src']).group(1)
            with open(f"{self.IMG_CATALOG}/{layout['residential_complex'].replace('/', '_')}/{image_name}",
                      'wb') as out:
                out.write(resp.content)
        except OSError:
            if 'fasfdas' not in os.listdir(path=self.IMG_CATALOG):
                os.mkdir(f"{self.IMG_CATALOG}/{'fasfdas'}")
            image_name = re.search(r'/(\d+.\w+)', layout['img_src']).group(1)
            with open(f"{self.IMG_CATALOG}/{'fasfdas'}/{image_name}",
                      'wb') as out:
                out.write(resp.content)

    def create_xls_file(self):
        wb = xlwt.Workbook()
        ws = wb.add_sheet('sheet')
        ws.write(0, 0, 'url')
        ws.write(0, 1, 'планировка')
        ws.write(0, 2, 'площадь, м2')
        ws.write(0, 3, 'цена, руб')
        wb.save(self.EXCEL_FILE_NAME)
        for i in range(0, 4):
            ws.col(i).width = 6000


def main():
    parser = NewBuildingsData()
    try:
        cities = eval(load_file('cities'))
    except FileNotFoundError:
        cities = parser.get_cities_urls()
        save_file(str(cities), 'cities')
    try:
        new_buildings_urls = eval(load_file('new_buildings_urls'))
    except FileNotFoundError:
        new_buildings_urls = []
        for city in cities:
            print(city)
            new_buildings_urls.extend(parser.get_newbuildings_urls(city))
        save_file(str(new_buildings_urls), 'new_buildings_urls')
    try:
        parsed_url = eval(load_file('parsed_url'))
    except FileNotFoundError:
        parsed_url = []
    for new_building_url in new_buildings_urls:
        if new_building_url in parsed_url:
            continue
        print(new_building_url)
        layouts = parser.get_building_layouts(new_building_url)
        parser.save_layouts(layouts)
        parsed_url.append(new_building_url)
        save_file(str(parsed_url), 'parsed_url')


if __name__ == '__main__':
    main()