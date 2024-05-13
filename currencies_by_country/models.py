from django.db import models
import datetime

class CountryCodes(models.Model):

    country = models.CharField(max_length=255, null=False, verbose_name='Страна')
    currency = models.CharField(max_length=255, null=False, verbose_name='Валюта')
    code = models.CharField(max_length=255, null=False, verbose_name='Код')
    number = models.CharField(max_length=255, null=False, verbose_name='Номер')

    def __str__(self):
        return self.country
    
class CurrencyRates(models.Model):

    usd_currency = models.CharField(max_length=255, verbose_name='Доллар США')
    eur_currency = models.CharField(max_length=255, verbose_name='Евро')
    gpb_currency = models.CharField(max_length=255, verbose_name='Фунт стерлингов')
    ikr_currency = models.CharField(max_length=255, verbose_name='Индийская рупия')
    cny_currency = models.CharField(max_length=255, verbose_name='Китайский юань Жэньминьби')
    try_currency = models.CharField(max_length=255, verbose_name='Турецкая лира')
    jpy_currency = models.CharField(max_length=255, verbose_name='Японская йена')
    date = models.DateField(verbose_name='Дата')

    @classmethod
    def calculate_relative_changes(self, base_date: datetime.date):
        '''
        Takes: Принимает базовую дату, с которой рассчитываются относительные изменения курсов

        Return: None

        Заносит все в таблицу CurrencyRateChange, при отсутствии изменений в строке не создает новую,
        при наличии строки с датой и валютой, как на входе, проверяет, сменилось ли относительная величина,
        и меняет ее если надо, при отсутвии создает такую строку
        '''
        base_rates = CurrencyRates.objects.filter(date=base_date).first()
        if not base_rates:
            return  # Handle the case when base rates are not available
        
        currencies = ['usd_currency', 'eur_currency', 'gpb_currency', 'ikr_currency', 'cny_currency', 'try_currency', 'jpy_currency']
        queryset = self.objects.all()
        for row in queryset:
            
            for currency in currencies:
                defaults = dict()
                base_rate = float(getattr(base_rates, currency).replace(',', '.'))
                current_rate = float(getattr(row, currency).replace(',', '.'))
                relative_change = ((current_rate - base_rate) / base_rate) * 100
                defaults['currency'] = currency
                change_obj, created = CurrencyRateChange.objects.update_or_create(
                    date=row.date,
                    currency=currency,
                    defaults={
                        'relative_change': relative_change,
                    },
                )    
                change_obj.save()

    def __str__(self):
        return str(self.pk)

class CurrencyRateChange(models.Model):
    currency = models.CharField(max_length=255, verbose_name='Валюта')
    date = models.DateField(verbose_name='Дата')
    relative_change = models.FloatField(verbose_name='Относительное изменение (%)')

    def __str__(self):
        return f'{self.currency} - {self.date}'