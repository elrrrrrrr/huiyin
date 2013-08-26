#encoding=utf-8
import web
import math
import urllib
from config import setting
from model import user
from util import login as login_mod
from util import oauth

config = setting.config
render = setting.render
blankrender = setting.blankrender
db = setting.db

class base(object):
    def __init__(self):
        pass
    def GET(self):
        cur_user = login_mod.logged()
        self.cur_user = cur_user
        web.template.Template.globals['user'] = cur_user



class index(base):
    def GET(self):
        """ app index """
        super(index,self).GET()
        return render.index()

class new(base):
    def GET(self):
        """ write new piece """
        super(new,self).GET()
        return render.new()
    def POST(self):
        """ post the piece """
        super(new,self).GET()
        from model import piece
        from urlparse import urlparse

        post = web.input(_method="post",share=[])

        if self.cur_user:
            # cur_user
            cur_user = self.cur_user

            # user_id
            user_id = cur_user["id"]

            # link
            link = post["link"]
            url_parsed = urlparse(link)
            if not url_parsed.netloc:
                link = None

            # private
            if "private" in post:
                private = True
            else:
                private = False

            # content
            content = post["content"]

            # insert
            piece_id = piece.add(user_id=user_id,content=content,link=link,private=private)
            
            # share
            if not private:
                share = post["share"]
                share_content = u"「" + content + u"」" + " http://" + web.ctx.host + "/piece/" + str(piece_id)
                if "weibo" in share:
                    client = oauth.createClientWithName("weibo",cur_user)
                    client.post(share_content)

                if "douban" in share:
                    client = oauth.createClientWithName("douban",cur_user)
                    client.post(share_content)

            # redirect
            web.redirect("/people/"+str(user_id))
        else:
            return render.new()



class people(base):
    def GET(self,id):
        """ people """
        super(people,self).GET()

        per = 5
        try:
            page = int(web.input(page=1)["page"])
        except Exception:
            page = 1

        if page < 1:
            page = 1

        where = "fav.userid=user.id and fav.pieceid=piece.id and user.id=$id"
        vars = {"id":id}

        favs = db.select(["fav","piece","user"]
            ,what="avatar,piece.id,piece.content,fav.addtime"
            ,where=where
            ,vars=vars,limit=per
            ,offset=(page-1) * per
            ,order="addtime DESC")
        
        # mine = db.select(["piece","user"],what="piece.id,piece.content,piece.addtime",where="piece.user=user.id and user.id=$id",vars={"id":id},limit=5)
        rows = db.select(["user"],what="avatar,name,id",where="id=$id",vars={"id":id})

        if not rows:
            web.notfound()
            return "user not found"

        the_user = rows[0]
        if len(favs) == 0:
            favs = [{"content":"如果有收藏过喜欢的句子，他们会出现在这里。","id":None}]
        
        pages = db.select(["fav","piece","user"]
            ,what="COUNT(piece.id) as count"
            ,where=where
            ,vars=vars
        )[0]["count"]

        pages = math.ceil(float(pages)/per)
        pages = int(pages)

        return render.people(favs,the_user,pages,page)

class piece(base):
    def GET(self,id):
        """ piece """
        super(piece,self).GET()
        pieces = db.select("piece",what="id,content,link",where="id=$id",vars={"id":id})
        cur_user = self.cur_user
        cur_user_id = cur_user and cur_user["id"] or 0
        if not pieces:
            return web.notfound("oops")

        curpiece = pieces[0]

        favs = db.select(["fav","user"],what="avatar,user.id", where="fav.userid=user.id and fav.pieceid=$id and fav.userid<>$cur_user_id",vars={"id":id,"cur_user_id":cur_user_id}, limit=5)
        
        liked = False
        where = {"id":id}
        if cur_user:
            where["userid"] = self.cur_user.id;
        if cur_user and db.select("fav",what="id",where="fav.userid=$userid and pieceid=$id",vars=where):
            liked = True
        return render.piece(curpiece,favs,liked)

class logout:
    def GET(self):
        login_mod.logout()
        referer = web.ctx.env.get('HTTP_REFERER', '/')
        web.seeother(referer)

class login:
    def GET(self):
        input = web.input()
        if login_mod.logged():
            if "redirect" in input:
                web.redirect(urllib.unquote_plus(input["redirect"]))
            else:
                web.redirect("/")

        return blankrender.login()

class tools(base):
    def GET(self):
        return render.tools()

class about(base):
    def GET(self):
        return render.about()

class bookmarklet(base):
    def GET(self):
        super(bookmarklet,self).GET()
        input = web.input()
        url = input["url"]
        title = urllib.unquote(input["title"])
        data = {"url":url,"title":title}
        if len(url) > 36:
            shorturl = url[:36]+"..."
        else:
            shorturl = url

        data["shorturl"] = shorturl
        # return ctx.home + ctx.fullpath
        
        return blankrender.bookmarklet(data)

class auth_redirect:
    def GET(self,name):
        try:
            client = oauth.createClientWithName(name)
            url = client.redirect()
            web.seeother(url)
        except Exception,e:
            return e

class auth:
    def GET(self,name):
        input = web.input()
        new_user = None
        cur_user = login_mod.logged()
        try:
            client = oauth.createClientWithName(name)
            access_token = client.get_access_token(input["code"])
            user_info = client.get_current_user_info(access_token)

            user_info["access_token"] = access_token
            


            if cur_user:
                user.update_oauth_userid(name,cur_user["id"],user_info["id"])
                user.update_access_token(name,user_info["id"],access_token)
            if not cur_user:
                oauth_user = user.exist_oauth_user(name,user_info)
                if not oauth_user:
                    new_user = user.new_oauth_user(name,user_info)
                else:
                    user.update_access_token(name,oauth_user[name+"_id"],access_token)
                user.login_oauth_user(name,user_info)

            return blankrender.logged(True,new_user)
        except Exception:
            return blankrender.logged(True,None)
