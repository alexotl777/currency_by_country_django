import base64
from io import BytesIO
import datetime
import pytz
from django.http import Http404, JsonResponse
from django.views.generic import TemplateView
from django.shortcuts import redirect, render

from currencies.settings import ALLOWED_HOSTS
from .models import CountryCodes, CurrencyRates, CurrencyRateChange
from bs4 import BeautifulSoup
import requests
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.dates import DayLocator
import matplotlib
matplotlib.use('Agg')

class DateValidation:
    tz = pytz.timezone('Europe/Moscow')

    def check_day(self, day: int) -> int:
        '''
        Takes: целочисленный день
        
        Returns: целочисленный день, если он между 1 и 31, иначе вызывает ошибку
        '''
        if day < 1 or day > 31:
            raise Http404("Day should be between 1 and 31")
        return day

    def check_month(self, month: int) -> int:
        '''
        Takes: целочисленный месяц
        
        Returns: целочисленный месяц, если он между 1 и 12, иначе вызывает ошибку
        '''
        if month < 1 or month > 12:
            raise Http404("Month should be between 1 and 12")
        return month

    def check_year(self, year: int) -> int:
        '''
        Takes: целочисленный месяц
        
        Returns: целочисленный месяц, если он между 1 и 12, иначе вызывает ошибку
        '''
        current_year = datetime.datetime.now(self.tz).date().year
        if year < 1 or year > current_year:
            raise Http404("Year should be a positive number not greater than the current year")
        return year
    
    def check_all_date(self, day: int, month: int, year: int):
        '''
        Takes: целочисленный день, месяц, год
        
        Returns: None

        Проверяет дату на ее существование и больше ли она текущей даты, 
        иначе возвращает ошибку
        '''
        try:
            date = datetime.date(year, month, day)
        except ValueError:
            raise Http404("Incorrect data")
        if date > datetime.datetime.now(self.tz).date():
            raise Http404("Input date greater then now date")
        
    def check_interval(self, day_start: int, month_start: int, year_start: int,
                       day_end: int, month_end: int, year_end: int):
        '''
        Takes: целочисленный день, месяц, год дат начала и конца интервала
        
        Returns: None

        Проверяет, находится ли интервал от 0 до 2 лет, 
        иначе возвращает ошибку
        '''
        start_date = datetime.date(year_start, month_start, day_start)
        end_date = datetime.date(year_end, month_end, day_end)

        if (end_date - start_date).days > 2 * 365:
            raise Http404("Interval must be <= 2 years")
        elif (end_date - start_date).days < 0:
            raise Http404("End date must be >= start date")

class GetterCurrencies:

    
    def redirect_to_main(request):
        '''
        Перенаправляет с базового роута на главную страницу с формой
        '''
        return redirect("main/")
    

    def get_currency_of_country(request) -> pd.DataFrame:
        '''
        Собирает с iban.ru информацию о кодах валют стран 
        и синхранизирует их в БД в таблице CountryCodes
        '''
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

        try:
            for id, row in df.iterrows():
                codes_obj, created = CountryCodes.objects.update_or_create(
                    country=row['Страна'],
                    defaults={
                        'currency': row['Валюта'],
                        'code': row['Код'],
                        'number': row['Номер'],
                    }
                )
                codes_obj.save()

        except BaseException as e:
            print(f'Ошибка [get_currency_of_country] - {e}')

        return JsonResponse(dict_country_currency)
    
    def get_rates(request):
        '''
        Собирает с finmarket.ru информацию о курсах валют 
        и синхранизирует их в БД в таблице CountryCodes
        '''
        
        bd = int(request.GET.get('bd'))
        bm = int(request.GET.get('bm'))
        by = int(request.GET.get('by'))

        ed = int(request.GET.get('ed'))
        em = int(request.GET.get('em'))
        ey = int(request.GET.get('ey'))

        response = requests.get(
            'https://www.finmarket.ru/currency/rates/?id=10148&pv=1#archive',
        )

        soup = BeautifulSoup(response.content, 
                             "html.parser", 
                             from_encoding='utf-8')

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

        # Преобразуем столбец даты в формат даты и времени
        df['Дата'] = pd.to_datetime(df['Дата'], format='%d.%m.%Y')

        # Форматируем столбец даты в формат YYYY-MM-DD
        df['Дата'] = df['Дата'].dt.strftime('%Y-%m-%d')

        # Сохранение полученных данных в базу данных
        try:
            for id, row in df.iterrows():
                rates_obj, created = CurrencyRates.objects.update_or_create(
                    date=row['Дата'],
                    defaults={
                        'usd_currency': row['Доллар США'],
                        'eur_currency': row['ЕВРО'],
                        'gpb_currency': row['Фунт стерлингов'],
                        'ikr_currency': row['Индийская рупия'],
                        'cny_currency': row['Китайский юань Жэньминьби'],
                        'try_currency': row['Турецкая лира'],
                        'jpy_currency': row['Японская йена'],
                    }
                )
                rates_obj.save()

            # Определение базовой даты
            base_date = datetime.datetime.strptime(df['Дата'][0], '%Y-%m-%d').date()

            # Вычисление относительных изменений
            CurrencyRates.calculate_relative_changes(base_date=base_date)
        except BaseException as e:
            print(f'Ошибка [get_rates] - {e}')

        return JsonResponse(course_to_rub)
    

    def get_countries_rates(request):
        '''
        Запрашивает коды и курсы валют, расчитывает относительные изменения курсов
        за определенный период с определенным списком стран и строит по этому график
        '''
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

        selected_countries = request.POST.getlist('countries')
        # selected_countries содержит список выбранных стран

        country_currencies = requests.get(f"http://{ALLOWED_HOSTS[0]}:8000/api/GET/country-currency/")
        json_content_countries = country_currencies.json()
        df_contries_currency = pd.DataFrame(json_content_countries)
        df_contries_currency = df_contries_currency[
            df_contries_currency["Страна"].isin(selected_countries)
            ]
        
        rates_currencies_to_rub = requests.get(f"http://{ALLOWED_HOSTS[0]}:8000/api/GET/currency-rates/?bd={bd}&bm={bm}&by={by}&ed={ed}&em={em}&ey={ey}")
        json_content_rates = rates_currencies_to_rub.json()
        df_rates_currency = pd.DataFrame(json_content_rates)

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
            
            # Фильтруем данные из второго датафрейма по коду валюты
            filtered_data = df_rates_currency[['Дата', trans_codes[currency_code]]].copy()
            
            # Преобразуем значения в числовой тип (заменяем запятые на точки и преобразуем в float)
            filtered_data[trans_codes[currency_code]] = filtered_data[trans_codes[currency_code]].str.replace(',', '.').astype(float)
            
            # Рассчитываем относительные изменения курса валюты
            filtered_data['Относительное изменение'] = filtered_data[trans_codes[currency_code]].pct_change() * 100
            
            # Строим график для каждой страны
            ax.plot(filtered_data['Дата'], filtered_data['Относительное изменение'], label=country)

        # Добавляем подписи к осям и заголовок
        ax.set_xlabel('Дата')
        ax.set_ylabel('Относительное изменение курса (%)')
        ax.set_title('Относительные изменения курсов валют')
        ax.legend()

        # Поворачиваем даты на оси x для лучшей читаемости
        plt.xticks(rotation=90)
        ax.xaxis.set_major_locator(DayLocator(interval=10)) 

        # Сохраняем график 
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
        '''
        Определяет форму, которая принимает страны и интервал дат, а зате отправляет запрос на get_countries_rates
        '''
        country_currencies = requests.get(f"http://{ALLOWED_HOSTS[0]}:8000/api/GET/country-currency/")
        json_content_countries = country_currencies.json()
        df_contries_currency = pd.DataFrame(json_content_countries)
        all_countries = df_contries_currency['Страна'].to_list()

        return render(request, 
                      'main_form.html', 
                      context={'countries': all_countries})
    