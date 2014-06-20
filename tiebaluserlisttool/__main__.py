#!/usr/bin/python
#encoding=UTF-8
#  
#  Copyright 2014 MopperWhite <mopperwhite@gmail.com>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#  
#  

from BeautifulSoup import BeautifulSoup
import urllib,urllib2,os,re,time,yaml,sys,locale,traceback,socket,cmd,sys
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
		self.file_path="culcache/"+ba_name.encode(sys.getfilesystemencoding())+"_cache.xml"
		self.load()
	def new(self):
		root=ET.Element("ba_data")
		root.set("last_page","1")
		tree=ET.ElementTree(root)
		tree.write(open(self.file_path,'w'))
	def load(self):
		if not os.path.exists(self.file_path):self.new()
		self.tree=ET.parse(self.file_path)
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
		path="culcache/"+self.ba_name.encode(sys.getfilesystemencoding())+".yaml"
		page_list_to_yaml(self.to_list(),open(path,'w'))
	def save(self):
		self.tree.write(open(self.file_path,"w"))
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

def pull_ba(ba_name):
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
				break
				
def cmd_str_to_unicode(s):
	return s.decode(locale.getdefaultlocale()[1])


class Cmd(cmd.Cmd):
		prompt="<tult cmd>:"
		def preloop(self):
			print u'''欢迎使用贴吧用户列表抓取工具1.0
出现问题请联系MopperWhite<mopperwhite@gmail.com>
输入help查看所有命令
输入exit或使用Ctrl+D退出
本程序使用GPL许可证发布
'''
		def default(self,line):
			print u'无效命令：',line
			print u'输入 help 获取帮助'
			
			
		def do_pull(self,ba_name):
			pull_ba(cmd_str_to_unicode(ba_name))
			print u"抓取完成."
		def help_pull(self):
			print u'''抓取贴吧用户列表
			pull 用户名'''
			
		def do_cmp(self,line):
			args=line.split()
			if len(args)<3:
				print u'"cmp"命令至少接受三个参数'
				return
			func={
				"^":lambda a,b:a^b,
				"|":lambda a,b:a|b,
				"&":lambda a,b:a&b,
				"-":lambda a,b:a-b
			}.get(args[0])
			if not func:
				print u"无效的运算符."
				return
			ba_name_list=[cmd_str_to_unicode(ba_name) for ba_name in args[1:]]
			try:
				ba_list=[
					set( item["name"] for item in yaml.load(open("culcache/"+ba_name+".yaml")))
					for ba_name in ba_name_list
				]
			except:
				traceback.print_exc()
				print u"获取贴吧信息失败，请确保输入的吧名已被抓取."
				return
				
			result=reduce(func,ba_list)
			for i in result:
				print i
			print u'总数:',len(result)
			return 
			
		def help_cmp(self):
			print u'''比较各吧用户			
	取并集
		cmp | 吧名1 吧名2
	取交集
		cmp & 吧名1 吧名2
	取差集（相对补集）
		cmp - 吧名1 吧名2
	取对称差集
		cmp ^ 吧名1 吧名2'''
			
		def do_get(self,line):
			args=cmd_str_to_unicode(line).split()
			if len(args)!=2:
				print u'参数错误.'
				return
			ba_name,username=args
			ba_path="culcache/"+ba_name+".yaml"
			if not os.path.exists(ba_path):
				print ba_name,u'吧尚未被抓取.'
				return 
			ul=[u for u in yaml.load(open(ba_path)) if u["name"]==username]
			if not ul:
				print u'用户未找到.'
				return
			for user in ul:
				print u"用户名:",user["name"]
				print u"排名:",user["index"]
				print u"等级:",user["title"]
				print u"经验值:",user["exp"]
			print u"位于", ba_name,u"吧"
		def help_get(self):
			print u'''取得用户信息
	get 吧名 用户名'''
			
		def do_list(self,ba_name):
			ba_name=cmd_str_to_unicode(ba_name)
			ba_path="culcache/"+ba_name+".yaml"
			if not os.path.exists(ba_path):
				print ba_name,u'吧尚未被抓取.'
				return
			ul=[item["name"] for item in yaml.load(open(ba_path))] 
			for i in ul:
				print i
			print u"总数:",len(ul)
		def help_list(self):
			print u'''列出贴吧所有用户
	list 贴吧名'''
		def do_exit(self,arg):
			sys.exit()
		def help_exit(self):
			print u'退出.也可使用Ctrl+D.'
		def do_EOF(self,a):
			print
			sys.exit()
			return True
		def help_EOF(self):print u'退出.'
if __name__=='__main__':	
	if not os.path.exists("culcache"):
		os.mkdir("culcache")
	c=Cmd()
	c.cmdloop()
