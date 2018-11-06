
# -*- coding:utf-8 -*-
from ftpclient import FtpClient

#----------------------------------------------
SUPPORT_CMD = {"rmd":1,"cd":1,"pwd":0,"list":1,"get":1,"put":1,"user":1,"pass":1,"sys":0}






RemoteCmd = ("rmd","cd","pwd","list","get","put","user","pass","sys","mkd","quit")
LocalCmd  = ("lcd","lpwd","llist","lmkd","lrmd")
CmdAlias  = {"ls":"list","lls":"llist","mkdir":"mkd","lmkdir":"lmkd"}

#--------------------------------------------------------------
class CmdParser(object):
    def parse_cmd(self,cmd):
        cmd = cmd.strip(" ")  ##去掉头尾的空格
        params = cmd.split(" ") ##空格分离
        ###参数在1-2之间否则报错
        if len(params) <= 0 or len(params) > 2 :
            print len(params)
            raise ValueError("CMD {} invalid".format(cmd))
        ###去掉l后不在里面
        op  = params[0].lower()  #取第一个操作参数并且小写
        if op not in RemoteCmd and op not in LocalCmd and op not in CmdAlias :
            raise ValueError("CMD {} invalid".format(cmd))
        ####操作未实现
        if op in CmdAlias :
            op = CmdAlias.get(op)
            params[0] = op ###替换别名
        print params


class FtpCmd(object):
    def __init__(self,host,port):
        self.fc   = FtpClient(host,port,"ftp_cmd")
        self.cp   = CmdParser()

    def start_loop(self):
        while True :
            cmd = raw_input()
            self.cp.parse_cmd(cmd)

    def _list(self):
        pass

    def _llist(self):
        pass

    def _cd(self):
        pass

    def _lcd(self):
        pass

    def _pwd(self):
        pass

    def _lpwd(self):
        pass

    def _quit(self):
        pass

if __name__ == "__main__":
    # ftpCmd  = FtpCmd("127.0.0.1",9999)
    # ftpCmd.start_loop()
    FtpCmd("127.0.0.1",9999).start_loop()
