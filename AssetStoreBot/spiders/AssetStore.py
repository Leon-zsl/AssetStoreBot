# -*- coding: utf-8 -*-

import os.path
import logging
import scrapy
import json
from scrapy.selector import Selector
from AssetStoreBot import items

class AssetstoreSpider(scrapy.Spider):
	name = 'AssetStore'
	allowed_domains = ['assetstore.unity.com']
	asset_store_url = 'https://assetstore.unity.com/publishers/%d'
	publishers_start = 1
	publishers_end = 100000
	default_next_page = 2
	default_page_size = 24
	pages = {}

	def start_requests(self):
		for i in range(AssetstoreSpider.publishers_start, AssetstoreSpider.publishers_end):
			yield scrapy.http.Request(AssetstoreSpider.asset_store_url % i, callback=self.parse_html)


	def parse_html(self, response):
		table = response.selector.css('div[data-reactid="418"] > div')
		for item in table:
			uris = item.css('._1ClTv::attr(href)').extract()
			uri = uris[0] if len(uris ) > 0 else ''

			categorys = item.css('._2kcTW::text').extract()
			category = categorys[0] if len(categorys) > 0 else ''

			publishers = item.css('.q2zeR::text').extract()
			publisher = publishers[0] if len(publishers) > 0 else ''
			
			names = item.css('._1EyLb::text').extract()
			name = names[0] if len(names) > 0 else ''
			
			prices = item.css('._223RA::text').extract()
			price = prices[0] if len(prices) > 0 else 'FREE'
			if price == 'FREE':
				price = float(0.00)
			else:
				price = float(price.strip('$').strip())
				
			rating_counts = item.css('.NoXio::text').extract()
			rating_count = rating_counts[0] if len(rating_counts) > 0 else ''
			rating_count = rating_count.strip('(').strip(')').strip()
			try:
				rating_count = int(rating_count)
			except Exception:
				rating_count = 0

			rating_score = len(item.css('.ifont-star'))

			yield self.gen_item(name,
								uri,
								price,
								rating_score,
								rating_count,
								publisher,
								category)

		next = response.selector.css('button[label="Next"]')
		if next:
			yield self.gen_graphql_req(response.url.split('/')[-1],
									AssetstoreSpider.default_next_page,
									AssetstoreSpider.default_page_size)


	def parse_json(self, response):
		if len(response.body) == 0:
			return

		data = json.loads(response.body)[0]
		if 'error' in data:
			logging.error("error found: %s,%s", response.url, data['error'])
			return
		if not 'data' in data:
			logging.warning("not data in response: %s", response.url)
			return
		if not 'publisher' in data['data']:
			logging.warning("not publisher in response: %s", response.url)
			return
		if not 'packages' in data['data']['publisher']:
			logging.warning("not packages in response: %s", response.url)
			return
		if not 'results' in data['data']['publisher']['packages']:
			logging.warning("not results in response: %s", response.url)
			return
		results = data['data']['publisher']['packages']['results']
		if not results or len(results) == 0:
			logging.warning("results is empty in response: %s", response.url)
			return

		for item in results:
			name = item['name']
			slug = item['slug']
			origin_price = item['originalPrice']
			price = float(origin_price['originalPrice'])
			rating = item['rating']
			rating_count = rating['count']
			rating_score = rating['average']
			publisher = item['publisher']
			publisher_name = publisher['name']
			category = item['category']
			category_name = category['longName'].replace('/', ' > ')
			category_slug = category['slug']
			uri = os.path.join('packages', category_slug, slug)
			yield self.gen_item(name,
								uri,
								price,
								rating_score,
								rating_count,
								publisher_name,
								category_name)

		page_index = response.meta['page_index']
		page_size = response.meta['page_size']
		publisher_id = response.meta['publisher_id']
		if len(results) == page_size:
			yield self.gen_graphql_req(publisher_id, page_index + 1, page_size)


	def gen_graphql_req(self, publisher_id, page_index, page_size):
		body = [{
				'operationName': 'Publisher',
				'variables': {
					'id': publisher_id,
					'page': page_index,
					'size': page_size,
					'orderBy': 'popularity',
					'rating': 0,
					'released': 0,
					'plusPro': False,
					'price': '0-4000',
				},
				'query': r"""query Publisher {
  publisher(id: $id) {
	id
	organizationId
	name
	packages(page: $page, size: $size, sort_by: $orderBy, price: $price, rating: $rating, released: $released, plusPro: $plusPro) {
	  total
	  results {
		...product
	  }
	}
  }
}

fragment product on Product {
  id
  productId
  itemId
  slug
  name
  rating {
	average
	count
  }
  currentVersion {
	id
	name
	publishedDate
  }
  reviewCount
  downloadSize
  assetCount
  publisher {
	id
	name
	url
  }
  originalPrice {
	itemId
	originalPrice
	finalPrice
	isFree
	discount {
	  save
	  percentage
	  type
	  saleType
	}
	currency
	entitlementType
  }
  category {
	id
	name
	slug
	longName
  }
  firstPublishedDate
  supportedUnityVersions
  popularTags {
	id
	pTagId
	name
  }
  plusProSale
}
""",
			}]

		meta = {'publisher_id':publisher_id, 'page_index':page_index, 'page_size':page_size}
		headers = {
		  'authority': 'assetstore.unity.com',
		  'origin': 'https://assetstore.unity.com',
		  'referer': 'https://assetstore.unity.com/',
		  'x-requested-with': 'XMLHttpRequest',
		  'content-type': 'application/json;charset=UTF-8',
		}
		req = scrapy.Request(url='https://assetstore.unity.com/api/graphql/batch',
							callback=self.parse_json,
							method='POST',
							headers=headers,
							body=json.dumps(body),
							meta=meta)
		return req


	def gen_item(self, name, uri, price, rating_score, rating_count, publisher, category):
		item = items.AssetstorebotItem()
		item['name'] = name
		item['uri'] = uri
		item['price'] = price
		item['rating_score'] = rating_score
		item['rating_count'] = rating_count
		item['publisher'] = publisher
		item['category'] = category
		return item
