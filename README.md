# TwitterAnalysis

### `ScrapeTweet.py`

- `make_url(query=None, lang=None, **params)`

make request URL with GET parameters, must specify at least one of (`query`, `lang`)

keyword arguments `params` are as below (for the parameter **from**, use `from_` instead)

|keyword argument|format|example|
|:-:|:-:|:-:|
|`since`, `until`|'YYYY-MM-DD' or 'YYYY-MM-DD_hh:mm:ss_timezone'|`'2020-06-01_12:00:00_ICT'`|
|`from_`, `to`|str|`'NationTV22'`|
|`min_retweets`,`min_faves`,`min_replies`|int|5|
|`near` `within`|str float|`'เชียงใหม่'` 5|
|`geocode`|tuple or list of (latitude, longitude, radius)|(13, 100, 1)|


~~~python
make_url(
  query='#สลิ่ม',
  lang='th',
  until='2020-8-16_20:00:00_ICT',
  geocode=(13.756567, 100.5002908, 0.5)
  )
  
>>>'https://twitter.com/search?f=live&q=%23สลิ่ม%20lang:th%20until:2020-8-16_20:00:00_ICT%20geocode:13.756567,100.5002908,0.5km'
~~~
