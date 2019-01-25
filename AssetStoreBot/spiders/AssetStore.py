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
	publishers_end = 2
	pages = {}
	def start_requests(self):
		for i in range(AssetstoreSpider.publishers_start, AssetstoreSpider.publishers_end):
			yield scrapy.http.Request(AssetstoreSpider.asset_store_url % i, callback=self.parse_html)


	def parse_html(self, response):
		table = response.selector.css('div[data-reactid="418"] > div')
		for item in table:
			uri = item.css('._1ClTv::attr(href)').extract()[0]
			category = item.css('._2kcTW::text').extract()[0]
			publisher = item.css('.q2zeR::text').extract()[0]
			name = item.css('._1EyLb::text').extract()[0]
			price = item.css('._223RA::text').extract()[0]
			if price == 'FREE':
				price = float(0.00)
			else:
				price = float(price.strip('$'))
			rating_count = item.css('.NoXio::text').extract()[0]
			rating_count = rating_count.strip('(').strip(')')
			try:
				rating_count = int(rating_count)
			except Exception:
				rating_count = 0
			rating_score = len(item.css('.ifont-star'))

			yield self.gen_item(name, uri, price, rating_score, rating_count, publisher, category)

		next = response.selector.css('button[label="Next"]')
		if next:
			yield self.gen_graphql_req(response.url.split('/')[-1], 2, 24)


	def parse_json(self, response):
		if not response.body or len(response.body) == 0:
			return

		data = json.loads(response.body)
		print type(response.body), type(data)

		if not 'data' in data[0]:
			return
		if not 'publisher' in data[0]['data']:
			return
		if not 'packages' in data[0]['data']['publisher']:
			return
		if not 'results' in data[0]['data']['publisher']['packages']:
			return
		results = data[0]['data']['publisher']['packages']['results']
		if not results or len(results) == 0:
			return

		page_index = response.meta['page_index']
		page_size = response.meta['page_size']
		publisher_id = response.meta['publisher_id']
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
			yield self.gen_item(name, uri, price, rating_score, rating_count, publisher_name, category_name)

		if len(results) == page_size:
			yield self.gen_graphql_req(publisher_id, page_index+1, page_size)


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
	publisherProfileId
	organizationId
	name
	description
	website
	keyImages {
	  type
	  imageUrl
	  __typename
	}
	supportUrl
	supportEmail
	shortUrl
	gaAccount
	gaPrefix
	lists(page: 1, size: 20) {
	  total
	  results {
		...list
		packages(size: 6) {
		  total
		  results {
			...product
			__typename
		  }
		  __typename
		}
		__typename
	  }
	  __typename
	}
	packages(page: $page, size: $size, sort_by: $orderBy, price: $price, rating: $rating, released: $released, plusPro: $plusPro) {
	  total
	  results {
		...product
		__typename
	  }
	  __typename
	}
	__typename
  }
}

fragment list on List {
  id
  type
  listId
  slug
  name
  description
  ownerId
  ownerType
  status
  headerImage
  __typename
}

fragment product on Product {
  id
  productId
  itemId
  slug
  name
  description
  rating {
	average
	count
	__typename
  }
  currentVersion {
	id
	name
	publishedDate
	__typename
  }
  reviewCount
  downloadSize
  assetCount
  publisher {
	id
	name
	url
	supportUrl
	supportEmail
	gaAccount
	gaPrefix
	__typename
  }
  mainImage {
	big
	facebook
	small
	icon
	icon75
	__typename
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
	  __typename
	}
	currency
	entitlementType
	__typename
  }
  images {
	type
	imageUrl
	thumbnailUrl
	__typename
  }
  category {
	id
	name
	slug
	longName
	__typename
  }
  firstPublishedDate
  publishNotes
  supportedUnityVersions
  state
  overlay
  overlayText
  popularTags {
	id
	pTagId
	name
	__typename
  }
  plusProSale
  __typename
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
		# logging.info("gen item:%s", item)
		print 'gen item:', item
		return item
