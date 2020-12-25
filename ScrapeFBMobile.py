from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
import re, json, os, sys, tqdm, time, html, traceback, bs4, datetime

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
	
	def get_date_from_elem(self, selenium_elem):
		metadata = selenium_elem.get_attribute('data-store') # selenium_elem = <article ...>...</article>
		try:
			postid = re.search(r'"post_id\\?":(\d+),', metadata).group(1)
			date = datetime.datetime.fromtimestamp(int(re.search(r'"publish_time\\?":(\d+),', metadata).group(1))).isoformat().replace('T',' ')
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

	def get_one_post(self, selenium_elem):
		postid, date = self.get_date_from_elem(selenium_elem)
		soup = bs4.BeautifulSoup(selenium_elem.get_attribute('innerHTML'))
		article, hashtags = self.get_article(soup)
		images = self.get_images(soup)
		
		dic = {
			'date': date,
			'article': article,
			'url': f'https://www.facebook.com/{postid}',
			'hashtags': hashtags,
			'images': images
		}
		return dic