#!/usr/bin/python
#encoding=UTF-8
from BeautifulSoup import BeautifulSoup
import urllib,urllib2,os,re,time,yaml,sys,locale,traceback,socket
from xml.etree import ElementTree as ET
REQ_HEADER= {'User-Agent':'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
			 'Accept':'text/html;q=0.9,*/*;q=0.8',
			 'Accept-Charset':'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
#			 'Accept-Encoding':'gzip',
			 'Connection':'close',
			 'Referer':None,
			 }
TIME_OUT=20
PAUSE_TIME=3
RETRY_TIME=20

class XmlBaList(object):
	def __init__(self,ba_name):
		self.ba_name=ba_name
		self.file_path=ba_name.encode(sys.getfilesystemencoding())+"_cache.xml"
		self.load()
	def new(self):
		root=ET.Element("ba_data")
		root.set("last_page","1")
		tree=ET.ElementTree(root)
		tree.write(open("culcache/"+self.file_path,'w'))
	def load(self):
		if not os.path.exists(self.file_path):self.new()
		self.tree=ET.parse("culcache/"+self.file_path)
		self.root=self.tree.getroot()
		object.__setattr__(self,"last_page",int(self.root.get("last_page")))
	def addPage(self,page_list,p):
		if p>self.last_page:
			self.last_page=p
		old_element=self.root.find("page[@p='%d']"%p)
		if old_element:
			self.root.remove(old_element)
		page=ET.SubElement(self.root,"page")
		page.set("p",str(p))
		for i in page_list:
			item=ET.SubElement(page,"user")
			item.text=i["name"]
			for j in ["index","title","exp"]:
				item.set(j,str(i[j]))
		self.save()
	def to_list(self):
		return [dict(name=i.text,title=int(i.get("title")),index=int(i.get("index")),exp=int(i.get("exp"))) 
				for i in self.root.findall("./page/user")]
	def save_as_yaml(self):
		path=self.ba_name.encode(sys.getfilesystemencoding())+".yaml"
		page_list_to_yaml(self.to_list(),open("culcache/"+path,'w'))
	def save(self):
		self.tree.write(open("culcache/"+self.file_path,"w"))
	def __setattr__(self,var,val):
		if var=="last_page":
			self.root.set(var,str(val))
		else:
			object.__setattr__(self,var,val)
	def __getattribute__(self,var):
		if var=='last_page':
			return int(self.root.get(var))
		else:return object.__getattribute__(self,var)
def open_url(url):
	req = urllib2.Request(url,None,REQ_HEADER)
	return urllib2.urlopen(req,None,TIME_OUT)

def init():
	if not os.path.isdir("cul_data"):
		os.mkdir("cul_data")
def get_item_soup(item_soup):
	index=int(item_soup.td.p.text)
	name=item_soup.findChild("td",{"class":"drl_item_name"}).div.a.text
	title=int(re.search(r"bg_lv(\d{1,2})",dict(item_soup.findChild("td",{"class":"drl_item_title"}).find("div").attrs)["class"]).group(1))
	exp=int(item_soup.findChild("td",{"class":"drl_item_exp"}).find("span").text)
	return {
			"index":index,
			"name":name,
			"title":title,
			"exp":exp,
			}

def get_page_soup(page_data):
	root_soup=BeautifulSoup(page_data)
	return [get_item_soup(item_soup) for item_soup in root_soup.findAll("tr",{"class":"drl_list_item"})]

def get_list_page(ba_name,p):
	url="http://tieba.baidu.com/f/like/furank?kw=%s&ie=UTF-8&pn=%d"%(urllib.quote(ba_name.encode("UTF-8")),p)
	return get_page_soup(open_url(url).read().decode("gbk",'ignore'))
def get_ba_list(ba_name):
	list_=[]
	def get_page_(p):
		try:
			sub_list=get_list_page(ba_name,p)
			print type(sub_list)
			if sub_list:
				print "page:",p
				print "users:"," , ".join(i["name"] for i in sub_list)
				print
			else:
				print "[done]",ba_name
				return sub_list
		except urllib2.URLError as error:
			print "Urlopen Error (p%d):"%p,error
			return None
		except socket.timeout as error:
			print "Time out (p%d)."%p
			return None
			

	p_=1
	while True:
		sub_list=get_page_(p_)
		while sub_list is None:
			time.sleep(20)
			sub_list=get_page_(p_)
		if sub_list:
			list_.extend(sub_list)
			p_+=1
			time.sleep(PAUSE_TIME)
		else:return list_



def page_list_to_yaml(page_list,file_):
	yaml.safe_dump(page_list,file_,default_flow_style=False,allow_unicode=True)

if __name__=="__main__":
	ba_name=raw_input(u"吧名:".encode(locale.getdefaultlocale()[1])).decode(locale.getdefaultlocale()[1])
	xbl=XmlBaList(ba_name)
	def get_page_(p):
		try:
			sub_list=get_list_page(ba_name,p)
			if sub_list:
				print "page:",p
				print "users:"," , ".join(i["name"] for i in sub_list)
				print
			else:
				print ba_name,"...[done]"
			return sub_list
		except urllib2.URLError as error:
			print "Urlopen Error (p%d):"%p,error
			return None
		except socket.timeout as error:
			print "Time out (p%d)."%p
			return None

	p_=xbl.last_page
	while True:
		if not os.path.exists("culcache"):
			os.mkdir("culcache")

		sub_list=get_page_(p_)
		while sub_list is None:
			print "Retry in %ds"%RETRY_TIME
			time.sleep(RETRY_TIME)
			print "Restart now."
			sub_list=get_page_(p_)
		if sub_list:
			xbl.addPage(sub_list,p_)
			p_+=1
			time.sleep(PAUSE_TIME)
		else:
			xbl.save_as_yaml()
			exit()