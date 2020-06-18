import requests
from bs4 import BeautifulSoup
import sys
from urllib.parse import quote, unquote
import re
import xlwt, xlrd
import time
import os
from parsing_base import Parser


def save_file(txt: str, file_name: str):
    with open(file_name, 'w', encoding='utf8') as file:
        file.write(txt)


def load_file(file_name: str):
    try:
        with open(file_name, 'r', encoding='utf8') as file:
            return file.read()
    except FileNotFoundError:
        return '[]'


class NewBuildingsData(Parser):
    MAIN_PAGE = 'https://korter.ru/'
    EXCEL_FILE_NAME = 'data.xls'
    IMG_CATALOG = 'img'

    def get_cities_urls(self):
        resp = self.request.get(self.MAIN_PAGE)
        soup = BeautifulSoup(resp.text, 'lxml')
        city_urls = [self.MAIN_PAGE + quote(city_block['href'][1:]) for city_block in soup.select('.SeoLink__StyledWrapper-sc-7zimy-0')
                     if 'новостройки' in city_block['href']]
        return city_urls

    def get_newbuildings_urls(self, url_city_list):
        print('[INFO] Получение ссылок на новостройки в городах')
        start_time = time.time()
        resps = self.requests.get(url_city_list)
        newbuildings_city = {}
        for index_resp in range(len(resps)):
            city = unquote(url_city_list[index_resp]).split('/')[-1]
            max_page = self.get_max_page(resps[index_resp])
            pages_url = [url_city_list[index_resp]]
            page = 1
            if max_page:
                while page != max_page:
                    while page != max_page:
                        page += 1
                        page_url = url_city_list[index_resp] + f'?page={page}'
                        pages_url.append(page_url)
                    resp_page = self.request.get(pages_url[-1])
                    max_page = self.get_max_page(resp_page.text)
            resps_all_pages = self.requests.get(pages_url)
            newbuildings_urls = []
            for resp in resps_all_pages:
                newbuildings_urls.extend(self.parsing_newbuildings_urls(resp))
            newbuildings_city[city] = newbuildings_urls
        print('{} секунд'.format(time.time()-start_time))
        return newbuildings_city

    def get_max_page(self, resp_text):
        soup = BeautifulSoup(resp_text, 'lxml')
        max_page = soup.select('.Pagination__StyledPaginationButton-fz9lk2-0')[-2].text
        return int(max_page)

    def parsing_newbuildings_urls(self, resp_text):
        soup = BeautifulSoup(resp_text, 'lxml')
        url_blocks = soup.select('.Link__StyledLink-sc-1qa6dyr-0.jPkwaa.buildingCard__StyledAction-sc-1t8cw05-9.esqEyb')
        new_buildings_urls = [self.MAIN_PAGE + quote(new_building['href'][1:]) for new_building in url_blocks]
        return new_buildings_urls

    def get_building_layouts(self, new_building_urls):
        urls = [new_building_url + quote('/планировки') for new_building_url in new_building_urls]
        newbildings_name = [unquote(new_building_url).split('/')[-1] for new_building_url in new_building_urls]
        resps = self.requests.get(urls)
        layouts = []
        for resp_index in range(len(resps)):
            soup = BeautifulSoup(resps[resp_index], 'lxml')
            layouts_urls = [self.MAIN_PAGE + quote(layout['href'].replace(self.MAIN_PAGE,'')) for layout in soup.select('.LayoutCard__StyledImage-sc-1j6xc9t-0.bOLFEI')]
            resps_layout = self.requests.get(layouts_urls)
            for resp_layout_index in range(len(resps_layout)):
                layout = self.parsing_layout(resps_layout[resp_layout_index])
                if not layout:
                    resp_layout = self.request.get(layouts_urls[resp_layout_index])
                    layout = self.parsing_layout(resp_layout.text)
                if not layout:
                    continue
                layout['url'] = urls[resp_index]
                layout['residential_complex'] = newbildings_name[resp_index]
                print(layout)
                layouts.append(layout)
        return layouts

    def parsing_layout(self, resp_text):
        soup = BeautifulSoup(resp_text, 'lxml')
        layout_page_info = {}
        for element in soup.select('.KeyValue__StyledKeyValue-gwnrbl-0.bKluVn'):
            layout_page_info[element.select('div')[0].text] = element.select('div')[1].text
        image_block = soup.select_one('.SwipableGallery__StyledImage-q9ee6z-4')
        if not image_block:
            save_file(resp_text, 'eror_imag.html')
            return None
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
        return layout

    def save_layouts(self, layouts, city):
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
            self._save_image(layout, city)
        wb.save(self.EXCEL_FILE_NAME)

    def _save_image(self, layout, city):
        try:
            os.listdir(path=self.IMG_CATALOG)
        except FileNotFoundError:
            os.mkdir(self.IMG_CATALOG)
        if city not in os.listdir(path=self.IMG_CATALOG):
            os.mkdir(f"{self.IMG_CATALOG}/{city}")
        if layout['residential_complex'] not in os.listdir(path=f"{self.IMG_CATALOG}/{city}"):
            os.mkdir(f"{self.IMG_CATALOG}/{city}/{layout['residential_complex']}")
        if layout['layout_name'] not in os.listdir(path=f"{self.IMG_CATALOG}/{city}/{layout['residential_complex']}"):
            os.mkdir(f"{self.IMG_CATALOG}/{city}/{layout['residential_complex']}/{layout['layout_name']}")
        image_name = re.search(r'/(\d+.\w+)', layout['img_src']).group(1)
        file_name = f"{self.IMG_CATALOG}/{city}/{layout['residential_complex']}/{layout['layout_name']}/{image_name}"
        print(file_name)
        self.save_image(layout['img_src'], file_name)

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
    cities = parser.get_cities_urls()
    cities.reverse()
    new_buildings_urls = parser.get_newbuildings_urls(cities)
    for city in new_buildings_urls:
        parsed_cities = eval(load_file('cities'))
        if city in parsed_cities:
            continue
        print(city)
        layouts = parser.get_building_layouts(new_buildings_urls[city])
        parser.save_layouts(layouts, city)
        parsed_cities.append(city)
        save_file(str(parsed_cities), 'cities')



if __name__ == '__main__':
    main()