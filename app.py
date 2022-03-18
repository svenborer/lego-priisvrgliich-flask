#!/usr/bin/env python3.6
from statistics import mean
import os
import re
from flask import Flask
from flask import request
from flask import jsonify
from flask_caching import Cache
from helper import get_availability_score

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

from models import Subscription, SubscriptionTheme

wl_set_number = _config['scanner']['wishlist']['set_number']
wl_theme = _config['scanner']['wishlist']['theme']
wl_subtheme = _config['scanner']['wishlist']['subtheme']

@app.route("/lego-priisvrgliich/")
def index():
    provider_deals_tmp = q.get_provider_deals()
    provider_deals = []
    for deal in provider_deals_tmp:
        deal = dict(deal)
        deal.update({'availability' : get_availability_score(deal['availability'])})
        provider_deals.append(deal)
    return render_template('index.html', provider_deals=provider_deals)

@app.route("/lego-priisvrgliich/provider/<provider>")
def provider(provider):
    provider_deals_tmp = [_ for _ in q.get_provider_deals() if _['provider'] == provider]
    provider_deals = []
    for deal in provider_deals_tmp:
        deal = dict(deal)
        deal.update({'availability' : get_availability_score(deal['availability'])})
        provider_deals.append(deal)
    return render_template('index.html', provider_deals=provider_deals)

@app.route("/lego-priisvrgliich/diefflieger")
def diefflieger():
    provider_deals_tmp = [_ for _ in q.get_provider_deals() if _['price_change_l7d'] != 0]
    provider_deals_tmp = sorted(provider_deals_tmp, key = lambda i: i['price_change_l7d'])
    provider_deals = []
    for deal in provider_deals_tmp:
        deal = dict(deal)
        deal.update({'availability' : get_availability_score(deal['availability'])})
        provider_deals.append(deal)
    return render_template('index.html', provider_deals=provider_deals)

@app.route("/lego-priisvrgliich/eol")
def eol():
    provider_deals_tmp = [_ for _ in q.get_provider_deals() if _['is_eol']]
    provider_deals = []
    for deal in provider_deals_tmp:
        deal = dict(deal)
        deal.update({'availability' : get_availability_score(deal['availability'])})
        provider_deals.append(deal)
    return render_template('index.html', provider_deals=provider_deals)

@app.route("/lego-priisvrgliich/set/<set_number>")
def set_information(set_number):
    if re.match(r'[0-9]{4,7}', str(set_number)):
        set_informations = q.get_set_information(set_number)
        if set_informations:
            offers_tmp = q.get_latest_offers(set_number)
            offers = []
            for offer in offers_tmp:
                offer = dict(offer)
                offer.update({'availability' : get_availability_score(offer['availability'])})
                offers.append(offer)
            return render_template(
                'set.html', 
                set_information=set_informations,
                title="{0} {1}".format(set_number, set_informations[0]['name']),
                set_number=set_number,
                offers=offers
            )
    return render_template('404.html'), 404

@app.route("/lego-priisvrgliich/price_chart/<set_number>")
def price_chart(set_number):
    if re.match(r'[0-9]{4,7}', str(set_number)):
        sql_prices_temp = "SELECT MIN(price) AS price, provider, DATE_FORMAT(scan_date, '%%Y-%%m-%%d') AS timestamp FROM tbl_provider_scans WHERE set_number = %s GROUP BY provider, timestamp"
        sql_prices_temp_data = q._execute_query(sql_prices_temp, (set_number, ))
        prices = {}
        dates = []
        set_information = q.get_set_information(set_number)
        uvp=set_information[0]['ch_price'] if set_information[0]['ch_price'] else False
        blv=set_information[0]['qty_avg_price'] if set_information[0]['qty_avg_price'] else False
        if sql_prices_temp_data:
            providers = list(dict.fromkeys([_['provider'] for _ in sql_prices_temp_data]))
            tmp_dates = list(dict.fromkeys([_['timestamp'] for _ in sql_prices_temp_data]))
            min_date = datetime.strptime(min(tmp_dates), '%Y-%m-%d')
            max_date = datetime.strptime(max(tmp_dates), '%Y-%m-%d')
            while min_date <= max_date:
                dates.append(min_date.strftime('%Y-%m-%d'))
                min_date = min_date + timedelta(days=+1)
            colorIndex = 0
            for provider in providers:
                prices[provider] = {}
                prices[provider]['color'] = _config['colors'][colorIndex]
                prices[provider]['prices'] = []
                price_timestamp = [(d['price'], d['timestamp']) for d in sql_prices_temp_data if d['provider'] == provider]
                for date in dates:
                    p = [t[0] for t in price_timestamp if t[1] == date]
                    price = p[0] if p else "null"
                    prices[provider]['prices'].append(price)
                colorIndex = colorIndex + 2
        return render_template(
            'price_chart.html', 
            prices=prices,
            dates=dates,
            uvp=uvp,
            blv=blv
        )
    return render_template('404.html'), 404

@app.route("/lego-priisvrgliich/bl_price_chart/<set_number>")
def bl_price_chart(set_number):
    if re.match(r'[0-9]{4,7}', str(set_number)):
        sql_prices_temp = "SELECT qty_avg_price, DATE_FORMAT(scan_date, '%%Y-%%m-%%d') AS timestamp FROM tbl_bricklink_prices WHERE set_number = %s AND product_condition = 'new' AND qty_avg_price > 0"
        sql_prices_temp_data = q._execute_query(sql_prices_temp, (set_number, ))
        prices = {}
        dates = []
        if sql_prices_temp_data:
            tmp_dates = [_['timestamp'] for _ in sql_prices_temp_data]
            min_date = datetime.strptime(min(tmp_dates), '%Y-%m-%d')
            max_date = datetime.strptime(max(tmp_dates), '%Y-%m-%d')
            while min_date <= max_date:
                dates.append(min_date.strftime('%Y-%m-%d'))
                min_date = min_date + timedelta(days=+1)
            price_timestamp = [(d['qty_avg_price'], d['timestamp']) for d in sql_prices_temp_data]
            for date in dates:
                p = [t[0] for t in price_timestamp if t[1] == date]
                price = p[0] if p else "null"
                prices[date] = price
        return render_template(
            'bl_price_chart.html', 
            prices=prices
        )
    return render_template('404.html'), 404

@app.route("/lego-priisvrgliich/new_listings")
def new_listings():
    new_listings = []
    new_listings_tmp = q.get_new_listings()
    for listing in new_listings_tmp:
        listing = dict(listing)
        listing.update({'availability' : get_availability_score(listing['availability'])})
        new_listings.append(listing)
    return render_template(
        'new_listings.html', 
        new_listings=new_listings
    )

@app.route("/lego-priisvrgliich/auction_deals")
def auction_deals():
    auction_deals = q.get_auction_deals()
    auction_deals = [d for d in auction_deals if (str(d['set_number']) in wl_set_number or d['subtheme'] in wl_subtheme or d['theme'] in wl_theme) and d['save_in_percentage'] > -10 and not any(x in d['title'] for x in _config['scanner']['title_blacklist'])]
    buy_now_deals = q.get_buy_now_deals()
    buy_now_deals = [d for d in buy_now_deals if (str(d['set_number']) in wl_set_number or d['subtheme'] in wl_subtheme or d['theme'] in wl_theme) and d['save_in_percentage'] > -10 and not any(x in d['title'] for x in _config['scanner']['title_blacklist'])]
    return render_template(
        'auction_deals.html', 
        auction_deals=auction_deals,
        buy_now_deals=buy_now_deals
    )

@app.route("/lego-priisvrgliich/set_statistics")
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
def scan_statistics():
    scan_data = q.get_scans_by_date(age=14)
    providers = list(dict.fromkeys([_['provider'] for _ in scan_data]))
    data = {}
    for provider in providers:
        data[provider] = []
        for i in reversed(range(1, 14)):
            date = (datetime.now() + timedelta(days=-i)).strftime('%Y-%m-%d')
            count_data = [d['count'] for d in scan_data if d['provider'] == provider and d['date'].strftime('%Y-%m-%d') == date]
            count = count_data[0] if count_data else 0
            data[provider].append((date, count))
    return render_template(
        'scan_statistics.html', 
        data=data
    )

@app.route("/lego-priisvrgliich/theme/<theme>", defaults={'subtheme': '%'})
@app.route("/lego-priisvrgliich/theme/<theme>/<subtheme>")
def sets_by_theme(theme, subtheme):
    sets = q.get_sets_on_market_unique(theme=theme, subtheme=subtheme)
    all_sets = q.get_sets(theme=theme, subtheme=subtheme)
    if all_sets:
        biggest_set = max([x for x in all_sets if x['pieces']], key=lambda x:x['pieces'])
        cost_per_piece = [(x['ch_price']/x['pieces']) for x in all_sets if x['ch_price'] and x['pieces']]
        cost_per_piece = mean(cost_per_piece) if len(cost_per_piece) > 0 else 0
        birthyear = min(all_sets, key=lambda x:x['year'])['year']
        uvp_to_pieces = [('{} {}'.format(_['set_number'], _['name']), _['pieces'], _['ch_price'], _['current_low_price']) for _ in sets if _['ch_price']]
        return render_template('sets_by_theme.html', subtheme=subtheme, uvp_to_pieces=uvp_to_pieces, sets=sets, eol_sets=all_sets, cost_per_piece=cost_per_piece, biggest_set=biggest_set, birthyear=birthyear)
    return render_template('404.html'), 404

@app.route("/lego-priisvrgliich/search/", methods=['GET'])
def search():
    query = request.args.get('q')
    query_pattern = '%{}%'.format(query)
    provider_deals = q.get_provider_deals(lp_treshold=-999, query_pattern=query_pattern)
    return render_template('index.html', provider_deals=provider_deals, query=query)

@app.route("/lego-priisvrgliich/subscribe/set/<set_number>", methods=['POST', 'GET'])
def subscribe_set_number(set_number):
    if request.method == 'POST':
        email = request.form.get('email')
        price_treshold = request.form.get('price_treshold')
        s = Subscription(set_number = set_number, email = email, price_treshold = price_treshold)
        db.session.add(s)
        db.session.commit()
        return {'data' : {'set_number' : set_number, 'email' : email, 'price_treshold' : price_treshold }}
    return {'error' : 'no_data'}

@app.route("/lego-priisvrgliich/subscribe/theme/<theme>", methods=['POST', 'GET'])
def subscribe_theme(theme):
    if request.method == 'POST':
        email = request.form.get('email')
        save_treshold = request.form.get('save_treshold')
        s = SubscriptionTheme(theme=theme, email=email, save_treshold=save_treshold)
        db.session.add(s)
        db.session.commit()
        return {'email' : email, 'save_treshold' : save_treshold, 'theme' : theme}
    return {'error' : 'no_data'}

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

if __name__ == "__main__":
    app.run(host='127.0.0.1', port=5000, debug=True)
