#!/usr/bin/env python
# -*- coding=utf-8 -*-
# python version 2.7.2
# 文件名:pixiv.py
# 输入P图址下载并按特定名字模式保存
# pixiv -h 查看帮助
# pixiv -v 查看名字模式
# ----------------------------------------------------------
# Author: xuhui
# WeiBo: http://weibo.com/asahui
# Version: 2012/7/13

#Problem
#2012.1.14
#  <script>!window.jQuery && document.write('<script src="http://source.pixiv.net/source/js/lib/jquery-1.7.1.min.js"></scr' + 'ipt>');</script>
#导致匹配出错
#修改getWeb函数，加入
#htmlcode = htmlcode.replace("</scr' + 'ipt>", '')
#去掉此影响

#Problem
#2012.3.26
# //<CDATA[\nif(typeof(adingoFluct) !="undefined") adingoFluct.showAd(\'1000003051\');\n//
#导致匹配出错
#修改getWeb函数，加入
#htmlcode = htmlcode.replace("//<![CDATA[", '')
#去掉此影响
#默认代理改用goagent代理

#Problem
#2012.7.13
# <a href="/{{#eq type "message"}}msgbox{{else}}notify_all{{/eq}}.php">
# <a href="{{#if approved}}{{#if from.type "novel"}}/novel/show.php?id={{else}}/member_illust.php?mode=medium&amp;illust_id={{/if}}{{from.id}}{{else}}/response.php?mode=chk{{/if}}">
#反正就是出现很多这种双引号中又有双引号，所以导致匹配出错的script
#修改getWeb函数，加入
#htmlcode = htmlcode.replace('type "novel"', '')
#htmlcode = htmlcode.replace('type "message"', '')
#去掉此影响

#Problem
#2012.8.10
#忘记登录时也要去掉一些数据影响
#修改login函数，加入
#htmlcode = htmlcode.replace("//<![CDATA[", '')
#htmlcode = htmlcode.replace('type "novel"', '')
#htmlcode = htmlcode.replace('type "message"', '')

#Problem
#2013.2.1
#修改loggin函数,加入
#htmlcode = htmlcode.replace('"{{tag_name}}"', '')
#修改getInfo函数,将匹配代码加入try except，一般匹配失败就停止，此时可能
#图片信息已经足够，如果不足够则下面使用会报错
#    try:
#            hp.feed(htmlcode.decode('utf-8'))
#            hp.close()
#    except HTMLParser.HTMLParseError as e:
#        print (u'匹配信息出错，估计是网页其干扰信息')

#Update
#2013.2.2
#加入getInfoByRegex函数，直接使用正则表达式取得图片信息
#将默认取图片信息改为用正则，加入-c
# --closeregex选项，用于关闭正则用回原来的HTMLPareser
#将login，getWeb函数里获取到网页后去除干扰的代码移到getInfo函数
#！全体代码格式更改，全部使用8个空格作为缩进


import urllib
import urllib2
import cookielib
import re
import os
import HTMLParser
from optparse import OptionParser

#程序使用的默认值，请自行修改
useproxy = False               #默认不使用代理，如果用-u选项开启则默认使用下面的proxy代理   
proxy = '127.0.0.1:8087'       #默认使用goagent代理，可以使用-p更改
#directory = 'd:\\PixivPic\\'   #默认路径
directory = '/home/xuhui/pictures/Pixiv/'
filename = '%i_%n／%a'         #默认名字模式
logindata={'mode':'login', 'pixiv_id':'yorkfinechan@gmail.com', 'pass':'cxhcxh'}    #R18图片需要登录，这里可默认设计登录账号与密码，就可以直接使用-l选项开启登录下载
sysenc = 'utf8'                 #系统默认编码，命令行默认编码


#2.7.2版本里面的已经可以匹配中文，但最好传unicode对象
#为了匹配如果pixiv网上如果读取了<div class="label"><label><input type="checkbox"{{if checked == 1}} checked{{/if}} onchange="pixiv.autoView.update(this.checked)">这样无聊错误代码（又不包含在注释中）加入一堆匹配符号
attrfind = re.compile(
    r'\s*([a-zA-Z_{1=][-.:a-zA-Z_0-9{}/]*)(\s*=\s*'
    r'(\'[^\']*\'|"[^"]*"|[^\s"\'=<>`]*))?')

#使用这个版本，解决<img src="http://abc1.com"width=10 />两个属性间没空格的问题，必须修改
#因为有时获取到pixiv网页里有javascript代码，代码里竟然有这'<scr' + 'ipt.....>'这样无聊的字符串连接，根源问题找到了，不用修改
#为了匹配如果pixiv网上如果读取了<div class="label"><label><input type="checkbox"{{if checked == 1}} checked{{/if}} onchange="pixiv.autoView.update(this.checked)">这样无聊错误代码（又不包含在注释中）
locatestarttagend = re.compile(r"""
  <[a-zA-Z][-.a-zA-Z0-9:_]*          # tag name
  (?:\s*                             # optional whitespace before
    (?:[a-zA-Z_{1][-.:a-zA-Z0-9_{}/]*# attribute name  # 为了匹配如果pixiv网上如果读取了无聊代码加入一堆匹配符号
      (?:\s*=\s*                     # value indicator
        (?:'[^']*'                   # LITA-enclosed value
          |\"[^\"]*\"                # LIT-enclosed value
          |[^'\">\s]+                # bare value
        )
       )?
       |(?:\"+)                     # 匹配pixiv网上如果读取了javascript但里面究竟有<span class="ads_desc style="display: inline-block"">这样的错误
       #根源问题找到了，不用修改
     )
   )*
  \s*                                # trailing whitespace
""", re.VERBOSE)



HTMLParser.locatestarttagend = locatestarttagend
HTMLParser.attrfind = attrfind
tagfind = re.compile('[a-zA-Z][-.a-zA-Z0-9:_]*')

class PixivHTMLParser(HTMLParser.HTMLParser):
        def __init__(self):
                HTMLParser.HTMLParser.__init__(self)
                self.attrs = []
                self.id = ''
                self.title = ''
                self.titleflag = 0

        # 重定义此函数
        # Internal -- handle starttag, return end or -1 if not terminated
        def parse_starttag(self, i):
                self.__starttag_text = None
                endpos = self.check_for_whole_start_tag(i)
                if endpos < 0:
                        return endpos
                rawdata = self.rawdata
                self.__starttag_text = rawdata[i:endpos]

                # Now parse the data between i+1 and j into a tag and attrs
                attrs = []
                match = tagfind.match(rawdata, i+1)
                assert match, 'unexpected call to parse_starttag()'
                k = match.end()
                self.lasttag = tag = rawdata[i+1:k].lower()

                while k < endpos:
                        m = attrfind.match(rawdata, k)
                        if not m:
                                break
                        attrname, rest, attrvalue = m.group(1, 2, 3)
                        if not rest:
                                attrvalue = None
                        elif attrvalue[:1] == '\'' == attrvalue[-1:] or \
                         attrvalue[:1] == '"' == attrvalue[-1:]:
                                attrvalue = attrvalue[1:-1]
                                attrvalue = self.unescape(attrvalue)
                        attrs.append((attrname.lower(), attrvalue))
                        k = m.end()

                end = rawdata[k:endpos].strip()
                if end not in (">", "/>"):
                        lineno, offset = self.getpos()
                        if "\n" in self.__starttag_text:
                                lineno = lineno + self.__starttag_text.count("\n")
                                offset = len(self.__starttag_text) \
                                 - self.__starttag_text.rfind("\n")
                        else:
                                offset = offset + len(self.__starttag_text)
                        self.error("junk characters in start tag: %r"
                               % (rawdata[k:endpos][:20],))
                if end.endswith('/>'):
                        # XHTML-style empty tag: <span attr="value" />
                        self.handle_startendtag(tag, attrs)
                else:
                        self.handle_starttag(tag, attrs)
                        # 你妹的，就是你这里突然将匹配模式换成interesting_cdata模式，导致网页里的javascript都被分析了
                        # 找你之前改了N多正则，最后一条无论如何改正则都不行，最后逼我全部源码看懂才找到根源的你
                        #if tag in self.CDATA_CONTENT_ELEMENTS:
                        #    self.set_cdata_mode()
                return endpos

        def handle_starttag(self, tag, attrs):
                if tag == "img":
                        #匹配例子<img src="http://img21.pixiv.net/img/s_f_nov17/20090818_m.jpg" alt="縁側/パセリ" title="縁側/パセリ" border="0" />
                        if len(attrs) < 1: pass
                        else:
                                for (variable, value)  in attrs:
                                        if variable == "src":
                                                if value.encode('gbk').find(self.id) != -1:
                                                        self.attrs = attrs

                if tag == 'title':
                        self.titleflag = 1

        def handle_data(self, data):
                if self.titleflag == 1:
                        self.title = data
                        self.titleflag = 0
                        #print data
                else: pass


def no_redirect(req, fp, code, msg, hdrs, newurl):
        return None
redirect_handler = urllib2.HTTPRedirectHandler()
redirect_handler.redirect_request=no_redirect

def login(addr, useproxy=False, proxyip='http://127.0.0.1:8087'):
        opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookielib.LWPCookieJar()))
        if useproxy:
                proxy_support = urllib2.ProxyHandler({'http':proxyip})
                opener.add_handler(proxy_support)
        data = urllib.urlencode(logindata)
        f = opener.open('http://www.pixiv.net/login.php', data)
        if f.read().find('pixiv.user.loggedIn = true') != -1:
                print u'登录成功'

                try:
                        f = opener.open(addr)
                except urllib2.URLError as e:
                        print (u'网络错误:' + e.reason.__str__())
                else:
                        print u'获取中'
                        htmlcode = f.read()
                        f.close()
                if htmlcode != None:
                        return htmlcode
        else:
                print u'登录失败'
                return None

def getWeb(addr, useproxy=False, proxyip='http://127.0.0.1:8087', opener=None):
        req = urllib2.Request(addr)
        req.add_header("Cookie", "pixiv_embed=pix")
        if not opener:
                opener = urllib2.build_opener(redirect_handler)
        htmlcode = None
        if useproxy:
                proxy_support = urllib2.ProxyHandler({'http':proxyip})
                opener.add_handler(proxy_support)
        try:
                f = opener.open(req)
        except urllib2.HTTPError as e:
                if e.code == 302:
                        print u'图片可能是R18，需登录，用-l选项或-s选项'
                if e.code == 404:
                        print u'无法链接到地址'
        except urllib2.URLError as e:
                print (u'网络错误:' + e.reason.__str__())
        else:
                print u'获取中'
                htmlcode = f.read()
                f.close()
        return htmlcode	

def getInfo(htmlcode, id):
        #使用HTMLPareser匹配信息，先去掉干扰
        htmlcode = htmlcode.replace("</scr' + 'ipt>", '')
        htmlcode = htmlcode.replace("//<![CDATA[", '')
        htmlcode = htmlcode.replace('type "novel"', '')
        htmlcode = htmlcode.replace('type "message"', '')
        htmlcode = htmlcode.replace('"{{tag_name}}"', '')

        hp = PixivHTMLParser()
        hp.id = id
        try:
                hp.feed(htmlcode.decode('utf-8'))
                hp.close()
        except HTMLParser.HTMLParseError as e:
                print (u'匹配信息出错，估计是网页其干扰信息')

        info = {}
        if len(hp.attrs) == 0 or len(hp.title) ==0 :
                print u'匹配图片信息失败1'
                return
        for (k, v) in hp.attrs:
                if k == 'src':
                        info['link'] = v.replace(id+'_m', id)
                        i = info['link'].find(id)+len(id)+1
                        info['type'] = info['link'][i:i+3]
                '''已经失效，title只存了图片名	
                if k == 'title':
                        info['name'] = v.split('/')[0]
                        info['artist'] = v.split('/')[1]
                '''
        m = re.match(u'.*?「([^」]*)」\s*/\s*「([^」]*)」.*', hp.title)
        if not m:
                print u'匹配图片名或作者名失败，请用-n，否则以ID号为名'
                print hp.title
                info['name'] = ''
                info['artist'] = ''
                info['nameerror'] = 'error'
                return info
        info['name'] = m.group(1)
        info['artist'] = m.group(2)
        if len(info['name']) == 0 or len(info['artist']) == 0 :
                print u'匹配图片名或作者名失败，请用-n，否则以ID号为名'
                info['name'] = ''
                info['artist'] = ''
                info['nameerror'] = 'error'
                return info
        print u'匹配图片信息成功'
        info['nameerror'] = 'none'
        return info

def getInfoByRegex(htmlcode, id):
        htmlcode = htmlcode.decode("utf-8")
        reTitle = r"<title>([^<]*)</title>"
        reImg = r"<img\s*src=\"([^\"]*?" + id + r".*?)\".*(?=/>)/>"

        title = re.search(reTitle, htmlcode)
        if not title:
                print u'匹配图片信息失败'
                return
        imgLink = re.search(reImg, htmlcode)
        if not imgLink:
                print u'匹配图片地址失败'
                return
        info = {}
        info['link'] = imgLink.group(1).replace(id+'_m', id)
        i = info['link'].find(id)+len(id)+1
        info['type'] = info['link'][i:i+3]

        m = re.match(u'.*?「([^」]*)」\s*/\s*「([^」]*)」.*', title.group(1))
        if not m:
                print u'匹配图片名或作者名失败，请用-n，否则以ID号为名'
                print title.group(1)
                info['name'] = ''
                info['artist'] = ''
                info['nameerror'] = 'error'
                return info
        info['name'] = m.group(1)
        info['artist'] = m.group(2)
        if len(info['name']) == 0 or len(info['artist']) == 0 :
                print u'匹配图片名或作者名失败，请用-n，否则以ID号为名'
                info['name'] = ''
                info['artist'] = ''
                info['nameerror'] = 'error'
                return info
        print u'匹配图片信息成功'
        info['nameerror'] = 'none'
        return info


# 这个方法不太成熟，不用了
def getManga(filename, id, useproxy, proxy):
        addr = 'http://www.pixiv.net/member_illust.php?mode=manga&illust_id='+id
        mangaPage = getWeb(addr, useproxy, proxy)
        if mangaPage != None:
                 print u'是漫画，请等"漫画下载完毕"出现，如果没有说明下载中途出现未知错误'
        print mangaPage
        p = re.compile("unshift\('.*?'\)")
        m = p.findall(mangaPage)
        if not m:
                filename = filename.decode('utf8')
                for picaddr in m:
                        pic = getWeb(picaddr, useproxy, proxy)
                        fn = ''
                        if pic != None:
                                fn = filename.replace(str(id), str(id)+'_p'+str(i))
                                try:
                                        f = open(fn, 'wb')
                                        f.write(pic)
                                except IOError:
                                        print u'写文件错误'
                                else:
                                        try:
                                                print (u'下载完成:'+fn) #print会自动调用fn.encode(sysenc)，可以测试到是否包含非系统编码字符，最终文件名还是Unicode编码保存
                                        except UnicodeEncodeError:
                                                print (u'下载完成:id='+str(id)+u'，图片名包含非系统编码字符，某些看图软件可能打不开')
                                        f.close()
                                        i = i+1
                        else:
                                print u'无法获取图片'



def getPic(addr, filename, useproxy, proxy, id):
        pic = getWeb(addr, useproxy, proxy)
        fn = ''
        if pic != None:
                fn = filename.decode('utf8')
                try:
                        f = open(fn, 'wb')
                        f.write(pic)
                except IOError:
                        print u'写文件错误'
                else:
                        try:
                                print (u'下载完成:'+fn) #print会自动调用fn.encode(sysenc)，可以测试到是否包含非系统编码字符，最终文件名还是Unicode编码保存
                        except UnicodeEncodeError:
                                print (u'下载完成:id='+str(id)+u'，图片名包含非系统编码字符，某些看图软件可能打不开')
                        f.close()
        else:
                print u'无法获取图片'
                print u'有可能漫画，尝试漫画模式'
                #getManga(filename, id, useproxy, proxy)
                s = addr
                pic = getWeb(s.replace(str(id), str(id)+'_p0'), useproxy, proxy)
                if pic != None:
                        print u'是漫画，请等"漫画下载完毕"出现，如果没有说明下载中途出现未知错误'
                        filename = filename.decode('utf8')
                        i = 0
                        while pic != None:
                                try:
                                        fn = filename.replace(str(id), str(id)+'_p'+str(i))
                                        f = open(fn, 'wb')
                                        f.write(pic)
                                except IOError:
                                        print u'写文件错误'
                                        break
                                else:
                                        try:
                                                print (u'下载完成:'+fn) #print会自动调用fn.encode(sysenc)，可以测试到是否包含非系统编码字符，最终文件名还是Unicode编码保存
                                        except UnicodeEncodeError:
                                                print (u'下载完成:id='+str(id)+'_p'+str(i)+u'，图片名包含非系统编码字符，某些看图软件可能打不开')
                                        f.close()
                                        i = i + 1
                                        pic = getWeb(s.replace(str(id), str(id)+'_p'+str(i)), useproxy, proxy)
                        print u'漫画下载完毕'
                else:
                        print u'非漫画，无法获取图片'


def main():
        global useproxy  
        global proxy
        global directory
        global filename
        usage = "usage: %prog [options]"    
        parser = OptionParser(usage)
        parser.add_option("-d", "--path", dest="path", help=u"保存图片路径")
        parser.add_option("-u", "--usedefaultproxy", action="store_true", dest="useproxy", help=u'使用默认代理')
        parser.add_option("-p", "--proxy", action="store", dest="proxy", help=u'使用代理，后面输入代理IP地址与端口，格式ip:port')
        parser.add_option("-l", "--login", action="store_true", dest="login", help=u'使用在源码写好的默认账号登录')
        parser.add_option("-s", "--signin", action="store", dest="signin", help=u'登录，后面参数格式 "登录号:密码"')
        parser.add_option("-n", "--name", action="store", dest="name", help=u'后面根据名字模式，使用-v选项打印名字名字模式')
        parser.add_option("-v", action="store_true", help=u'打印自定义名字模式帮助')
        parser.add_option("-c", "--closeregex", action="store_true",
                dest="closeregex",
                help=u'默认使用正则来搜索图片信息,此选项表示不用正则，使用HTMLParser来匹配图片信息')

        namepattern=ur"""
名字模式：
%i代表id号，%n代表图片名，%a代表作者名
可选与可自由组合,文件名有空格用引号
例子:id号是"20090818"，作者是"パセリ"，作品是"縁側"
          模式                保存文件名
    ---------------    -----------------------
    %i_%n_%a           20090818_縁側_パセリ
    %i_%n--20111001    20090818_20090818--縁側
    selfDefineName     selfDefineName
"""
        (options, args) = parser.parse_args()
        if len(args) > 0:
                parser.error(u"程序不需要参数")
        if options.v:
                print namepattern
                return

        if options.useproxy:
                useproxy = options.useproxy
        if options.proxy:
                useproxy = True
                proxy = options.proxy

        input = raw_input(u"输入Id或地址:".encode(sysenc))
        if input.strip().find('t.cn') != -1:            # 处理微博链接
                opener = urllib2.build_opener(redirect_handler)
                try:
                        f = opener.open(input)
                except urllib2.HTTPError as e:
                        if e.code == 302:
                                input = e.hdrs['Location']
                print u'真实地址：' + input
        p = re.compile('\d+$')
        m = p.search(input.strip())
        if not m:
                print u'可能不是正确的链接'
                return
        id = m.group()
        addr = 'http://www.pixiv.net/member_illust.php?mode=medium&illust_id='+id

        if options.signin:
                s = options.signin.strip()
                logindata['pixiv_id'] = s.split(':')[0]
                logindata['pass'] = s.split(':')[1]
                options.login = True
                
        if options.login:
                htmlcode = login(addr, useproxy, proxy)
        else:
                htmlcode = getWeb(addr, useproxy, proxy)
        if htmlcode != None:
                '''测试用，输出获取页面
                htmlout = open("htmlcode.txt", 'w')
                htmlout.write(htmlcode)
                htmlout.close()
                '''

                info={}
                if options.closeregex:
                        info = getInfo(htmlcode, id)
                else:
                        info = getInfoByRegex(htmlcode, id)
                if info:
                        if info['nameerror'] == 'error':
                                filename = '%i'
                        if options.name:
                                filename = options.name
                                filename = filename.decode(sysenc).encode('utf8')

                        filename = filename.replace('%i', id)
                        filename = filename.replace('%n', info['name'].encode('utf8'))
                        filename = filename.replace('%a', info['artist'].encode('utf8'))
                        filename = filename + '.' + info['type'].encode('utf8')


                        # 判断名字是否合法
                        if not re.match("[^\\s\\\\/:\\*\\?\\\"<>\\|](\\x20|[^\\s\\\\/:\\*\\?\\\"<>\\|])*[^\\s\\\\/:\\*\\?\\\"<>\\|\\.]$", filename):
                                try:
                                        print u'原图片名字'+filename.decode('utf8')
                                except UnicodeEncodeError:
                                        print (u'图片名字不合法且包含非系统编码字符，请使用-n选项更名，名字模式可用-v查看')
                                else:
                                        print u'图片名字不合法，请使用-n选项更名，名字模式可用-v查看'
                                return
                        if options.path:
                                directory = options.path
                                print u"保存至 %s" % options.path
                        if os.path.exists(directory) == False:
                                os.mkdir(directory)
                        print(u"图片源地址:"+info['link'])
                        getPic(info['link'], directory+filename, useproxy, proxy, id)


if __name__ == "__main__":
        main()
