
# -*- coding:utf-8 -*-
from ftpclient import FtpClient
from core.common import TimeoutError
import os
#----------------------------------------------
SUPPORT_CMD = {"rmd":1,"cd":1,"pwd":0,"list":1,"get":1,"put":1,"sys":0}

####有的login mode之类的交给用户自己实现 ,有的连接命令的失败会造成客户端关闭
RemoteCmd = ("rmd","cd","pwd","list","get","put","sys","mkd","quit","auth","mode")
LocalCmd  = ("lcd","lpwd","llist","lmkd","lrmd")
CmdAlias  = {"ls":"list","lls":"llist","mkdir":"mkd","lmkdir":"lmkd","store":"put"}
from core.protocol import ReplyCodeDef
NeedOneParam  = "{} need one param {}"

#--------------------------------------------------------------
class CmdParser(object):
    def parse_cmd(self,cmd):
        cmd = cmd.strip(" ")  ##去掉头尾的空格
        params = cmd.split(" ") ##空格分离
        valid_params = []
        for param in params :
            if not param :
                continue
            valid_params.append(param)  ##去除多余的空格
        ###参数在1-2之间否则报错
        if not valid_params :
            raise ValueError("CMD {} invalid".format(cmd))
        ###去掉l后不在里面
        op  = valid_params[0].lower()  #取第一个操作参数并且小写
        if op not in RemoteCmd and op not in LocalCmd and op not in CmdAlias :
            raise ValueError("CMD {} invalid".format(cmd))
        ####操作未实现
        if op in CmdAlias :
            op = CmdAlias.get(op)
            params[0] = op ###替换别名
        return op , valid_params[1:]  ##返回解析结果 (操作和参数)

PASSIVE_MODE          =  100
PORT_MODE             =  200

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

def _check_params_num(cmd,num,least,most):
    if num > most or num < least :
        raise ValueError("{} takes {} - {} params num".format(cmd,least,most))

#------------------------------------------------------------
class FtpCmd(object):
    def __init__(self):
        self.ftp_client         =  FtpClient("ftp_cmd")
        self.cmd_parser         =  CmdParser()
        self.stopped            =  False
        self.mode               =  None
        self.cwd                =  os.getcwd()

    def set_mode(self,mode):
        self.mode   =  mode

    def stop(self):
        self.stopped = True
        self.ftp_client.close()

    def start(self):
        host , port = self._input_host_()
        if not self.start_connect(host,port) :
            return ###不能连接服务器则结束
        self.cmd_loop()

    def cmd_loop(self):  ##循环解析用户输入的命令
        while not self.stopped:
            cmd = raw_input()
            try:
                op_, params = self.cmd_parser.parse_cmd(cmd)
            except ValueError , e:
                print e
                continue  ###命令解析错误则不需要继续往下解析
            ###print op_, params
            processor = self.__getattribute__("_" + op_)
            if processor == None:
                print "processor is none."
                continue  ####不继续执行
            try :
                processor(params)
            except TimeoutError as e :
                self.stop()
                return
            except ValueError , e :
                print e

    def start_connect(self,host,port):
        print "connecting server ..."
        try :
            self.ftp_client._connect_ftp_server(host,port)
            print "CONN OK."
            return True
        except :
            print "Can't connect to Server."
            return False

    ###until correct input format
    def _input_host_(self):
        while True :
            try:
                ftp_host = raw_input("host:")
                _check_none_(ftp_host)
                _check_host_(ftp_host)
                ftp_port = raw_input("port:")
                _check_none_(ftp_port)
                _check_port_(ftp_port)
                return ftp_host , int(ftp_port)
            except ValueError , e:
                print e

    def _mode(self,params):
        _check_params_num("Mode",len(params),1,1)
        param = params[0]
        if param.lower() != "pasv" and param.lower() != "port" :
            print "{} only pasv and port".format("Mode")
            return
        if param == "pasv" :
            rep_code , _ = self.ftp_client.ftp_pasv()           # passive mode
            if rep_code  == ReplyCodeDef.ENTER_PASSIVE_MODE :
                self.mode  = PASSIVE_MODE
            print rep_code , _
            return
        else :
            rep_code , _ = self.ftp_client.ftp_port()           # port mode
            if rep_code == ReplyCodeDef.ENTER_PORT_MODE :
                self.mode  =  PORT_MODE
            print rep_code , _
            return

    def _auth(self,params):
        _check_params_num("Auth",len(params),0,0)
        username  =  raw_input("username:")
        password  =  raw_input("password:")
        try :
            _check_none_(username)
            _check_none_(password)
        except ValueError , e:
            print e
            return
        rep_code , _ = self.ftp_client.ftp_user(username)
        if rep_code  != ReplyCodeDef.USER_OK :
            print _
            return
        rep_code , _ = self.ftp_client.ftp_pass(password)
        if rep_code  != ReplyCodeDef.LOGIN_OK :
            print _
            return
        print _
        return

    def _list(self,params):
        if not self.mode:
            print "Need a Mode first ."
            return
        _check_params_num("List",len(params),0,1)
        param  = "."
        if len(params) == 1 :
            param = params[0]
        rep_code , message = self.ftp_client.ftp_list(param)
        if rep_code != ReplyCodeDef.OK_OPERATION :
            print rep_code , message
            return
        file_list = eval(message)
        self.show_file_list(file_list)
        return

    def _mkd(self,params):
        _check_params_num("Mkd",len(params),1,1)
        rep_code , message =self.ftp_client.ftp_mkd(params[0])
        print message

    def _rmd(self,params):
        _check_params_num("Rmd",len(params),1,1)
        rep_code , message = self.ftp_client.ftp_rmd(params[0])
        return rep_code , message

    def _put(self,params):
        if not self.mode:
            print "Need a Mode first ."
            return
        _check_params_num("Put",len(params),1,1)
        rep_code , message = self.ftp_client.ftp_put(params[0])
        print message

    def _get(self,params):
        if not self.mode:
            print "Need a Mode first ."
            return
        _check_params_num("Get",len(params),1,1)
        rep_code , message = self.ftp_client.ftp_get(params[0])
        print message


    def _llist(self,params):
        _check_params_num("LList",len(params),0,1)
        param  = "."
        if len(params) == 1:
            param = params[0]
        rep_code , message = self.ftp_client.local_list(param)
        if rep_code == ReplyCodeDef.OK_OPERATION :
            print message
            return
        self.show_file_list(message)

    def _cd(self,params):
        _check_params_num("Cd",len(params),1,1)
        rep_code , message = self.ftp_client.ftp_cd(params[0])
        print message

    def _lcd(self,params):
        _check_params_num("LList",len(params),1,1)
        rep_code , message = self.ftp_client.local_cd(params[0])
        print message

    def _pwd(self,params):
        _check_params_num("Pwd",len(params),0,0)
        op_code , message = self.ftp_client.ftp_pwd()
        print message


    def _lpwd(self,params):
        _check_params_num("LPwd",len(params),0,0)
        rep_code , message = self.ftp_client.local_pwd()
        print message

    def _lrmd(self,params):
        _check_params_num("LPwd", len(params), 1, 1)
        rep_code, message = self.ftp_client.local_mkd(params[0])
        print message

    def _lmkd(self,params):
        _check_params_num("LPwd", len(params), 1, 1)
        rep_code , message = self.ftp_client.local_mkd(params[0])
        print message

    def _quit(self,params):
        _check_params_num("Quit",len(params),0,0)
        op_code , message = self.ftp_client.ftp_quit()
        print message
        self.stop()

    def show_file_list(self,file_list):
        if len(file_list) == 0:
            return
        file_list_str = ""
        file_lines    = []

        for fff in file_list :
            if len(fff) + len(file_list_str) > 60 :
                file_lines.append(file_list_str)
                file_list_str = ""
            file_list_str = file_list_str + fff + " "
        if file_list_str :
            file_lines.append(file_list_str)
        file_list_str = ""
        for i in range(0,len(file_lines)) :
            if i == len(file_lines) - 1 :
                file_list_str = file_list_str + file_lines[i]
            else :
                file_list_str = file_list_str + file_lines[i] + "\n"
        print file_list_str
        return

if __name__ == "__main__":
    # ftpCmd  = FtpCmd("127.0.0.1",9999)
    # ftp_host , ftp_port = ftpCmd._input_host_()
    # if ftpCmd.start_connect(ftp_host,ftp_port) :
    #    ftpCmd._auth_()
    FtpCmd().start()


