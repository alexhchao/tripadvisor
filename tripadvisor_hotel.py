# -*- coding: utf-8 -*-
from lxml import html
import requests
from collections import OrderedDict
import json
import argparse
import re

def parse(url):
	print ("Fetching %s"%url)
	response = requests.get(url)
	parser = html.fromstring(response.text)
	
	XPATH_RATING = '//div[@data-name="ta_rating"]'
	XPATH_NAME = '//h1[@id="HEADING"]//text()'
	XPATH_HOTEL_RATING = '//span[@property="ratingValue"]//@content'
	XPATH_REVIEWS = '//a[contains(@class,"Reviews")]//text()'
	XPATH_RANK = '//span[contains(@class,"popularity")]//text()'
	XPATH_STREET_ADDRESS = "//span[@class='street-address']//text()"
	XPATH_LOCALITY  = '//div[contains(@class,"address")]//span[@class="locality"]//text()'
	XPATH_ZIP = '//span[@property="v:postal-code"]//text()'
	XPATH_COUNTRY = '//span[@class="country-name"]/@content'
	XPATH_AMENITIES = '//div[contains(text(),"Amenities")]/following-sibling::div[1]//div[@class!="textitem"]' 
	XPATH_HIGHLIGHTS = '//div[contains(@class,"highlightedAmenity")]//text()'
	XPATH_OFFICIAL_DESCRIPTION = '//div[contains(@class,"additional_info")]//span[contains(@class,"tabs_descriptive_text")]//text()'
	XPATH_ADDITIONAL_INFO = '//div[contains(text(),"Details")]/following-sibling::div[@class="section_content"]/div'
	XPATH_FULL_ADDRESS_JSON = '//script[@type="application/ld+json"]//text()'
	
	ratings = parser.xpath(XPATH_RATING)
	raw_name = parser.xpath(XPATH_NAME)
	raw_rank = parser.xpath(XPATH_RANK)
	raw_street_address = parser.xpath(XPATH_STREET_ADDRESS)
	raw_locality = parser.xpath(XPATH_LOCALITY)
	raw_zipcode =  parser.xpath(XPATH_ZIP)
	raw_country = parser.xpath(XPATH_COUNTRY)
	raw_review_count = parser.xpath(XPATH_REVIEWS)
	raw_rating = parser.xpath(XPATH_HOTEL_RATING)
	amenities = parser.xpath(XPATH_AMENITIES)
	raw_highlights = parser.xpath(XPATH_HIGHLIGHTS)
	raw_official_description = parser.xpath(XPATH_OFFICIAL_DESCRIPTION)
	raw_additional_info = parser.xpath(XPATH_ADDITIONAL_INFO)
	raw_address_json = parser.xpath(XPATH_FULL_ADDRESS_JSON)
				
	ratings = ratings[0] if ratings else []
	name = ''.join(raw_name).strip() if raw_name else None
	rank = ''.join(raw_rank).strip() if raw_rank else None
	street_address = raw_street_address[0].strip() if raw_street_address else None
	locality = raw_locality[0].strip() if raw_locality else None
	zipcode = ''.join(raw_zipcode).strip() if raw_zipcode else None
	country  = raw_country[0].strip() if raw_country else None
	review_count = re.findall(r'\d+(?:,\d+)?',''.join(raw_review_count).strip())[0].replace(",","") if raw_review_count else None
	hotel_rating = ''.join(raw_rating).strip() if raw_rating else None
	official_description = ' '.join(' '.join(raw_official_description).split()) if raw_official_description else None
	cleaned_highlights = filter(lambda x:x != '\n', raw_highlights)
	
	if raw_address_json:
		try:
			parsed_address_info = json.loads(raw_address_json[0])
			zipcode = parsed_address_info["address"].get("postalCode")
			country = parsed_address_info["address"].get("addressCountry",{}).get("name")
		except Exception as e:
			raise e
	
	highlights = ','.join(cleaned_highlights).replace('\n','')
	# Ordereddict is for preserve the site order
	ratings_dict = OrderedDict()
	for rating in ratings:

		#xpath rating
		XPATH_RATING_KEY = ".//label[contains(@class,'row_label')]//text()"
		XPATH_RATING_VALUE = ".//span[contains(@class,'row_num')]//text()"

		# take data from xpath
		raw_rating_key = rating.xpath(XPATH_RATING_KEY)
		raw_rating_value = rating.xpath(XPATH_RATING_VALUE)

		# cleaning data
		cleaned_rating_key = ''.join(raw_rating_key)
		cleaned_rating_value = ''.join(raw_rating_value).replace(",","") if raw_rating_value else 0
		ratings_dict.update({cleaned_rating_key:int(cleaned_rating_value)})
	

	amenity_dict = OrderedDict()
	for amenity in amenities:
		XPATH_AMENITY_KEY = './/div[contains(@class,"sub_title")]//text()'
		XPATH_AMENITY_VALUE = './/div[@class="sub_content"]//text()'

		raw_amenity_key = amenity.xpath(XPATH_AMENITY_KEY)
		raw_amenity_value = amenity.xpath(XPATH_AMENITY_VALUE)
		if raw_amenity_key and raw_amenity_value:
			amenity_key = ''.join(raw_amenity_key)
			amenity_value = ' ,'.join(raw_amenity_value)
			amenity_dict.update({amenity_key:amenity_value})

	additional_info_dict = OrderedDict()
	for info in raw_additional_info:
		XPATH_INFO_TEXT = "./text()"
		if info.xpath(XPATH_INFO_TEXT):
			XPATH_INFO_KEY = ".//text()"
			XPATH_INFO_VALUE = "./following-sibling::div[1]//text()"

			raw_info_key = info.xpath(XPATH_INFO_KEY)
			raw_info_value = info.xpath(XPATH_INFO_VALUE)
			if raw_info_value and raw_info_key:
				#cleaning
				raw_info_value = ''.join(raw_info_value).replace("#",", #").lstrip(", ")
				if raw_info_key[0] == "Hotel class":
					continue
				additional_info_dict.update({raw_info_key[0]:raw_info_value})

	#hotels official details is now rendering from this endpoint
	raw_hotel_id = re.findall("-d(.*)-Reviews",url)
	if raw_hotel_id:
		hotels_details_request_headers = {'accept': 'text/html, */*',
		'accept-encoding': 'gzip, deflate, br',
		'accept-language': 'en-GB,en;q=0.9,en-US;q=0.8,ml;q=0.7',
		'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
		'origin': 'https://www.tripadvisor.com',
		'referer': url,
		'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.186 Safari/537.36',
		'x-requested-with': 'XMLHttpRequest'
		}

		hotel_details_formadata = {'haveCsses': 'apg-Hotel_Review-in,responsive_calendars_classic',
			'haveJses': 'earlyRequireDefine,amdearly,global_error,long_lived_global,apg-Hotel_Review,apg-Hotel_Review-in,bootstrap,desktop-rooms-guests-dust-en_IN,responsive-calendar-templates-dust-en_IN,taevents',
			'metaReferer': 'Hotel_Review',
			'needContent': '$prp/resp_hr_about/placement?occur=0',
			'needCsses': '',
			'needDusts': '',
			'needJses': ''
		}

		hotel_details_url = "https://www.tripadvisor.com/DemandLoadAjax"
		hotel_details_response = requests.post(hotel_details_url, headers=hotels_details_request_headers, data=hotel_details_formadata).text
		hotel_details_parser = html.fromstring(hotel_details_response)
		raw_official_description = hotel_details_parser.xpath("//div[@class='section_content']//text()")
		official_description = ''.join(raw_official_description)

	address = {     
					'street_address':street_address,
					'locality':locality,
					'zipcode':zipcode,
					'country':country
	}

	data = {
			'address':address,
			'ratings':ratings_dict,
			'amenities':amenity_dict,
			'official_description':official_description,
			'additional_info':additional_info_dict,
			'rating':float(hotel_rating) if hotel_rating else 0.0,
			'review_count':int(review_count) if review_count else 0,
			'name':name,
			'rank':rank,
			'highlights':highlights,
			'hotel_url':response.url,
			}

	return data

if __name__=='__main__':
	parser = argparse.ArgumentParser()
	parser.add_argument('url',help='Tripadvisor hotel url')
	args = parser.parse_args()
	url = args.url
	scraped_data = parse(url)
	import pdb; pdb.set_trace()

	with open('tripadvisor_hotel_scraped_data.json','w') as f:
		json.dump(scraped_data,f,indent = 4, ensure_ascii=False)