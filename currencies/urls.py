"""
URL configuration for currencies project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from currencies_by_country.views import GetterCurrencies, MainPageForm

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", GetterCurrencies.redirect_to_main),
    path("main/", MainPageForm.main_form, name='main_form'),
    path("main/coutries-and-rates", GetterCurrencies.get_countries_rates, name="coutries_and_rates"),
    path("api/GET/country-currency/", GetterCurrencies.get_currency_of_country),
    path("api/GET/currency-rates/", GetterCurrencies.get_rates),
]
