import base64
import datetime
from io import BytesIO
from django.http import Http404, JsonResponse
from django.views.generic import TemplateView
from django.shortcuts import redirect, render
from bs4 import BeautifulSoup
from matplotlib.dates import DayLocator
import pytz
import requests
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

# https://www.finmarket.ru/currency/rates/?id=10148&pv=1&cur=52170&bd=1&bm=2&by=2022&ed=1&em=2&ey=2024&x=48&y=13#archive Евро
# https://www.finmarket.ru/currency/rates/?id=10148&pv=1&cur=52148&bd=1&bm=2&by=2022&ed=1&em=2&ey=2024&x=56&y=10#archive Доллар

class DateValidation:
    tz = pytz.timezone('Europe/Moscow')

    def check_day(self, day):
        
        if day < 1 or day > 31:
            raise Http404("Day should be between 1 and 31")
        return day

    def check_month(self, month):
        
        if month < 1 or month > 12:
            raise Http404("Month should be between 1 and 12")
        return month

    def check_year(self, year):
        
        current_year = datetime.datetime.now(self.tz).date().year
        if year < 1 or year > current_year:
            raise Http404("Year should be a positive number not greater than the current year")
        return year
    
    def check_all_date(self, day, month, year):
        try:
            date = datetime.date(year, month, day)
        except ValueError:
            raise Http404("Incorrect data")
        if date > datetime.datetime.now(self.tz).date():
            raise Http404("Input date greater then now date")
        
    def check_interval(self, day_start, month_start, year_start,
                       day_end, month_end, year_end):
        
        start_date = datetime.date(year_start, month_start, day_start)
        end_date = datetime.date(year_end, month_end, day_end)

        if (end_date - start_date).days > 2 * 365:
            raise Http404("Interval must be <= 2 years")
        elif (end_date - start_date).days < 0:
            raise Http404("End date must be >= start date")

class GetterCurrencies:

    
    def redirect_to_main(request):
        return redirect("main/")
    

    def get_currency_of_country(request) -> pd.DataFrame:
        response = requests.get(
            'https://www.iban.ru/currency-codes',
        )

        soup = BeautifulSoup(response.content, "html.parser", from_encoding='utf-8')

        head = list(
            map(lambda x: x.text, 
                soup.find('table').find('thead').find_all('th'))
            )

        currency_of_country = soup.find('table').find('tbody').find_all('tr')
        currency_of_country = list(
            map(lambda x: x.find_all('td'), 
                currency_of_country)
            )

        dict_country_currency = {column: list(
            map(
                lambda x: x[head.index(column)].text, 
                currency_of_country
                )
            ) for column in head}

        df = pd.DataFrame(dict_country_currency).sort_values('Страна', ignore_index=True)
        df = df[df['Код'] != '']
        dict_country_currency = df.to_dict()

        return JsonResponse(dict_country_currency)
    
    def get_rates(request):
        
        bd = int(request.GET.get('bd'))
        bm = int(request.GET.get('bm'))
        by = int(request.GET.get('by'))

        ed = int(request.GET.get('ed'))
        em = int(request.GET.get('em'))
        ey = int(request.GET.get('ey'))

        response = requests.get(
            'https://www.finmarket.ru/currency/rates/?id=10148&pv=1#archive',
        )

        soup = BeautifulSoup(response.content, "html.parser", from_encoding='utf-8')

        currency_codes = soup.find('select', 
                                {'name': 'cur'}).find_all('option')

        currency_url_codes = dict(
            map(
                (lambda x: (x.text, x['value'])), 
                currency_codes
                )
            )

        target_currencies = {'доллар сша', 
                            'евро', 
                            'фунт стерлингов', 
                            'японская йена', 
                            'турецкая лира', 
                            'индийская рупия', 
                            'китайский юань жэньминьби',
                            }

        course_to_rub = dict()
        for currency in currency_url_codes:

            if currency.lower() not in target_currencies:
                continue

            response = requests.get(
                f'https://www.finmarket.ru/currency/rates/?id=10148&pv=1&cur={currency_url_codes[currency]}&bd={bd}&bm={bm}&by={by}&ed={ed}&em={em}&ey={ey}#archive',
            )

            #получим html-страницу страницы сайта
            soup = BeautifulSoup(response.content, "html.parser", from_encoding='utf-8')

            head = soup.find("thead").find_all('th')
            head = list(map(lambda x: x.text, head))

            course_data = dict()
            course_data['EUR'] = dict()

            # current_course = soup.find_all("tr")
            current_course = list(
                map(
                    lambda x: x.find_all('td'), 
                    soup.find("table", {'class': 'karramba'}).find('tbody').find_all("tr")
                    )
                )
            
            date = list(map(lambda x: x[head.index('Дата')].text, current_course))
            
            current_course = list(map(lambda x: x[head.index('Курс')].text, current_course))

            course_to_rub[currency] = current_course

        course_to_rub["Дата"] = date

        df = pd.DataFrame(course_to_rub)

        df.to_excel('result.xlsx')

        return JsonResponse(course_to_rub)
    

    def get_countries_rates(request):

        date_validator = DateValidation()

        bd = date_validator.check_day(int(request.POST.get('bd')))
        bm = date_validator.check_month(int(request.POST.get('bm')))
        by = date_validator.check_year(int(request.POST.get('by')))
        date_validator.check_all_date(bd, bm, by)

        ed = date_validator.check_day(int(request.POST.get('ed')))
        em = date_validator.check_month(int(request.POST.get('em')))
        ey = date_validator.check_year(int(request.POST.get('ey')))
        date_validator.check_all_date(ed, em, ey)

        date_validator.check_interval(bd, bm, by,
                                      ed, em, ey)
        print(bd, bm, by, ed, em, ey)

        selected_countries = request.POST.getlist('countries')
        # Теперь selected_countries содержит список выбранных стран

        country_currencies = requests.get("http://127.0.0.1:8000/api/GET/country-currency/")
        json_content_countries = country_currencies.json()
        df_contries_currency = pd.DataFrame(json_content_countries)
        df_contries_currency = df_contries_currency[
            df_contries_currency["Страна"].isin(selected_countries)
            ]
        print(df_contries_currency)
        
        rates_currencies_to_rub = requests.get(f"http://127.0.0.1:8000/api/GET/currency-rates/?bd={bd}&bm={bm}&by={by}&ed={ed}&em={em}&ey={ey}")
        json_content_rates = rates_currencies_to_rub.json()
        df_rates_currency = pd.DataFrame(json_content_rates)
        # print([[df_rates_currency[currency_name[currency]]] for currency in df_contries_currency['Код']])

        print(df_rates_currency)

        # Создадим подграфики для каждой страны
        fig, ax = plt.subplots(figsize=(10, 6))

        trans_codes = {
            'EUR': 'ЕВРО',
            'USD': 'Доллар США',
            'JPY': 'Японская йена',
            'GBP': 'Фунт стерлингов',
            'CNY': 'Китайский юань Жэньминьби',
            'TRY': 'Турецкая лира',
            'INR': 'Индийская рупия',
        }
        not_exists = []
        # Проходим по выбранным странам
        for country in selected_countries:
            # Получаем код валюты из первого датафрейма
            currency_code = df_contries_currency[(df_contries_currency['Страна'] == country) & (df_contries_currency['Код'].isin(trans_codes))]['Код'].values
            
            if not currency_code:
                not_exists.append(country)
                continue

            currency_code = currency_code[0]
            print(currency_code[0])
            
            # Фильтруем данные из второго датафрейма по коду валюты
            filtered_data = df_rates_currency[['Дата', trans_codes[currency_code]]].copy()
            
            # Преобразуем значения в числовой тип (заменяем запятые на точки и преобразуем в float)
            filtered_data[trans_codes[currency_code]] = filtered_data[trans_codes[currency_code]].str.replace(',', '.').astype(float)
            
            # Рассчитываем относительные изменения курса валюты
            filtered_data['Относительное изменение'] = filtered_data[trans_codes[currency_code]].pct_change() * 100
            
            # Строим график для каждой страны
            ax.plot(filtered_data['Дата'], filtered_data['Относительное изменение'], label=country)
        print(filtered_data)
        # Добавляем подписи к осям и заголовок
        ax.set_xlabel('Дата')
        ax.set_ylabel('Относительное изменение курса (%)')
        ax.set_title('Относительные изменения курсов валют')
        ax.legend()

        # Поворачиваем даты на оси x для лучшей читаемости
        plt.xticks(rotation=90)
        ax.xaxis.set_major_locator(DayLocator(interval=10)) 
        # Сохраняем график в формате JPG
        plt.tight_layout()
        plt.grid(visible=True)

        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        buffer.close()
        
        return render(request, 'graph.html', {'image_graph': image_base64,
                                              'not_exists': not_exists})    

class MainPageForm(TemplateView):

    template_name = 'main_form.html'

    def main_form(request):

        country_currencies = requests.get("http://127.0.0.1:8000/api/GET/country-currency/")
        json_content_countries = country_currencies.json()
        df_contries_currency = pd.DataFrame(json_content_countries)
        all_countries = df_contries_currency['Страна'].to_list()

        return render(request, 
                      'main_form.html', 
                      context={'countries': all_countries})