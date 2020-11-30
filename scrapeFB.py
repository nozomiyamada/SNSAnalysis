from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import pandas as pd
import re, json, os, sys, glob, tqdm, time, html

def clean(text:str, remove_newline=False):
    text = html.unescape(text) # e.g. &ldquo; -> “
    text = re.sub(r'[“”„]', '"', text) # convert double quotations into "
    text = re.sub(r'[‘’`]', "'", text) # convert single quotations into '
    text = re.sub(r'[ \u00a0\xa0\u3000\u2002-\u200a\t]+', ' ', text) # shrink spaces  e.g. good  boy -> good boy
    text = re.sub(r'[\r\u200b\ufeff]+', '', text) # remove zero-width spaces
    text = text.replace('<span class="text_exposed_hide">...</span><span class="text_exposed_show">', '') # remove "show more"
    text = re.sub(r'</?span.+?>', '', text)
    if remove_newline:
        text = re.sub(' *\n *', ' ', text) # _\n__ -> _ single whitespace 
    return text.strip()

def convert_date_thai(date): # "วันอังคารที่ 22 กันยายน  2020 เวลา 04:00 น." -> 2020-09-22T04:00
    _,day,month,year,_,t,_ = re.split(' +', date)
    if len(day) == 1:
        day = '0' + day
    month = {'มกราคม':'01','กุมภาพันธ์':'02','มีนาคม':'03','เมษายน':'04','พฤษภาคม':'05','มิถุนายน':'06',
            'กรกฎาคม':'07','สิงหาคม':'08','กันยายน':'09','ตุลาคม':'10','พฤศจิกายน':'11','ธันวาคม':'12'}[month]
    return f'{year}-{month}-{day}T{t}'

##############################################################################
###   CLASS OF SELENIUM WINDOW
###   open a browser without login and scrape
##############################################################################
class Window:
    def __init__(self, headless=False, url=None):
        # headless or not (must True on google colab,)
        options = Options()
        if headless:
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
            self.driver = webdriver.Chrome(options=options)
        else:
            self.driver = webdriver.Chrome()

        # initialize & get page (if any)
        self.url = url; self.html = None
        if self.url != None:
            self.get_page(self.url)
        
        # flag to check whether the window can scroll more
        self.scroll_end = False

        # scraped data (list of dict)
        self.scraped_data = []
        
    def jquery(self, filepath='jquery.js'):
        with open(filepath) as f:
            script = f.read()
        self.driver.execute_script(script)
        
    def get_page(self, url):
        # get and wait
        self.driver.get(url)
        time.sleep(5)

        # keep current status
        self.url = self.driver.current_url
        self.html = self.driver.page_source.encode('utf8')

        # try to fetch contents 20 times
        # if not succeed, may be connection error
        for _ in range(20):
            try:
                # if succeed, break
                self.final_element = self.get_final_element()
                # read jquery
                self.jquery()
                return
            except:
                if 'ลิงก์ที่คุณเคยติดตามอาจเสียหายหรืออาจได้มีการลบเพจนี้ออกแล้ว' in str(self.html): # no page
                    print('NO RESULTS')
                    self.driver.close()
                    return
                time.sleep(2) # wait and try again
        raise ConnectionError('check your internet connection status')
                

    def get_elements(self):
        """
        get the list of post in present page
        <div class="_427x">
            ...
        </div>
        """
        main_content = self.driver.find_element_by_css_selector('div._1xnd')
        return main_content.find_elements_by_css_selector('div._427x')


    def get_final_element(self):
        return self.get_elements()[-1]


    def scroll(self):
        for _ in range(10): # try 10 times = 10 sec
            try:
                # close modal window, if any
                try:
                    self.driver.execute_script("document.querySelector('._t').querySelector('.autofocus').click()")
                except:
                    pass
                # scroll to the bottom
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                new_final_element = self.get_final_element() # get new final element
                if new_final_element != self.final_element: # if new one != old one, success
                    self.final_element = new_final_element
                    return # finish the function
            except:
                pass # retry

    def close(self):
        self.driver.close()

    def scrape(self, filename='FB.json', scroll=10):
        # scroll n times
        for _ in tqdm.tqdm(range(scroll)):
            self.scroll()

        # get all elements
        elems = self.get_elements()
        
        # scrape only new elements
        for elem in elems:
            try:
                dic = get_one_post(elem)
                self.scraped_data.append(dic)
            except: # error = inner content, etc
                pass
                
        # delete scraped elements
        self.driver.execute_script("document.querySelectorAll('._4-u2._4-u8').forEach(x => x.remove())")
        
        # unwrap parent nodes: using jQuery $(elem).unwrap()
        self.driver.execute_script("while(true){elems=document.querySelectorAll('._1xnd');if(elems.length>1){$(elems[elems.length-1]).unwrap();}else{break;}}")

        with open(filename, 'w') as f:
            json.dump(self.scraped_data, f, indent=2, ensure_ascii=False)

#####################################################################################

def get_one_post(elem):
    # date
    date = elem.find_element_by_tag_name('abbr').get_attribute('title')
    try:
        date = convert_date_thai(date) # for Thai "วันอังคารที่ 22 กันยายน  2020 เวลา 04:00 น."
    except:
        date = date
    
    # raw HTML & bs4 object 
    raw_html = elem.get_attribute('innerHTML') # get html content of element
    soup = BeautifulSoup(raw_html, features='html.parser') 
    
    # remove inner post (shared content) : <class="mts">
    if soup.select('.mts'):
        for child in soup.select('.mts'):
            child.decompose()
    
    # post ID & article
    ID = re.search(r'<input type="hidden".+?value="(\d+)">', raw_html).group(1)
    article = '\n'.join([clean(x.text) for x in soup.find_all('p')]) # each paragraph is in <p> tag
    
    # emotions
    def get_emotion_num(th, en): # th, en are name of emotions
        match = re.search(r'aria-label="(\d+) ({0}|{1})"'.format(th, en), raw_html)
        if match:
            return int(match.group(1))
        else:
            return 0 
    like = get_emotion_num('ถูกใจ', 'Like')
    love = get_emotion_num('รักเลย', 'Love')
    care = get_emotion_num('ห่วงใย', 'Care')
    haha = get_emotion_num('ฮ่าๆ', 'Haha')
    wow = get_emotion_num('ว้าว', 'Wow')
    sad = get_emotion_num('เศร้า', 'Sad')
    angry = get_emotion_num('โกรธ', 'Angry')
    
    # comment
    try:
        comment = int(re.search(r'>(\d+) Comments?</a>', raw_html).group(1))
    except:
        try:
            comment = int(re.search(r'>ความคิดเห็น (\d+) รายการ</a>', raw_html).group(1))
        except:
            comment = 0
        
    # share
    try:
        share = int(re.search(r'>(\d+) Shares?</a>', raw_html).group(1))
    except:
        try:
            share = int(re.search(r'>แชร์ (\d+) ครั้ง</a>', raw_html).group(1))
        except:
            share = 0
    
    
    # hashtags
    hashtags = soup.select('span._58cm')
    if hashtags:
        hashtags = [x.text for x in hashtags]
    
    dic = {
        'date': date,
        'article': clean(article),
        'url': f'https://www.facebook.com/{ID}',
        'emotion': {'like':like, 'love':love, 'care':care, 'haha':haha, 'wow':wow, 'sad':sad, 'angry':angry},
        'comment': comment,
        'share': share,
        'hashtags': hashtags
    }
    
    return dic

###################################################################################