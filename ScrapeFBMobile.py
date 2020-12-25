from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
import re, json, os, sys, tqdm, time, html, traceback, bs4
from datetime import datetime, timedelta

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
		self.get_page()
	
	def get_page(self):
		self.driver.get(self.url)

	def close(self):
		self.driver.close()

	def write(self, filename):
		with open(filename, 'w', encoding='utf8') as f:
			json.dump(self.scraped_posts, f, indent=2, ensure_ascii=False)

	def get_post_elements(self):
		return self.driver.find_elements_by_css_selector('article')
	def get_first_element(self):
		return self.driver.find_element_by_css_selector('article')
	def get_final_element(self):
		try:
			return self.get_post_elements()[-1]
		except: # no element = after delete element
			return None
	def delete_elements(self):
		self.driver.execute_script("document.querySelectorAll('article').forEach(x => x.remove())")

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
	
	def get_date_from_elem(self, selenium_elem):
		metadata = selenium_elem.get_attribute('data-store') # selenium_elem = <article ...>...</article>
		try:
			postid = re.search(r'"post_id\\?":(\d+),', metadata).group(1)
			date = datetime.fromtimestamp(int(re.search(r'"publish_time\\?":(\d+),', metadata).group(1))) + timedelta(hours=-15)
			date = date.isoformat().replace('T',' ')
		except:
			postid, date = None, None
		return postid, date

	def get_article(self, soup):
		article = ''
		hashtags = []
		for p in soup.find_all('p'):
			for elem in p.children:
				if type(elem) == bs4.element.NavigableString:
					article += elem
				elif elem.name == 'br':
					article += '\n'
				elif elem.name == 'a':
					if ['_5ayv','_qdx'] == elem.attrs.get('class',[]):
						hashtags.append(elem.text)
					else:
						article += elem.text
				elif elem.name == 'span':
					if 'text_exposed_hide' in elem.attrs.get('class', []):
						continue
					elif 'text_exposed_show' in elem.attrs.get('class', []):
						for e in elem:
							if type(e) == bs4.element.NavigableString:
								article += e.lstrip()
							elif e.name == 'br':
								article += '\n'
							elif e.name == 'a':
								if ['_5ayv','_qdx'] == e.attrs.get('class',[]):
									hashtags.append(e.text)
								else:
									article += e.text
					else: # e.g. emoji
						try:
							article += elem.text
						except:
							pass
			article += '\n\n'
			article = re.sub('\n +', '\n', article).strip()
		if hashtags == []:
			hashtags = None
		return article, hashtags

	def get_images(self, soup):
		images = []
		try: 
			img_div = soup.select_one('._5rgu._7dc9._27x0')
			for img in img_div.select('img'):
				images.append(img.get('src'))
		except:
			pass
		return images

	def get_video(self, soup):
		try: 
			img_div = soup.select_one('._5rgu._7dc9._27x0')
			video_div = img_div.select_one('div[data-sigil="inlineVideo"]')
			return re.search(r'src":"(.+?)"', video_div.get('data-store')).group(1).replace('\\/','/')
		except:
			return None

	def get_reaction(self, soup):
		footer = str(soup.find('footer'))
		try:
			like = re.search(r'>(?:ถูกใจ |>)([\d,]+) (?:คน|Like)', footer).group(1)
		except:
			like = '0'
		try:
			comment = re.search(r'>(?:ความคิดเห็น |>)([\d,]+) (?:รายการ|comment)', footer).group(1)
		except:
			comment = '0'
		try:
			share = re.search(r'(?:แชร์ |>)([\d,]+) (?:ครั้ง|share)', footer).group(1)
		except:
			share = '0'
		return like, comment, share

	def get_one_post(self, selenium_elem):
		postid, date = self.get_date_from_elem(selenium_elem)
		soup = bs4.BeautifulSoup(selenium_elem.get_attribute('innerHTML'), 'html.parser')
		article, hashtags = self.get_article(soup)
		images = self.get_images(soup)
		video = self.get_video(soup)
		like, comment, share = self.get_reaction(soup)
		
		dic = {
			'date': date,
			'article': article,
			'url': f'https://www.facebook.com/{postid}',
			'hashtags': hashtags,
			'images': images,
			'video': video,
			'like': like,
			'comment': comment,
			'share': share
		}
		return dic

	def append_data(self):
		post_elems = self.get_post_elements()
		for post_elem in post_elems:
			if post_elem.id in self.scraped_ID:
				continue
			try:
				dic = self.get_one_post(post_elem)
				self.scraped_posts.append(dic)
				self.scraped_ID.add(post_elem.id)
			except Exception as e:
				traceback.print_exc()

	##### MAIN FUNCTION #####
	def scrape(self, filename='FBmobile.json', scroll=10):
		for _ in tqdm.tqdm(range(scroll)): # scroll n times
			self.scroll()
		time.sleep(2)
		self.append_data()
		self.delete_elements()
		self.write(filename) 