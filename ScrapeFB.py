from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
import re, json, os, sys, tqdm, time, html, traceback, bs4

def clean(text:str, remove_newline=False):
	text = html.unescape(text) # e.g. &ldquo; -> “
	text = re.sub(r'[“”„]', '"', text) # convert double quotations into "
	text = re.sub(r'[‘’`]', "'", text) # convert single quotations into '
	text = re.sub(r'[ \u00a0\xa0\u3000\u2002-\u200a\t]+', ' ', text) # shrink spaces  e.g. good  boy -> good boy
	text = re.sub(r'[\r\u200b\ufeff]+', '', text) # remove zero-width spaces
	text = text.replace('<span class="text_exposed_hide">...</span><span class="text_exposed_show">', '') # remove "show more"
	text = re.sub(r'</?span.+?>', '', text)
	return text.strip()

def convert_date_thai1(date): # "วันอังคารที่ 22 กันยายน  2020 เวลา 04:00 น." -> 2020-09-22T04:00
	try:
		_,day,month,year,_,t,_ = re.split(' +', date)
		if len(day) == 1:
			day = '0' + day
		month = {'มกราคม':'01','กุมภาพันธ์':'02','มีนาคม':'03','เมษายน':'04','พฤษภาคม':'05','มิถุนายน':'06',
				'กรกฎาคม':'07','สิงหาคม':'08','กันยายน':'09','ตุลาคม':'10','พฤศจิกายน':'11','ธันวาคม':'12'}[month]
		return f'{year}-{month}-{day} {t}'
	except:
		return date

def convert_date_thai2(date): # "2020-ตุลาคม-15 20:00" -> 2020-10-22 04:00
	try:
		year, month, day, t = re.split(r'[ \-]', date)
		if len(day) == 1:
			day = '0' + day
		month = {'มกราคม':'01','กุมภาพันธ์':'02','มีนาคม':'03','เมษายน':'04','พฤษภาคม':'05','มิถุนายน':'06',
				'กรกฎาคม':'07','สิงหาคม':'08','กันยายน':'09','ตุลาคม':'10','พฤศจิกายน':'11','ธันวาคม':'12'}[month]
		return f'{year}-{month}-{day} {t}'
	except:
		return date

##############################################################################
###   CLASS OF SELENIUM WINDOW
###   inherited to WindowLogin or WindowNoLogin
##############################################################################

class Window:

	def __init__(self, url=None, headless=False, browser='chrome'):
		### SELENIUM WEBDRIVER ###
		
		if headless: # headless or not (must True on google colab,)
			if browser.lower() == 'chrome':
				options = webdriver.chrome.options.Options()
				options.add_argument('--headless')
				options.add_argument('--no-sandbox')
				options.add_argument('--disable-dev-shm-usage')
				self.driver = webdriver.Chrome(options=options)
			elif browser.lower() == 'firefox':
				options = webdriver.firefox.options.Options()
				options.add_argument("--headless")
				options.add_argument("start-maximized")
				self.driver = webdriver.Firefox(options=options)
		elif browser.lower() == 'chrome':
			self.driver = webdriver.Chrome()
		elif browser.lower() == 'firefox':
			self.driver = webdriver.Firefox()
		elif browser.lower() == 'opera':
			self.driver = webdriver.Opera()
		elif browser.lower() == 'safari':
			self.driver = webdriver.Safari()
		### SCRAPED DATA ###
		self.scraped_posts = []
		self.scraped_ID = set() # scraped ID of selenium element
		self.url = url
		if self.__class__ == WindowNoLogin:
			self.get_page()
	
	def get_page(self):
		self.driver.get(self.url)

	def close(self):
		self.driver.close()

	def write(self, filename):
		with open(filename, 'w', encoding='utf8') as f:
			json.dump(self.scraped_posts, f, indent=2, ensure_ascii=False)


##############################################################################
###   WINDOW WITHOUT LOGIN
##############################################################################

class WindowNoLogin(Window):
	def load_jquery(self, filepath='jquery.js'):
		with open(filepath) as f:
			script = f.read()
		self.driver.execute_script(script)

	def scroll(self):
		for _ in range(10): # try 10 times = 10 sec
			self.final_element = self.get_final_element()
			try: # close warning popup, if any
				self.driver.execute_script("document.querySelector('._t').querySelector('.autofocus').click()")
			except:
				pass
			try: # remove login popup, if any
				self.driver.execute_script("document.querySelector('#dialog_0').remove();")
			except:
				pass
			try:
				# scroll to the bottom
				self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
				time.sleep(1)
				new_final_element = self.get_final_element() # get new final element
				if new_final_element != self.final_element: # if new one != old one, success
					self.final_element = new_final_element
					return # finish the function
			except:
				pass # retry

	def get_post_elements(self):
		main_content = self.driver.find_element_by_css_selector('#pagelet_timeline_main_column')
		return main_content.find_elements_by_css_selector('div._427x')
	def get_first_element(self):
		main_content = self.driver.find_element_by_css_selector('#pagelet_timeline_main_column')
		return main_content.find_element_by_css_selector('div._427x')
	def get_final_element(self):
		try:
			return self.get_post_elements()[-1]
		except: # no element = after delete element
			return None
	def delete_elements(self):
		# delete all post elements & unwrap parent nodes: using jQuery $(elem).unwrap()
		self.driver.execute_script("document.querySelectorAll('._4-u2._4-u8').forEach(x => x.remove())")
		self.driver.execute_script("while(true){elems=document.querySelectorAll('#pagelet_timeline_main_column ._1xnd');if(elems.length>1){$(elems[elems.length-1]).unwrap();}else{break;}}")

	##### MAIN FUNCTION #####
	def scrape(self, filename='FB.json', scroll=10):
		for _ in tqdm.tqdm(range(scroll)): # scroll n times
			self.scroll()
		time.sleep(2)
		self.append_data(); print('append')
		self.load_jquery(); print('reload jQuery') # reload jQuery
		self.delete_elements(); print('delete')
		self.write(filename); print('write')

	def append_data(self):
		post_elems = self.get_post_elements()
		for post_elem in post_elems:
			if post_elem.id in self.scraped_ID:
				continue
			try:
				dic = self.get_one_post(post_elem)
				self.scraped_posts.append(dic)
				self.scraped_ID.add(post_elem.id)
			except:
				pass

	def get_one_post(self, post_elem):
		### GET DATE ###
		date = post_elem.find_element_by_tag_name('abbr').get_attribute('title')
		try:
			date = convert_date_thai2(date) # for Thai "วันอังคารที่ 22 กันยายน  2020 เวลา 04:00 น."
		except:
			date = date
    
		### RAW HTML & bs4 OBJECT ### 
		raw_html = post_elem.get_attribute('innerHTML') # get html content of element
		soup = bs4.BeautifulSoup(raw_html, features='html.parser') 
    
		### REMOVE INNERT POSTS (shared content) ### <class="mts">
		if soup.select('.mts'):
			for child in soup.select('.mts'):
				child.decompose()
    
		### post ID & article ###
		ID = re.search(r'<input type="hidden".+?value="(\d+)">', raw_html).group(1)
		article = '\n'.join([clean(x.text) for x in soup.find_all('p')]) # each paragraph is in <p> tag

		### EMOTIONS ###
		like = self.get_emotion_num(raw_html, 'ถูกใจ', 'Like')
		love = self.get_emotion_num(raw_html, 'รักเลย', 'Love')
		care = self.get_emotion_num(raw_html, 'ห่วงใย', 'Care')
		haha = self.get_emotion_num(raw_html, 'ฮ่าๆ', 'Haha')
		wow = self.get_emotion_num(raw_html, 'ว้าว', 'Wow')
		sad = self.get_emotion_num(raw_html, 'เศร้า', 'Sad')
		angry = self.get_emotion_num(raw_html, 'โกรธ', 'Angry')
    
		### COMMENT & SHARE ###
		try:
			comment = re.search(r'>(\d+) Comments?</a>', raw_html).group(1)
		except:
			try:
				comment = re.search(r'>ความคิดเห็น (\d+) รายการ</a>', raw_html).group(1)
			except:
				comment = 0
		try:
			share = re.search(r'>(\d+) Shares?</a>', raw_html).group(1)
		except:
			try:
				share = re.search(r'>แชร์ (\d+) ครั้ง</a>', raw_html).group(1)
			except:
				share = 0
    
		### HASHTAGS ###
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

	def get_emotion_num(self, raw_html, th_name, en_name): # th, en are name of emotions
		match = re.search(r'aria-label="(\d+) ({0}|{1})"'.format(th_name, en_name), raw_html)
		if match:
			return int(match.group(1))
		else:
			return 0 

##############################################################################
###   WINDOW WITH LOGIN
##############################################################################

class WindowLogin(Window):
	def __init__(self, url=None, headless=False, browser='Firefox', email=None, password=None):
		super().__init__(url, headless, browser)
		### USERNAME & PASSWORD ###
		self.email = email
		self.password = password
		### LOGIN ###
		self.login()
		self.get_page()

	def login(self):
		if self.email == None or self.password == None:
			print('CANNOT LOGIN')
			return
		else:
			self.driver.get('https://www.facebook.com/')
			time.sleep(1)
			self.driver.find_element_by_css_selector('#email').send_keys(self.email)
			self.driver.find_element_by_css_selector('#pass').send_keys(self.password)
			self.driver.find_element_by_css_selector('button[name="login"]').click()
			time.sleep(1)

	def get_post_elements(self):
		return self.driver.find_elements_by_css_selector('.du4w35lb.k4urcfbm.l9j0dhe7.sjgh65i0')
	def get_first_element(self):
		return self.driver.find_element_by_css_selector('.du4w35lb.k4urcfbm.l9j0dhe7.sjgh65i0')
	def get_final_element(self):
		return self.get_post_elements()[-1]
	def delete_element(self): # delete one element
		self.driver.execute_script("document.querySelector('.du4w35lb.k4urcfbm.l9j0dhe7.sjgh65i0').remove();")

	def append_data(self, post_elem, need_emotion=False):
		# scrape only new elements
		if post_elem.id in self.scraped_ID:
			self.delete_element()
		else:
			dic = self.get_one_post(post_elem, emotion=need_emotion)
			self.scraped_posts.append(dic)
			self.scraped_ID.add(post_elem.id)
			self.delete_element()

	def scroll_to_element(self):
		self.driver.execute_script('window.scrollTo(0, 400);') # scroll up into view	
	
	def write(self, filename):
		with open(filename, 'w', encoding='utf8') as f:
			json.dump(self.scraped_posts, f, indent=2, ensure_ascii=False)

	def scrape(self, filename='FB.json', scroll=10, retry=5):
		for _ in tqdm.tqdm(range(scroll)):
			# get first element and scrol
			post_elem = self.get_first_element()
			for i in range(retry): # try 5 times
				try:
					self.append_data(post_elem, False)
					break
				except:
					pass
				if i == retry-1:
					self.delete_element() # if not succeed, skip
		self.write(filename)

	def get_date_from_elem(self, post_elem, sleeptime=1):
		date_elem = post_elem.find_elements_by_css_selector('.qzhwtbm6.knvmm38d')[1].find_element_by_css_selector('a')
		self.mouseover_element(post_elem) # mouseoff <a>
		self.mouseover_element(date_elem) # mouseover <a>
		time.sleep(sleeptime)
		# get date from popover & create link by mouseover
		link = date_elem.get_attribute('href').split('?')[0]
		mousehover_elem = self.driver.find_elements_by_css_selector('.__fb-light-mode')[-1] # get date modal
		date = mousehover_elem.text.strip()
		self.mouseover_element(post_elem) # mouseoff <a> again
		return date, link

	def mouseover_element(self, selenium_elem):
		actions = ActionChains(self.driver)
		actions.move_to_element(selenium_elem)
		self.scroll_to_element()
		actions.perform()

	def get_one_post(self, post_elem, emotion=False):

		### CLICK "See More" ###
		try:
			post_elem.find_element_by_css_selector('div[role="button"].lrazzd5p').click()
		except:
			pass

		### GET DATE & URL ###
		# mouseover by selenium, and create link in <a href="#"> -> <a href="...">
		date, link = '', ''
		for i in range(6): # if date is empty, wait more 1+i*0.5 sec
			if date == '' or link.endswith('#'):
				date, link = self.get_date_from_elem(post_elem, 1+i*0.5)
			else:
				break


		### ARTICLE & HASHTAGS ###
		# raw HTML & bs4 object
		raw_html = post_elem.get_attribute('innerHTML') # get html content of this element
		soup = bs4.BeautifulSoup(raw_html, features='html.parser')
		# lists to store
		article = []; hashtags = []
		for paragraph in soup.select('.cxmmr5t8.oygrvhab.hcukyx3x.c1et5uql.ii04i59q'):
			text_in_paragraph = ''
			for div in paragraph.select('div'):
				for child in div.children:
					if type(child) == bs4.element.NavigableString:
						text_in_paragraph += '\n' + child
					elif type(child) == bs4.element.Tag:
						inner_text = child.text.strip()
						if inner_text != '': # hashtag or link
							if inner_text.startswith('#'): # hashtag
								hashtags.append(inner_text)
							else: # link
								text_in_paragraph += inner_text
						else:
							emoji = re.search(r'<img alt="(.+?)".+/?>', str(child))
							if emoji:
								text_in_paragraph += emoji.group(1)
			article.append(text_in_paragraph)
		article = '\n\n'.join(article)

		### COMMENTS & SHARES ###
		comment, share = 0, 0
		for e in soup.select('.gtad4xkn'):
			if re.search(r'Shares?$', e.text):
				share = e.text.rsplit(' ', 1)[0]
			elif re.search(r'Comments?$', e.text):
				comment = e.text.rsplit(' ', 1)[0]

		dic = {
			'date': date,
			'article': clean(article),
			'url': link,
			'comment': comment,
			'share': share,
			'hashtags': hashtags
		}

		### EMOTIONS ###
		if emotion:
			emotion_dic = {'like':0, 'love':0, 'care':0, 'haha':0, 'wow':0, 'sad':0, 'angry':0} # initialize dictionary
			post_elem.find_element_by_css_selector('.bp9cbjyn.j83agx80.buofh1pr.ni8dbmo4.stjgntxs > div').click() # open emotion modal
			time.sleep(1)
			for emotion in self.driver.find_elements_by_css_selector('.j1lvzwm4.dati1w0a'):
				try:
					icon_href = emotion.find_element_by_css_selector('img').get_attribute('src') # there are no label, only href for icon
					num = int(re.search(r'>(\d+)</span>', emotion.get_attribute('innerHTML')).group(1))
				except:
					continue # no icon href = "All" tab
				if icon_href.startswith('https://static.xx.fbcdn.net/rsrc.php/v3/yU/r/tc5IAx58Ipa.png'):
					emotion_dic['like'] = num
				elif icon_href.startswith('https://static.xx.fbcdn.net/rsrc.php/v3/yE/r/MB1XWOdQjV0.png'):
					emotion_dic['love'] = num
				elif icon_href.startswith('https://static.xx.fbcdn.net/rsrc.php/v3/yR/r/QTVmPoFjk5O.png'):
					emotion_dic['care'] = num
				elif icon_href.startswith('https://static.xx.fbcdn.net/rsrc.php/v3/yS/r/tHO3j6Ngeyx.png'):
					emotion_dic['wow'] = num
				elif icon_href.startswith('https://static.xx.fbcdn.net/rsrc.php/v3/yK/r/bkP6GqAFgZ_.png'):
					emotion_dic['haha'] = num
				elif icon_href.startswith('https://static.xx.fbcdn.net/rsrc.php/v3/y4/r/1eqxxZX7fYp.png'):
					emotion_dic['sad'] = num
				elif icon_href.startswith('https://static.xx.fbcdn.net/rsrc.php/v3/yY/r/PByJ079GWfl.png'):
					emotion_dic['angry'] = num
			# close emotion window
			self.driver.find_element_by_css_selector('.cypi58rs.pmk7jnqg.fcg2cn6m.tkr6xdv7').click()
			dic['emotion'] = emotion_dic
		
		return dic