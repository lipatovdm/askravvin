from app import app
import requests
from flask import request
from bs4 import BeautifulSoup as bs
import json
import logging
from flask import render_template

logger = logging.getLogger(__name__)

@app.route('/')
@app.route('/index')
def index():
	json = {"msg": "hello world"}
	return render_template('index.html', json=json)

@app.route('/api/fetch')
def fetch_game():
	region = request.args.get('region')
	currency = request.args.get('currency')
	platform = request.args.get('platform').upper()
	query = request.args.get('q')
	user_price = float(request.args.get('price'))

	s = requests.Session()
	s.headers.update({
	'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:45.0) Gecko/20100101 Firefox/45.0'
	})

	user_input = 'Need For Speed'
	url = 'https://psprices.com/region-{region}/search/?q={query}&platform={platform}'.format(region=region,query=query, platform=platform)

	def get_currency_rate(val_from, val_to, amount):
		curr_url = 'http://www.xe.com/currencyconverter/convert/?Amount=%s&From=%s&To=%s' % (amount, val_from, val_to)
		r = requests.get(curr_url)
		data = r.text
		soup = bs(data)
		return float(soup.find('span', class_='uccResultAmount').text.replace(',', ''))

	def load_data(url, session):
		conn = True
		while conn:
			try:
				r = session.get(url, timeout=5)
				conn = False
			except requests.exceptions.ReadTimeout:
				print('FUCK')
		return r.text

	def check_discount(item):
		return item.find('span', class_='old') != None


	queryset_text = load_data(url, s)

	data = bs(queryset_text)

	def fetch_search_results(data):
		results = []
		for game_card in data.find_all('div', class_="content__game_card", limit=5):
			item_currency = 'RUB'
			new_currency = currency.upper()
			discount = check_discount(game_card)
			game_item = {}
			game_item['metadata'] = {}
			game_item['price'] = {}
			game_item['price']['current_price'] = {}
			game_item['price']['discount_price'] = {}
			game_item['price']['converted_price'] = {}
			game_item['price']['profit_price'] = {}
			
			game_item_img = game_card.find('img').get('data-original')
			game_item_title = game_card.find('span', class_='content__game_card__title').text
			# META DATA OF GAME
			game_item['metadata']['title'] = game_item_title
			game_item['metadata']['platform'] = platform
			game_item['metadata']['id'] = game_item_img.split('/')[5]
			game_item['metadata']['img'] = game_item_img
			game_item['metadata']['discount'] = discount
			# META END
			
			#PRICE DATA OF GAME
			#CURRENT PRICE
			game_item['price']['current_price']['amount'] = float(game_card.find('span', class_='content__game_card__price').get('content').split(',')[0])
			game_item['price']['current_price']['currency'] = item_currency

			#CONVERTED PRICE
			game_item['price']['converted_price']['amount'] = round(get_currency_rate(item_currency, new_currency, game_item['price']['current_price']['amount']),0)
			game_item['price']['converted_price']['currency'] = new_currency

			#PROFIT PRICE
			game_item['price']['profit_price']['amount'] = round(game_item['price']['converted_price']['amount'] - user_price,0)
			game_item['price']['profit_price']['currency'] = new_currency

			#DISCOUNT
			if discount:
				game_item['price']['discount_price']['old_amount'] = round(float(game_card.find('span', class_='old').text.split(' ')[0]),2)
				game_item['price']['discount_price']['currency'] = item_currency
			
            #PRICE END
			results.append(game_item)
		return results

	def convert_price(price_input, out_currency, rate_list, src_currency=None,):
		return price_input * rate_list[out_currency]
	# print(data)
	return(json.dumps(fetch_search_results(data), ensure_ascii=False).encode('utf-8'))
