
# -*- coding:utf-8 -*-
from ftpclient import FtpClient

#----------------------------------------------
SUPPORT_CMD = {"rmd":1,"cd":1,"pwd":0,"list":1,"get":1,"put":1,"user":1,"pass":1,"sys":0}

RemoteCmd = ("rmd","cd","pwd","list","get","put","sys","mkd","quit")
LocalCmd  = ("lcd","lpwd","llist","lmkd","lrmd")
CmdAlias  = {"ls":"list","lls":"llist","mkdir":"mkd","lmkdir":"lmkd","store":"put"}
from core.protocol import ReplyCodeDef
#--------------------------------------------------------------
class CmdParser(object):
    def parse_cmd(self,cmd):
        cmd = cmd.strip(" ")  ##去掉头尾的空格
        params = cmd.split(" ") ##空格分离
        ###参数在1-2之间否则报错
        if len(params) <= 0 or len(params) > 2 :
            raise ValueError("CMD {} invalid".format(cmd))
        ###去掉l后不在里面
        op  = params[0].lower()  #取第一个操作参数并且小写
        if op not in RemoteCmd and op not in LocalCmd and op not in CmdAlias :
            raise ValueError("CMD {} invalid".format(cmd))
        ####操作未实现
        if op in CmdAlias :
            op = CmdAlias.get(op)
            params[0] = op ###替换别名
        return op , params[1:]  ##返回解析结果 操作和参数

PASSIVE_MODE          =  0
PORT_MODE             =  1

def _check_host_(host):
    params   = host.split(".")
    if len(params) != 4 :
        raise ValueError("host {} must like 0.0.0.0".format(host))
    for param in params :
        try :
            param = int(param)
        except :
            raise ValueError("{} in host must integer.".format(param))
        if param < 0 or param > 255 :
            raise ValueError("{} is out of range".format(param))


def _check_port_(port):
    try :
        port = int(port)
        if port <= 0 or port > 65535 :
            raise ValueError("port {} is out of range".format(port))
    except :
        raise ValueError("port {} is not integer.".format(port))

def _check_none_(param):
    if not param :
        raise ValueError("param is none.")
#------------------------------------------------------------
class FtpCmd(object):
    def __init__(self,host,port):
        self.ftp_client         =  FtpClient(host,port,"ftp_cmd")
        self.cmd_parser         =  CmdParser()
        self.stopped            =  False
        self.mode               =  PORT_MODE

    ###ftp_list列出服务器工作目录的文件列表
    def start_connect(self):
        self.ftp_client.ftp_list(".")

    def _auth_(self):   ####如果服务器需要登录则进行登录
        while True :
            try :
                username = raw_input("username:")
                _check_none_(username)
                password = raw_input("password:")
                _check_none_(password)
                break
            except ValueError as e :
                print e
        try :
            op_code , _ = self.ftp_client.ftp_user(username)
            if op_code  == ReplyCodeDef.NO_USER :
                print _
                return False
            op_code , _ = self.ftp_client.ftp_pass(password)
            print _
            if op_code  == ReplyCodeDef.LOGIN_OK :
                return True
            else :
                return False
        except :
            print "Can't connect to ftp server."
            return False

    def _connect_ftp_server_(self):
        while True :
            try:
                ftp_host = raw_input("host:")
                _check_none_(ftp_host)
                _check_host_(ftp_host)
                ftp_port = int(raw_input("port:"))
                _check_none_(ftp_port)
                _check_port_(ftp_port)
                break
            except ValueError , e:
                print e

    def cmd_loop(self):  ##循环解析用户输入的命令
        while not self.stopped :
            cmd = raw_input()
            try :
                op_, params = self.cmd_parser.parse_cmd(cmd)
            except ValueError :
                continue  ###命令解析错误则不需要继续往下解析
            print op_ , params
            processor = self.__getattribute__("_"+op_)
            if processor == None :
                print "processor is none."
                continue      ####不继续执行
            processor(params)

    def _list(self,params):
        print "i am list"

    def _llist(self,params):
        pass

    def _cd(self,params):
        pass

    def _lcd(self,params):
        pass

    def _pwd(self,params):
        pass

    def _lpwd(self,params):
        pass

    def _quit(self,params):
        pass

if __name__ == "__main__":
    ftpCmd  = FtpCmd("127.0.0.1",9999)
    ftpCmd._connect_ftp_server()
