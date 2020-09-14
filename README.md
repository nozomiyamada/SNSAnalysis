## `ScrapeTweet.py`

HOW DOES IT WORK?
  
  Since Twitter is dynamic website (using Ajax, iframe), the ordinary way such as `requests.get(URL)` cannot get its contents. Therefore, it is necessary to open in browser in order to scrape the contents.
  
[selenium](https://pypi.org/project/selenium/) is one of the software(interface) that can manipulate web browser by using programming language. It also enables to access website without opening real browser window (so-called _headless_). The codes here also using selenium in the background.

To use this program, python package [selenium](https://pypi.org/project/selenium/) and [chromedriver](https://chromedriver.chromium.org/) are needed. The version of chromedrive must be compatible with the version of Google Chrome that you use. After you downloaded chromedriver, the binary file must be move to PATH environment such as `usr/local/bin`

### - `make_url(query=None, lang=None, **params)`

make request URL with GET parameters, must specify at least one of (`query`, `lang`)

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

### - _class_ `Window(url=None, headless=False)`

An instance of class `Window` will hold a browser window and its contents. When instantiate, you can choose headless mode by keyword argument `headless=True`. If you want to see how the program really works, it is recommended not to change. `url` is the URL of website to access at first (optional).

~~~python3
from ScrapeTweet import make_url, Window

twitter_url = make_url(
  lang='th',
  until='2020-8-16_20:00:00_ICT',
  )
  
window = Window(twitter_url) 
~~~

![window](https://user-images.githubusercontent.com/44984892/93103732-2fe28f80-f6d7-11ea-928d-5af70aab0630.png)

