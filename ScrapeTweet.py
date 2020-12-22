from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
import pandas as pd
import re, json, os, sys, glob, datetime, random, tqdm, time

##############################################################################

class Window:
    def __init__(self, username=None, password=None, email=None, headless=False):
        
        # headless or not
        options = Options()
        if headless:
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(options=options)
        
        # initialize
        self.url = None; self.html = None; self.soup = None
        
        # login
        if username and password and email:
            self.twitter_login(username, password, email)
        
        # flag to check whether the window can scroll more
        self.scroll_end = False
        
    def twitter_login(self, username, password, email):
        self.driver.get('https://twitter.com/login')
        time.sleep(1)
        # input username
        self.driver.find_element_by_name('session[username_or_email]').send_keys(username)
        # input password
        self.driver.find_element_by_name('session[password]').send_keys(password)
        # click login button
        self.driver.find_element_by_css_selector('form > div > div:nth-child(8) > div').click()
        time.sleep(1)
        if self.driver.current_url.startswith('https://twitter.com/login/error'):
            self.driver.close()
            raise ValueError('cannot login')
        # verify Email (if any)
        elif self.driver.current_url.startswith('https://twitter.com/account/login_challenge'):
            hint = self.driver.find_element_by_tag_name('strong').text
            self.driver.find_element_by_id('challenge_response').send_keys(email)
            self.driver.find_element_by_id('email_challenge_submit').click()
            time.sleep(1)
            # email missmatch -> show input form
            if self.driver.current_url.startswith('https://twitter.com/account/login_challenge'):
                email = input(f'verify Email (hint {hint}): ')
                self.driver.find_element_by_id('challenge_response').send_keys(email)
                self.driver.find_element_by_id('email_challenge_submit').click()
                time.sleep(1)
                # missmatch twice -> raise error
                if self.driver.current_url.startswith('https://twitter.com/account/login_challenge'):
                    self.driver.close()
                    raise ValueError('cannot login, Email is not correct')
        
    
    def get_page(self, url):
        self.driver.get(url)
        time.sleep(3)
        self.url = self.driver.current_url
        self.html = self.driver.page_source.encode('utf8')
        self.soup = BeautifulSoup(self.html, 'html.parser')
        for _ in range(20):
            try:
                # set final tweet in the current window
                self.final_element = self.get_final_element()
                return
            except:
                if 'No results for' in str(self.html):
                    print('NO RESULTS')
                    self.driver.close()
                    return
                time.sleep(2) # wait and try again
        raise ConnectionError('check your internet connection status')
                

    def get_contents(self):
        """
        get the list of contents (tagged 'article') from present page
        <article>
            ...
        </article>
        each content is bs4 object
        even if the html structure of Twitter changes, this code can be used
        """
        self.html = self.driver.page_source.encode('utf8')
        self.soup = BeautifulSoup(self.html, 'html.parser')
        return self.soup.find_all('article')

    def get_final_element(self):
        return self.driver.find_elements_by_tag_name('article')[-1]
    
    def scroll(self):
        if self.scroll_end: # if cannot scroll more, end
            return
        for _ in range(5): # try 5 times
            try:
                actions = ActionChains(self.driver)
                actions.move_to_element(self.final_element)
                actions.perform()
                time.sleep(1)
                new_final_element = self.get_final_element()
                if new_final_element != self.final_element: # if get new one
                    self.final_element = new_final_element
                    return # scroll and finish
            except:
                pass
        # try 5 times but not change = no more result
        self.scroll_end = True

    def close(self):
        self.driver.close() 

#####################################################################################

class TweetContent:
    """
    get each tweet from bs4 object
    """
    def __init__(self, content):
        # one element of contents
        # content must be BeautifulSoupObject
        self.content = content      
        """
        @2020/8/27 one block is in "1-1-1-2-2-2th div" of content
        it may change in the future
        class names are unavailable, because they are changed frequently
        <article>
          <div> # 1
            <div> # 1-1
              <div> # 1-1-1
                <div>...</div>
                <div> # 1-1-1-2
                  <div>...</div>
                  <div> # 1-1-1-2-2
                    <div>...</div>
                    <div> # 1-1-1-2-2-2
                        --- BLOCK IS HERE ---
                        <div> reply to (if any) </div>
                        <div> tweet content </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </article>
        """
        try:
            self.block = self.content.div.div.div\
            .find_all('div',recursive=False)[1]\
            .find_all('div',recursive=False)[1]\
            .find_all('div',recursive=False)[1]
        except:
            pass
        
    def get_tweet_block(self):
        # if no reply, tweet is in 1-1-1-2-2-2 (-1th) div
        # else, tweet is in 1-1-1-2-2-2 (-2th) div
        """
        --- REPLY BLOCK = divs[0] ---
        <div class="...">
          <div class="..." dir="auto">
            Replying to 
            <div class="...">
              <a class="..." data-focusable="true" href="/pertetaeyongx" role="link">
                <span class="...">
                  @pertetaeyongx
                </span>
              </a>
            </div>
          </div>
        </div>

        --- TWEET BLOCK = divs[1] ---
        <div class="...">
          <div class="..." dir="auto" lang="th">
            <span class="...">
              โห ถามแบบนี้ลลไม่รู้จะตอบยังไงเลยเพราะดูแล้วเขาน่าจะไม่ออก555555
            </span>
          </div>
        </div>
        
        divs[-1] = retweet, reply, like
        """
        divs = self.block.find_all('div', recursive=False)
        if divs[0].text.startswith('Replying to'):
            self.reply_to = divs[0].text.split('Replying to')[-1].strip() # string
            self.tweet_block = divs[1] # bs4 object, continue to process in the next function
        else:
            self.reply_to = None
            self.tweet_block = divs[0]

    def get_tweet(self):
        """
        tweet_block contains both <span> and <a>
        ignore <img>
        --- self.tweet_block ---
        <div class="css-1dbjc4n">
          <div class="..." dir="auto" lang="th">
            <span class="...">
              แน่นอน
            </span>
            <a href="...">
              ...
            </a>
          </div>
        </div>
        """
        self.lang = self.tweet_block.div.get('lang')
        tweet = ''
        for segment in self.tweet_block.div.find_all(['span','a'],recursive=False):
            if segment.name == 'a':
                url = re.search(r'title="(.+?)"', str(segment)).group(1) # extract full URL
                tweet += url
            elif segment.text == '':
                # if img alt is one character = emoji 
                # exclude emoji w/o one char img alt e.g. img alt ="Dissapointed face"
                emoji = re.search(r'img alt="(.)"', str(segment))
                if emoji:
                    tweet += emoji.group(1)
            else:
                tweet += segment.text # normal text
        tweet = tweet.replace('\u200b', '')
        self.tweet = tweet
        
    def get_hashtags(self):
        self.hashtags = re.findall(r'(#[^#]+?)(?:[ \n]|$)', self.tweet)
        
    def get_retweet(self):
        text = str(self.block)
        self.reply = re.search(r'aria-label=\"(\d+?) Repl', text).group(1)
        self.retweet = re.search(r'aria-label=\"(\d+?) Retweet', text).group(1)
        self.like = re.search(r'aria-label=\"(\d+?) Like', text).group(1)
    
    def get_metadata(self):
        self.date = self.content.time.get('datetime')[:-5]
        self.displayname = self.content.find_all("a")[1].span.text
        self.username = self.content.find_all("a")[1].get('href')[1:]
        self.tweetid = self.content.find_all('a')[2].get('href').split('/')[-1]
    
    def get_data(self):
        self.get_tweet_block()
        self.get_tweet()
        self.get_hashtags()
        self.get_retweet()
        self.get_metadata()
        dic = {
            'date':self.date,
            'displayname':self.displayname,
            'username':self.username,
            'reply_to':self.reply_to,
            'tweet':self.tweet.strip(),
            'hashtag':self.hashtags,
            'language':self.lang,
            'reply':self.reply,
            'retweet':self.retweet,
            'like':self.like,
            'url':f'https://twitter.com/tweet/status/{self.tweetid}',
        }
        return dic

###################################################################################

def get_random_tweet_one_day(filename='randomtweet.json', append=True, lang='th', year=2020, month=4, day=1, headless=False, scroll_time=5, point_in_hour=2):
    if append and os.path.exists(filename):
        answer = input(f'do you append to "{filename}"? [y/n]: ')
        if answer != 'y':
            return
    elif append == False and os.path.exists(filename):
        answer = input(f'do you overwrite "{filename}"? [y/n]: ')
        if answer != 'y':
            os.remove(filename)
            return
        
    # iterate each hour
    for h in tqdm.tqdm(range(24)):
        window = Window(headless=headless) # make new window in oreder to refresh browser & IP address
        tweet_list = [] # list for storing tweet dict
        for j in range(point_in_hour): # every 60//point minutes
            # minute : selected randomly e.g. 0+14, 30+22, if point_in_hour == 2
            minute = j*(60//point_in_hour) + random.randint(0, 60//point_in_hour-1) 
            url = f'https://twitter.com/search?f=live&q=lang%3A{lang}%20until%3A{year}-{month}-{day}_{h}:{minute}:00_UTC'       
            window.get_page(url)
            for _ in range(scroll_time): # scroll
                contents = window.get_contents()
                tweet_list += get_tweets(contents)
                tweet_list = drop_duplicate(tweet_list)
                window.scroll()
        window.close()

        # write to file
        write_to_json(filename, tweet_list, append=True)

        
def get_tweet_by_query(query, filename='tweets.json', scroll_time=50, iter_time=10, headless=False, until_date=None):
    """
    scrape tweets by query or hashtag \n
    if choose existing filename, you can continue to scrape from the oldest date \n
    
    :scroll_time: how many times does the window scroll. scroll_time<=50 is recommended because of request limits \n
    :iter_time: how many times does the window open/close. In short, scroll_time * iter_time is the total number of scroll \n
    :headless: whether use headless mode or not. it must be True when run program in Google Colab
    """
    
    # replace hashtag #
    if query.startswith('#'):
        query = query.replace('#', '%23')

    # replace whitespace between queries
    query = re.sub(r'\s+', '%20', query.strip())
            
    # check existing file
    if os.path.exists(filename) and until_date==None:
        answer = input(f'continue from the oldest date of "{filename}"? [y/n]: ')
        if answer != 'y':
            return
        
    # iterate "max_iter"
    for _ in tqdm.tqdm(range(iter_time)):
        window = Window(headless=headless) # open/reopen window
        tweet_list = [] # list for storing tweet dict
        # if no until_date -> get the oldest date from the file
        if until_date:
            until = until_date
        else:
            until = get_until_date(filename) # 2020-03-31_17:02:58
        url = f'https://twitter.com/search?f=live&q={query}%20until%3A{until}_ICT'
        window.get_page(url)
        for _ in range(scroll_time): # scroll
            contents = window.get_contents()
            tweet_list += get_tweets(contents)
            tweet_list = drop_duplicate(tweet_list)
            window.scroll()
        window.close()

        # write to file & 
        write_to_json(filename, tweet_list, append=True)
        if until_date:
            until_date = tweet_list[-1]['date'].replace('T', '_')

def get_tweet_by_user(user, filename='tweet_user.json', scroll_time=50, iter_time=10, headless=False, until_date=None, append_newdata=False):
    """
    scrape tweets by username \n
    if choose existing filename, you can continue to scrape from the oldest date \n
    
    :scroll_time: how many times does the window scroll. scroll_time<=50 is recommended because of request limits \n
    :iter_time: how many times does the window open/close. In short, scroll_time * iter_time is the total number of scroll \n
    :headless: whether use headless mode or not. it must be True when run program in Google Colab
    :until_date: the newest date you need (default: today)
    :append_newdata: whether append new data (until today) into existing file or not. filename must be consistent 
    """
    
    ### add @ ###
    if not user.startswith('@'):
        user = '@' + user
            
    ### check existing file ###
    if append_newdata == True and os.path.exists(filename):
        answer = input(f'append new data to "{filename}"? [y/n]: ')
        if answer != 'y':
            return
    elif os.path.exists(filename) and until_date==None:
        answer = input(f'continue from the oldest date of "{filename}"? [y/n]: ')
        if answer != 'y':
            return
        
    ### iterate "max_iter" ###
    for _ in tqdm.tqdm(range(iter_time)):
        window = Window(headless=headless) # open/reopen window
        tweet_list = [] # list for storing tweet dict
        if append_newdata: # until today
            until = str(datetime.datetime.today()).split('.')[0].replace(' ','_') # '2020-12-18 03:23:16.998132' -> '2020-12-18 03:23:16' -> '2020-12-18_03:23:16'
        elif until_date:
            until = until_date
        else: # get the oldest date from the file
            until = get_until_date(filename) # 2020-03-31_17:02:58
        url = f'https://twitter.com/search?f=live&q=from%3A{user}%20until%3A{until}_ICT'
        window.get_page(url)
        for _ in range(scroll_time): # scroll
            contents = window.get_contents()
            tweet_list += get_tweets(contents)
            tweet_list = drop_duplicate(tweet_list)
            window.scroll()
        window.close()

        ### write to file ###
        write_to_json(filename, tweet_list, append=True, newdata=append_newdata)
        if until_date:
            until_date = tweet_list[-1]['date'].replace('T', '_')

    
def get_tweets(contents):
    """
    make list of dictionaries from contents list (list of bs4 objects)
    contents is a list of bs4 object, which Window.get_contents() gives
    """
    return_list = []
    for content in contents:
        try:
            inst = TweetContent(content)
            return_list.append(inst.get_data())
        except: # advetisement or hidden content
            pass
    return return_list

def drop_duplicate(lst_of_dict, reverse=False):
    newlist = []
    urllist = set()
    for dic in lst_of_dict:
        if dic['url'] not in urllist:
            newlist.append(dic)
            urllist.add(dic['url'])
    if reverse:
        return newlist[::-1]
    else:
        return newlist

def write_to_json(filename:str, tweet_list:list, append=True, newdata=False):
    if newdata and os.path.exists(filename):
        with open(filename) as f:
            data = json.load(f)
            data = tweet_list + data # append before
    elif append and os.path.exists(filename):
        with open(filename) as f:
            data = json.load(f)
            data += tweet_list # append after
    else:
        data = tweet_list
    with open(filename, 'w', encoding='utf8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
def get_until_date(filename):
    if os.path.exists(filename):
        df = pd.read_json(filename)
        df = df.iloc[len(df)-1]
        return df['date'].strftime('%Y-%m-%d_%H:%M:%S') # 2020-03-31_17:02:58
    else:
        until = datetime.datetime.now()
        return until.strftime('%Y-%m-%d_%H:%M:%S')

###################################################################################

def make_url(query=None, lang=None, **params):
    """
    make request URL with parameters \n
    :query: keyword XXX or hashtag #XXX \n
    :lang: language e.g. th, en, ja \n
    :params: optional parameters, use "from_" instead "from" \n
    >>> make_url(query='นก', since='2020-01-01', from_='NationTV22')
    """
    url = 'https://twitter.com/search?f=live&q='
    
    ### query OR language ###
    if query == None and lang == None and 'from_' not in params:
        raise ValueError('must specify at least one of (query=, lang=)')
        
    ### query ###
    if query:
        if query.startswith('#'):
            query = query.replace('#', '%23')
        query = re.sub(r'\s+', '%20', query)
        url += query + '%20'
        
    ### language ###
    if lang:
        if lang in ["en", "ar", "bn", "cs", "da", "de", "el", "es",
                    "fa", "fi", "fil", "fr", "he", "hi", "hu", "id",
                    "it", "ja", "ko", "msa", "nl", "no", "pl", "pt", "und",
                    "ro", "ru", "sv", "th", "tr", "uk", "ur", "vi", "zh-cn", "zh-tw"]:
            url += f"lang:{lang}%20"
        else:
            raise ValueError(f'language "{lang}" is not supported')
            
    ### since ###
    if 'since' in params:
        since = params['since']
        try: # check YYYY-MM-DD format
            Y,M,D = map(int, (since.split('_')[0].split('-')))
            datetime.datetime(Y,M,D)
        except:
            raise ValueError('date format must be YYYY-MM-DD')
        if since.count('_') >= 1: # if has time & timezone
            try:
                Y,M,D = map(int, since.split('_')[0].split('-'))
                h,m,s = map(int, since.split('_')[1].split(':'))
                datetime.datetime(Y,M,D,h,m,s)
            except:
                raise ValueError('datetime format must be YYYY-MM-DD_HH:MM:SS')
            if since.count('_') >= 2:
                if not since.split('_')[2] in ['ICT', 'UTC']:
                    raise ValueError('timezone must be "ICT" or "UTC"')
            url += f'since:{since}%20'
        else: # without time, timezone
            url += f'since:{since}_0:00:00_ICT%20'
            
    ### until ###
    if 'until' in params:
        until = params['until']
        try: # check YYYY-MM-DD format
            Y,M,D = map(int, (until.split('_')[0].split('-')))
            datetime.datetime(Y,M,D)
        except:
            raise ValueError('date format must be YYYY-MM-DD')
        if until.count('_') >= 1: # if has time & timezone
            try:
                Y,M,D = map(int, until.split('_')[0].split('-'))
                h,m,s = map(int, until.split('_')[1].split(':'))
                datetime.datetime(Y,M,D,h,m,s)
            except:
                raise ValueError('datetime format must be YYYY-MM-DD_HH:MM:SS')
            if until.count('_') >= 2:
                if not until.split('_')[2] in ['ICT', 'UTC']:
                    raise ValueError('timezone must be "ICT" or "UTC"')
            url += f'until:{until}%20'
        else: # without time, timezone
            url += f'until:{until}_0:00:00_ICT%20'
            
    ### from, to ###
    if 'from_' in params:
        url += f"from:{params['from_']}%20"
    if 'to' in params:
        url += f"to:{params['to']}%20"
        
    ### min retweet, like, reply ###
    if 'min_retweets' in params:
        try:
            int(params['min_retweets'])
        except:
            raise ValueError('min_retweets must be integer')
        url += f"min_retweets:{params['min_retweets']}%20"
        
    if 'min_faves' in params:
        try:
            int(params['min_faves'])
        except:
            raise ValueError('min_faves must be integer')
        url += f"min_faves:{params['min_faves']}%20"
        
    if 'min_replies' in params:
        try:
            int(params['min_replies'])
        except:
            raise ValueError('min_replies must be integer')
        url += f"min_replies:{params['min_replies']}%20"
    
    ### near ###
    if 'near' in params:
        url += f"near:{params['near']}%20"
        if 'within' in params:
            url += f"within:{params['within']}km%20"
            
    ### geocode ###
    if 'geocode' in params:
        geocode = params['geocode']
        if not (type(geocode) == tuple or type(geocode) == list):
            raise TypeError('geocode must be list or tuple')
        if len(geocode) != 3:
            raise ValueError('geocode must have (latitude, longitude, radius)')
        try:
            for x in geocode:
                float(x)
        except:
            raise ValueError('(latitude, longitude, radius) must be numeric')
        url += f"geocode:{','.join(map(str,geocode))}km%20"
    
    return url.strip('%20')
