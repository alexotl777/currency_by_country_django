from django.db import models

# Create your models here.

class CountryCodes(models.Model):

    country = models.CharField(max_length=255, null=False, verbose_name='Страна')
    currency = models.CharField(max_length=255, null=False, verbose_name='Валюта')
    code = models.CharField(max_length=255, null=False, verbose_name='Код')
    number = models.CharField(max_length=255, null=False, verbose_name='Номер')

    def __str__(self):
        return self.country
    
class CurrencyRates(models.Model):

    usd_currency = models.CharField(max_length=255, null=False, verbose_name='Доллар США')
    eur_currency = models.CharField(max_length=255, null=False, verbose_name='Евро')
    gpb_currency = models.CharField(max_length=255, null=False, verbose_name='Фунт стерлингов')
    ikr_currency = models.CharField(max_length=255, null=False, verbose_name='Индийская рупия')
    cny_currency = models.CharField(max_length=255, null=False, verbose_name='Китайский юань Жэньминьби')
    try_currency = models.CharField(max_length=255, null=False, verbose_name='Турецкая лира')
    jpy_currency = models.CharField(max_length=255, null=False, verbose_name='Японская йена')
    date = models.DateField(null=False, verbose_name='Дата')

    

    def __str__(self):
        return self.pk

class CurrencyRateChange(models.Model):
    currency = models.ForeignKey(CountryCodes, on_delete=models.CASCADE, verbose_name='Валюта')
    date = models.DateField(null=False, verbose_name='Дата')
    relative_change = models.FloatField(verbose_name='Относительное изменение (%)')

    def __str__(self):
        return f'{self.currency} - {self.date}'