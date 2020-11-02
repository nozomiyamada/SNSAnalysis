from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from bs4 import BeautifulSoup
import pandas as pd
import re, json, os, sys, glob, tqdm, time, html

def clean(text:str, remove_newline=False):
    text = html.unescape(text) # e.g. &ldquo; -> “
    text = re.sub(r'[“”„]', '"', text) # convert double quotations into "
    text = re.sub(r'[‘’`]', "'", text) # convert single quotations into '
    text = re.sub(r'[ \u00a0\xa0\u3000\u2002-\u200a\t]+', ' ', text) # e.g. good  boy -> good boy
    text = re.sub(r'[\r\u200b\ufeff]+', '', text) # remove zero-width spaces
    text = text.replace('<span class="text_exposed_hide">...</span><span class="text_exposed_show">', '')
    text = re.sub(r'</?span.+?>', '', text)
    if remove_newline:
        text = re.sub(' *\n *', ' ', text) # _\n__ -> _ single whitespace 
    return text.strip()

##############################################################################

class Window:
    def __init__(self, headless=False):
        
        # headless or not
        options = Options()
        if headless:
            options.add_argument('--headless')
            options.add_argument('--no-sandbox')
            options.add_argument('--disable-dev-shm-usage')
        self.driver = webdriver.Chrome(options=options)
        
        # initialize
        self.url = None; self.html = None; self.soup = None
        
        # flag to check whether the window can scroll more
        self.scroll_end = False
        
    
    def get_page(self, url):
        self.driver.get(url)
        time.sleep(5)
        self.url = self.driver.current_url
        self.html = self.driver.page_source.encode('utf8')
        for _ in range(20):
            try:
                # set final tweet in the current window
                self.final_element = self.get_final_element()
                return
            except:
                if 'ลิงก์ที่คุณเคยติดตามอาจเสียหายหรืออาจได้มีการลบเพจนี้ออกแล้ว' in str(self.html):
                    print('NO RESULTS')
                    self.driver.close()
                    return
                time.sleep(2) # wait and try again
        raise ConnectionError('check your internet connection status')
                

    def get_elements(self):
        """
        get the list of elements from present page
        <div class="_427x">
            ...
        </div>
        """
        main_content = self.driver.find_element_by_css_selector('div._1xnd')
        return main_content.find_elements_by_css_selector('div._427x')

    def get_final_element(self):
        return self.driver.find_elements_by_css_selector('div._427x')[-1]
    
    def scroll(self):
        for _ in range(10): # try 10 times
            try:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(1)
                new_final_element = self.get_final_element() # get new final element
                if new_final_element != self.final_element: # if new one == old one, retry
                    self.final_element = new_final_element
                    return # scroll and finish
            except:
                pass

    def close(self):
        self.driver.close()

#####################################################################################

def get_one_post(elem):
    date = elem.find_element_by_tag_name('abbr').get_attribute('title')
    #status = elem.find_element_by_css_selector('.fbPrivacyAudienceIndicator').get_attribute('aria-label')
    raw_html = elem.get_attribute('innerHTML') # get html content of element
    
    # make html into bs4 
    soup = BeautifulSoup(raw_html, features='html.parser') 
    # remove inner post (shared content)
    if soup.select('mts'):
        for child in soup.select('mts'):
            child.decompose()
    
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
        comment = int(re.search(r'>(\d+) (comments?|ความคิดเห็น)</a>', raw_html).group(1))
    except:
        comment = 0
        
    # share
    try:
        share = int(re.search(r'>(\d+) (shares?|แชร์)</a>', raw_html).group(1))
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

def scrape(URL, filename='FB.json', datalist=[], scroll=1000):
    window.get_page(URL)
    elems = window.get_elements()
    for elem in tqdm.tqdm(elems):
        try:
            dic = get_one_post(elem)
            datalist.append(dic)
        except: # error = inner content
            pass
    with open(filename, 'w') as f:
        json.dump(datalist, f, indent=2, ensure_ascii=False)
    
