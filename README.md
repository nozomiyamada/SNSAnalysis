# `ScrapeTweet.py`

HOW DOES IT WORK?
  
  Since Twitter is dynamic website (using Ajax, iframe), the ordinary way such as `requests.get(URL)` cannot get its contents. Therefore, it is necessary to open in browser in order to scrape the contents.
  
[selenium](https://pypi.org/project/selenium/) is one of the software(interface) that can manipulate web browser by using programming language. It also enables to access website without opening real browser window (so-called _headless_). The codes here also using selenium in the background.

To use this program, python package [selenium](https://pypi.org/project/selenium/) and [chromedriver](https://chromedriver.chromium.org/) are needed. The version of chromedrive must be compatible with the version of Google Chrome that you use. After you downloaded chromedriver, the binary file must be moved to PATH environment such as `usr/local/bin`

- - -

### - `make_url(query=None, lang=None, **params)`

function for making request URL with GET parameters, must specify at least one of (`query`, `lang`)

keyword arguments `params` are as below (for the parameter **from**, use `from_` instead)

|keyword argument|format|example|
|:-:|:-:|:-:|
|`since`, `until`|'YYYY-MM-DD' or 'YYYY-MM-DD_hh:mm:ss_timezone'|`'2020-06-01_12:00:00_ICT'`|
|`from_`, `to`|str|`'NationTV22'`|
|`min_retweets`,`min_faves`,`min_replies`|int|5|
|`near` `within`|str float|`'เชียงใหม่'` 5|
|`geocode`|tuple or list of (latitude, longitude, radius)|(13, 100, 1)|


~~~python3
from ScrapeTweet import make_url

make_url(
  query='#สลิ่ม',
  lang='th',
  until='2020-8-16_20:00:00_ICT',
  geocode=(13.756567, 100.5002908, 0.5)
  )
  
>>>'https://twitter.com/search?f=live&q=%23สลิ่ม%20lang:th%20until:2020-8-16_20:00:00_ICT%20geocode:13.756567,100.5002908,0.5km'
~~~
- - -

## - `get_random_tweet_one_day(filename='randomtweet.json', lang='th', append=True, year=2020, month=4, day=1, headless=False, scroll_time=5, point_in_hour=2)`

scrape tweets in the specified day at random without keyword/hashtag. Output is JSON file that is a list of dictionaries. The program will sample two time points in one hour (e.g. 13, 52) and the window will scroll 5 times in default (about 1800 tweets per day). You can change `scroll_time` and `point_in_hour`. 

|keyword argument|description|
|:-:|:-:|
|`filename`|name of JSON file, default is `randomtweet.json`|
|`lang`|language, e.g. `th`,`en`,`ja`|
|`append`|if `True` and `filename` already exists, append to the file|
|`year`, `month`, `day`|the target date|
|`headless`|if `True`, browser is hidden. You must turn `True` when you use in Google Colab|
|`scroll_time`|how many times scroll the window. scroll_time<=50 is recommended because of reaching request limits|
|`point_in_hour`|the number of sampling point in one hour|

~~~python3
from ScrapeTweet import get_random_tweet_one_day

get_random_tweet_one_day(
  filename='20200816.json',
  lang='th',
  year=2020,
  month=8,
  day=16,
  scroll_time=10,
  point_in_hour=3
)
~~~

The program will open browser and scroll automatically. In this case (`scroll_time=10`, `point_in_hours=3`), it takes about 20 minutes to complete.

## - `get_tweet_by_query(query, filename='tweets.json', scroll_time=50, iter_time=10, headless=False)`

scrape tweets that contain specified keyword/hashtag by going back to the past. Output is JSON file that is a list of dictionaries. If `filename` already exists, the program will start from the oldest date in the file. `iter_time` is how many times the window open/close. In short, scroll_time * iter_time is the total number of window scroll. 

~~~python3
from ScrapeTweet import get_tweet_by_query

get_tweet_by_query(
  query='#สลิ่ม',
  scroll_time=50,
  iter_time=10
)
~~~

The program will finish after 10 times iterations.

- - -

## _class_ `Window(username=None, password=None, email=None, headless=False)`

An instance of class `Window` will hold a browser window and its contents. When instantiate it, you can choose headless mode by keyword argument `headless=True`. If you want to see how the program really works, it is recommended not to change. You can login with your account if you give three optional arguments `username`, `password` and `email`. 

~~~python3
from ScrapeTweet import make_url, Window

# instantiation
window = Window(
  username='@AABBCC',
  password='xxxxx',
  email = 'yamada@zzz.zzz.zz'
) 
~~~

### - `.get_page(url:str)`

get a page of `url` and get its content (html, BeautifulSoupObject) 

~~~python3
twitter_url = make_url(
  lang='th',
  until='2020-8-16_20:00:00_ICT',
)

window.get_page(twitter_url)
~~~

![window](https://user-images.githubusercontent.com/44984892/93103732-2fe28f80-f6d7-11ea-928d-5af70aab0630.png)

### -`.close()`

close browser window

### -`.url`

url of current page

~~~python3
window.url

>>>'https://twitter.com/search?f=live&q=lang:th%20until:2020-8-16_20:00:00_ICT'
~~~

### -`.html`

html of current page

### -`.soup`

BeutifulSoupObject of current page

### -`.scroll()`

scroll down. if the window cannot scorll more, it prints `'cannot scroll more'` (or, you can check by the variable `.scroll_end`)

### -`.get_contents()`

returns **list of BeautifulSoupObject of each tweet** for the next process (you don't have to use it by yourself)

- - -

## _class_ `TweetContent(content:bs4.element)`

class for processing each tweet. You don't have to use methods of this class by yourself.

### -`.get_data()`

returns content of tweet as dictionary. If the content is invalid, returns `None` instead.

~~~python3
from ScrapeTweet import make_url, Window, TweetContent

# make request URL
twitter_url = make_url(
  query='#ไม่นก',
  until='2015-12-31',
)

# make window instance without login
window = Window()

# get page
window.get_page(twitter_url)

# get the third content as BeautifulSoup
one_content_bs = window.get_contents()[2] 

# instantiation
content = TweetContent(one_content_bs) 

# get dictionary
content.get_data() 

>>>{'date': '2015-09-28T15:16:26',
 'displayname': 'ソーラービーム',
 'username': 'bheamrapee',
 'reply_to': '@bhury',
 'tweet': '#ไม่นก',
 'hashtag': ['#ไม่นก'],
 'language': 'und',
 'reply': '0',
 'retweet': '0',
 'like': '0',
 'url': 'https://twitter.com/tweet/status/648516624618655744'}
~~~