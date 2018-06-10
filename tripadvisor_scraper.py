#!/usr/bin/env python
from datetime import datetime
from time import time
from lxml import html,etree
import requests,re
import os,sys
import unicodecsv as csv
import argparse
from lxml import html
import requests
from collections import OrderedDict
import json
import argparse
import re


def parse_hotel_url(url):
    print("Fetching %s" % url)
    response = requests.get(url)
    parser = html.fromstring(response.text)

    XPATH_RATING = '//div[@data-name="ta_rating"]'
    XPATH_NAME = '//h1[@id="HEADING"]//text()'
    XPATH_HOTEL_RATING = '//span[@property="ratingValue"]//@content'
    XPATH_REVIEWS = '//a[contains(@class,"Reviews")]//text()'
    XPATH_RANK = '//span[contains(@class,"popularity")]//text()'
    XPATH_STREET_ADDRESS = "//span[@class='street-address']//text()"
    XPATH_LOCALITY = '//div[contains(@class,"address")]//span[@class="locality"]//text()'
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
    raw_zipcode = parser.xpath(XPATH_ZIP)
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
    country = raw_country[0].strip() if raw_country else None
    review_count = re.findall(r'\d+(?:,\d+)?', ''.join(raw_review_count).strip())[0].replace(",",
                                                                                             "") if raw_review_count else None
    hotel_rating = ''.join(raw_rating).strip() if raw_rating else None
    official_description = ' '.join(' '.join(raw_official_description).split()) if raw_official_description else None
    cleaned_highlights = filter(lambda x: x != '\n', raw_highlights)

    if raw_address_json:
        try:
            parsed_address_info = json.loads(raw_address_json[0])
            zipcode = parsed_address_info["address"].get("postalCode")
            country = parsed_address_info["address"].get("addressCountry", {}).get("name")
        except Exception as e:
            raise e

    highlights = ','.join(cleaned_highlights).replace('\n', '')
    # Ordereddict is for preserve the site order
    ratings_dict = OrderedDict()
    for rating in ratings:
        # xpath rating
        XPATH_RATING_KEY = ".//label[contains(@class,'row_label')]//text()"
        XPATH_RATING_VALUE = ".//span[contains(@class,'row_num')]//text()"

        # take data from xpath
        raw_rating_key = rating.xpath(XPATH_RATING_KEY)
        raw_rating_value = rating.xpath(XPATH_RATING_VALUE)

        # cleaning data
        cleaned_rating_key = ''.join(raw_rating_key)
        cleaned_rating_value = ''.join(raw_rating_value).replace(",", "") if raw_rating_value else 0
        ratings_dict.update({cleaned_rating_key: int(cleaned_rating_value)})

    amenity_dict = OrderedDict()
    for amenity in amenities:
        XPATH_AMENITY_KEY = './/div[contains(@class,"sub_title")]//text()'
        XPATH_AMENITY_VALUE = './/div[@class="sub_content"]//text()'

        raw_amenity_key = amenity.xpath(XPATH_AMENITY_KEY)
        raw_amenity_value = amenity.xpath(XPATH_AMENITY_VALUE)
        if raw_amenity_key and raw_amenity_value:
            amenity_key = ''.join(raw_amenity_key)
            amenity_value = ' ,'.join(raw_amenity_value)
            amenity_dict.update({amenity_key: amenity_value})

    additional_info_dict = OrderedDict()
    for info in raw_additional_info:
        XPATH_INFO_TEXT = "./text()"
        if info.xpath(XPATH_INFO_TEXT):
            XPATH_INFO_KEY = ".//text()"
            XPATH_INFO_VALUE = "./following-sibling::div[1]//text()"

            raw_info_key = info.xpath(XPATH_INFO_KEY)
            raw_info_value = info.xpath(XPATH_INFO_VALUE)
            if raw_info_value and raw_info_key:
                # cleaning
                raw_info_value = ''.join(raw_info_value).replace("#", ", #").lstrip(", ")
                if raw_info_key[0] == "Hotel class":
                    continue
                additional_info_dict.update({raw_info_key[0]: raw_info_value})

    # hotels official details is now rendering from this endpoint
    raw_hotel_id = re.findall("-d(.*)-Reviews", url)
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
        hotel_details_response = requests.post(hotel_details_url, headers=hotels_details_request_headers,
                                               data=hotel_details_formadata).text
        hotel_details_parser = html.fromstring(hotel_details_response)
        raw_official_description = hotel_details_parser.xpath("//div[@class='section_content']//text()")
        official_description = ''.join(raw_official_description)

    address = {
        'street_address': street_address,
        'locality': locality,
        'zipcode': zipcode,
        'country': country
    }

    data = {
        'address': address,
        'ratings': ratings_dict,
        'amenities': amenity_dict,
        'official_description': official_description,
        'additional_info': additional_info_dict,
        'rating': float(hotel_rating) if hotel_rating else 0.0,
        'review_count': int(review_count) if review_count else 0,
        'name': name,
        'rank': rank,
        'highlights': highlights,
        'hotel_url': response.url,
    }

    return data


def parse(locality,checkin_date,checkout_date,sort):
    checkIn = checkin_date.strftime("%Y/%m/%d")
    checkOut = checkout_date.strftime("%Y/%m/%d")
    print("Scraper Inititated for Locality:{}".format(locality))
    # TA rendering the autocomplete list using this API
    print("Finding search result page URL")
    geo_url = 'https://www.tripadvisor.com/TypeAheadJson?action=API&startTime='+str(int(time()))+'&uiOrigin=GEOSCOPE&source=GEOSCOPE&interleaved=true&types=geo,theme_park&neighborhood_geos=true&link_type=hotel&details=true&max=12&injectNeighborhoods=true&query='+locality
    api_response  = requests.get(geo_url, verify=False).json()
    #getting the TA url for th equery from the autocomplete response
    url_from_autocomplete = "http://www.tripadvisor.com"+api_response['results'][0]['url']
    print('URL found {}'.format(url_from_autocomplete))
    geo = api_response['results'][0]['value']   
    #Formating date for writing to file 
    
    date = checkin_date.strftime("%Y_%m_%d")+"_"+checkout_date.strftime("%Y_%m_%d")
    #form data to get the hotels list from TA for the selected date
    form_data = {'changeSet': 'TRAVEL_INFO',
            'showSnippets': 'false',
            'staydates':date,
            'uguests': '2',
            'sortOrder':sort
    }
    #Referrer is necessary to get the correct response from TA if not provided they will redirect to home page
    headers = {
                            'Accept': 'text/javascript, text/html, application/xml, text/xml, */*',
                            'Accept-Encoding': 'gzip,deflate',
                            'Accept-Language': 'en-US,en;q=0.5',
                            'Cache-Control': 'no-cache',
                            'Connection': 'keep-alive',
                            'Content-Type': 'application/x-www-form-urlencoded; charset=utf-8',
                            'Host': 'www.tripadvisor.com',
                            'Pragma': 'no-cache',
                            'Referer': url_from_autocomplete,
                            'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:28.0) Gecko/20100101 Firefox/28.0',
                            'X-Requested-With': 'XMLHttpRequest'
                        }
    cookies=  {"SetCurrency":"USD"}
    print("Downloading search results page")
    page_response  = requests.post(url = url_from_autocomplete,data=form_data,headers = headers, cookies = cookies, verify=False)
    print("Parsing results ")
    parser = html.fromstring(page_response.text)
    hotel_lists = parser.xpath('//div[contains(@class,"listItem")]//div[contains(@class,"listing collapsed")]')
    hotel_data = []
    if not hotel_lists:
        hotel_lists = parser.xpath('//div[contains(@class,"listItem")]//div[@class="listing "]')

    for hotel in hotel_lists:
        XPATH_HOTEL_LINK = './/a[contains(@class,"property_title")]/@href'
        XPATH_REVIEWS  = './/a[@class="review_count"]//text()'
        XPATH_RANK = './/div[@class="popRanking"]//text()'
        XPATH_RATING = './/span[contains(@class,"rating")]/@alt'
        XPATH_HOTEL_NAME = './/a[contains(@class,"property_title")]//text()'
        XPATH_HOTEL_FEATURES = './/div[contains(@class,"common_hotel_icons_list")]//li//text()'
        XPATH_HOTEL_PRICE = './/div[contains(@data-sizegroup,"mini-meta-price")]/text()'
        XPATH_VIEW_DEALS = './/div[contains(@data-ajax-preserve,"viewDeals")]//text()' 
        XPATH_BOOKING_PROVIDER = './/div[contains(@data-sizegroup,"mini-meta-provider")]//text()'

        raw_booking_provider = hotel.xpath(XPATH_BOOKING_PROVIDER)
        raw_no_of_deals =  hotel.xpath(XPATH_VIEW_DEALS)
        raw_hotel_link = hotel.xpath(XPATH_HOTEL_LINK)
        raw_no_of_reviews = hotel.xpath(XPATH_REVIEWS)
        raw_rank = hotel.xpath(XPATH_RANK)
        raw_rating = hotel.xpath(XPATH_RATING)
        raw_hotel_name = hotel.xpath(XPATH_HOTEL_NAME)
        raw_hotel_features = hotel.xpath(XPATH_HOTEL_FEATURES)
        raw_hotel_price_per_night  = hotel.xpath(XPATH_HOTEL_PRICE)

        try:
            url = 'http://www.tripadvisor.com'+raw_hotel_link[0] if raw_hotel_link else  None
            reviews = ''.join(raw_no_of_reviews).replace("reviews","").replace(",","") if raw_no_of_reviews else 0
            rank = ''.join(raw_rank) if raw_rank else None
            rating = ''.join(raw_rating).replace('of 5 bubbles','').strip() if raw_rating else None
            name = ''.join(raw_hotel_name).strip() if raw_hotel_name else None
            hotel_features = ','.join(raw_hotel_features)
            #price_per_night = ''.join(raw_hotel_price_per_night).encode('utf-8').replace('\n','') if raw_hotel_price_per_night else None
            price_per_night = ''.join(raw_hotel_price_per_night).replace('\n',
                                                                        '') if raw_hotel_price_per_night else None
            no_of_deals = re.findall("all\s+?(\d+)\s+?",''.join(raw_no_of_deals))
            booking_provider = ''.join(raw_booking_provider).strip() if raw_booking_provider else None

            # get other meta data !!!! AC
            if url is not None:
                print('calling the detailed hotel parser')
                more_details = parse_hotel_url(url)
                rank = more_details['rank']
                rank_num = rank.split('#')[1].split(' ')[0] # split on # get 2nd term, then the 1st digit
                ratings_5 = more_details['ratings']['Excellent']
                ratings_4 = more_details['ratings']['Very good']
                ratings_3 = more_details['ratings']['Average']
                ratings_2 = more_details['ratings']['Poor']
                ratings_1 = more_details['ratings']['Terrible']
                #import pdb;pdb.set_trace()

        except:
            import pdb; pdb.set_trace()




        if no_of_deals:
            no_of_deals = no_of_deals[0]
        else:
            no_of_deals = 0
        #import pdb; pdb.set_trace()

        data = {
                    'hotel_name':name,

                    'locality':locality,
                    'reviews':reviews,
                    'tripadvisor_rating':rating,
                    'rank':rank,
                     'rank_num':rank_num,
                     '5_excellent':ratings_5,
            '4_excellent': ratings_4,
            '3_very_good': ratings_3,
            '2_poor': ratings_2,
            '1_terrible': ratings_1,
                    'checkOut':checkOut,
                    'checkIn':checkIn,
                    'hotel_features':hotel_features,
                    'price_per_night':price_per_night,
                    'no_of_deals':no_of_deals,
                    'booking_provider':booking_provider,
            'url': url

        }
        hotel_data.append(data)
    return hotel_data

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('checkin_date',help = 'Hotel Check In Date (Format: YYYY/MM/DD')
    parser.add_argument('checkout_date',help = 'Hotel Chek Out Date (Format: YYYY/MM/DD)')
    sortorder_help = """
    available sort orders are :\n
    priceLow - hotels with lowest price,
    distLow : Hotels located near to the search center,
    recommended: highest rated hotels based on traveler reviews,
    popularity :Most popular hotels as chosen by Tipadvisor users 
    """
    parser.add_argument('sort',help = sortorder_help,default ='popularity ')
    parser.add_argument('locality',help = 'Search Locality')
    args = parser.parse_args()
    locality = args.locality
    checkin_date = datetime.strptime(args.checkin_date,"%Y/%m/%d")
    checkout_date = datetime.strptime(args.checkout_date,"%Y/%m/%d")
    sort= args.sort
    checkIn = checkin_date.strftime("%Y/%m/%d")
    checkOut = checkout_date.strftime("%Y/%m/%d")
    today = datetime.now()
   
    if today<datetime.strptime(checkIn,"%Y/%m/%d") and datetime.strptime(checkIn,"%Y/%m/%d")<datetime.strptime(checkOut,"%Y/%m/%d"):

        try:
            data = parse(locality,checkin_date,checkout_date,sort)
        except:
            import pdb; pdb.set_trace()

        print("Writing to output file tripadvisor_data.csv")

        checkIn = checkin_date.strftime("%Y%m%d")
        checkOut = checkout_date.strftime("%Y%m%d")

        with open('tripadvisor_data_{}_{}_{}.csv'.format(locality,
                                                         checkIn,
                                                         checkOut),'wb') as csvfile: # AC switched w to wb
            fieldnames = ['hotel_name','url','locality','reviews','tripadvisor_rating',
                          'rank','rank_num',
                          '5_excellent',
                                        '4_excellent',
            '3_very_good',
            '2_poor',
            '1_terrible',
                          'checkIn','checkOut','price_per_night','booking_provider','no_of_deals','hotel_features']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in  data:
                writer.writerow(row)
    #checking whether the entered date is already passed
    elif today>datetime.strptime(checkIn,"%Y/%m/%d") or today>datetime.strptime(checkOut,"%Y/%m/%d"):
        print("Invalid Checkin date: Please enter a valid checkin and "
              "checkout dates,entered date is already passed")
    
    elif datetime.strptime(checkIn,"%Y/%m/%d")>datetime.strptime(checkOut,"%Y/%m/%d"):
        print("Invalid Checkin date: CheckIn date must be less than checkOut date")