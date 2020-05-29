#!/usr/bin/env python3.6
import os
import re
from flask import Flask
from flask_caching import Cache

from flask import render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import text
from config import Config, _config

from datetime import datetime, timedelta

app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)
cache = Cache()
cache.init_app(app, config={'CACHE_TYPE': 'simple'})

import queries as q
import models

COLORS = ['#f44336', '#e91e63', '#9c27b0', '#673ab7', '#3f51b5', '#2196f3', '#03a9f4', '#00bcd4', '#009688', '#4caf50', '#8bc34a', '#cddc39', '#ffeb3b', '#ffc107', '#ff9800', '#ff5722', '#795548', '#9e9e9e', '#607d8b']

wl_set_number = _config['scanner']['wishlist']['set_number']
wl_theme = _config['scanner']['wishlist']['theme']
wl_subtheme = _config['scanner']['wishlist']['subtheme']

@app.route("/lego-priisvrgliich/")
@cache.cached(timeout=3600)
def index():
    latests_scans = q._execute_query("SELECT scan_id FROM (SELECT * FROM tbl_provider_scans GROUP BY provider, scan_id ORDER BY scan_date DESC) AS t GROUP BY provider")
    scan_ids = [d['scan_id'] for d in latests_scans]
    provider_deals_tmp = q.get_provider_deals()
    provider_deals = []
    for deal in provider_deals_tmp:
        deal = dict(deal)
        if str(deal['set_number']) in wl_set_number or deal['subtheme'] in wl_subtheme or deal['theme'] in wl_theme:
            deal.update({'is_favorite' : True})
        if str(deal['availability']) in _config['availability']['coming_soon']:
            deal.update({'availability' : 4})
        elif str(deal['availability']) in _config['availability']['available']:
            deal.update({'availability' : 3})
        elif str(deal['availability']) in _config['availability']['limited']:
            deal.update({'availability' : 2})
        elif str(deal['availability']) in _config['availability']['out_of_stock']:
            deal.update({'availability' : 1})
        else:
            deal.update({'availability' : 0})
        provider_deals.append(deal)
    return render_template('index.html', provider_deals=provider_deals)

@app.route("/lego-priisvrgliich/set/<set_number>")
@cache.cached(timeout=10800)
def set_information(set_number):
    if re.match(r'[0-9]{4,7}', str(set_number)):
        set_informations = q.get_set_information(set_number)
        if set_informations:
            bl_price = [b['qty_avg_price'] for b in set_informations if b['set_number'] == set_number]
            bl_price = bl_price[0] if bl_price else None
            list_price = [d['ch_price'] for d in set_informations if d['set_number'] == set_number]
            list_price = list_price[0] if list_price else None
            offers = q.get_latest_offers(set_number)
            sql_prices_temp = "SELECT MIN(price) AS price, provider, DATE_FORMAT(scan_date, '%%Y-%%m-%%d') AS timestamp FROM tbl_provider_scans WHERE set_number = %s GROUP BY provider, timestamp"
            sql_prices_temp_data = q._execute_query(sql_prices_temp, (set_number, ))
            print(sql_prices_temp_data)
            providers = list(dict.fromkeys([row['provider'] for row in sql_prices_temp_data]))
            tmp_dates = list(dict.fromkeys([d['timestamp'] for d in sql_prices_temp_data]))
            min_date = datetime.strptime(min(tmp_dates), '%Y-%m-%d')
            max_date = datetime.strptime(max(tmp_dates), '%Y-%m-%d')
            dates = []
            while min_date <= max_date:
                min_date = min_date + timedelta(days=+1)
                dates.append(min_date.strftime('%Y-%m-%d'))
            colorIndex = 0
            prices = {}
            for provider in providers:
                prices[provider] = {}
                prices[provider]['color'] = COLORS[colorIndex]
                prices[provider]['prices'] = []
                price_timestamp = [(d['price'], d['timestamp']) for d in sql_prices_temp_data if d['provider'] == provider]
                for _ in dates:
                    p = [t[0] for t in price_timestamp if t[1] == d]
                    price = p[0] if p else "null"
                    prices[provider]['prices'].append(price)
                colorIndex = colorIndex + 2
            return render_template(
                'set.html', 
                set_information=set_informations, 
                title=set_number, 
                set_number=set_number, 
                offers=offers, 
                dates=dates, 
                prices=prices, 
                bl_price=bl_price, 
                list_price=list_price
            )
    return render_template('404.html')

@app.route("/lego-priisvrgliich/new_listings")
@cache.cached(timeout=3600)
def new_listings():
    new_listings = []
    new_listings_tmp = q.get_new_listings()
    for listing in new_listings_tmp:
        listing = dict(listing)
        listing.update({'is_favorite' : False})
        if str(listing['set_number']) in wl_set_number or listing['subtheme'] in wl_subtheme or listing['theme'] in wl_theme:
            listing.update({'is_favorite' : True})
        if str(listing['availability']) in _config['availability']['coming_soon']:
            listing.update({'availability' : 4})
        elif str(listing['availability']) in _config['availability']['available']:
            listing.update({'availability' : 3})
        elif str(listing['availability']) in _config['availability']['limited']:
            listing.update({'availability' : 2})
        elif str(listing['availability']) in _config['availability']['out_of_stock']:
            listing.update({'availability' : 1})
        else:
            listing.update({'availability' : 0})
        new_listings.append(listing)
    return render_template(
        'new_listings.html', 
        new_listings=new_listings
    )

@app.route("/lego-priisvrgliich/auction_deals")
@cache.cached(timeout=3600)
def auction_deals():
    auction_deals = q.get_auction_deals()
    auction_deals = [d for d in auction_deals if (str(d['set_number']) in wl_set_number or d['subtheme'] in wl_subtheme or d['theme'] in wl_theme) and d['save_in_percentage'] > -10]
    buy_now_deals = q.get_buy_now_deals()
    buy_now_deals = [d for d in buy_now_deals if (str(d['set_number']) in wl_set_number or d['subtheme'] in wl_subtheme or d['theme'] in wl_theme) and d['save_in_percentage'] > -10]
    return render_template(
        'auction_deals.html', 
        auction_deals=auction_deals,
        buy_now_deals=buy_now_deals
    )

@app.route("/lego-priisvrgliich/set_statistics")
@cache.cached(timeout=3600)
def set_statistics():
    sets_currently_in_market = [s['set_number'] for s in q.get_sets_currently_on_market()]
    data_tmp = q.get_market_statistics_for_sets()
    total = {}
    records = {}
    themes = list(dict.fromkeys([row['theme'] for row in data_tmp]))
    for theme in themes:
        print(theme)
        total[theme] = list(dict.fromkeys([row['subtheme'] for row in data_tmp if row['theme'] == theme]))
        records[theme] = {}
        for subtheme in total[theme]:
            print(subtheme)
            data = []
            sets = [d for d in data_tmp if d['theme'] == theme and d['subtheme'] == subtheme]
            print(sets)
            for s in sets:
                s = dict(s)
                s.update({'is_currently_on_market' : False})
                if s['set_number'] in sets_currently_in_market:
                    s.update({'is_currently_on_market' : True})
                data.append(s)
            records[theme][subtheme] = data
    return render_template(
        'set_statistics.html', 
        records=records
    )

@app.route("/lego-priisvrgliich/scan_statistics")
@cache.cached(timeout=3600)
def scan_statistics():
    providers = [d['provider'] for d in q.get_providers()]
    scan_data = q.get_scans_by_date(age=30)
    data = {}
    for provider in providers:
        data[provider] = []
        for i in reversed(range(1, 30)):
            date = (datetime.now() + timedelta(days=-i)).strftime('%Y-%m-%d')
            count_data = [d['count'] for d in scan_data if d['provider'] == provider and d['date'].strftime('%Y-%m-%d') == date]
            count = count_data[0] if count_data else 0
            data[provider].append((date, count))
    return render_template(
        'scan_statistics.html', 
        data=data
    )

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)