# -*- coding:utf-8 -*-
import socket
from core import session
from core.protocol import FieldLength , OpCode , ReplyCodeDef
from core.common import bc_to_decimal,decimal_to_bc,BYtesManager
import os
import platform


ONE_MINUTE           = 1000 * 60
TEN_MINUTE           = ONE_MINUTE * 10
ONE_HOUR             = 6 * TEN_MINUTE
TEN_SECOND           = 1000 * 10
#-------------------------------------------------------------------------#

NEED_AUTH            =  "Need LOGIN and PASS first ."
FILE_NOT_EXISTS      =  "File {} not exists."
DIR_NOT_EXISTS       =  "Directory {} not exists."
NOT_A_FILE           =  "{} Not a File."
NOT_A_DIR            =  "{} Not a Directory."

NO_PERMISSION        = "No Permission or Bad Name , Check it."

#-------------------------------------------------------------------------#
#-------------------------------------------------------------------------#

class UserSession(object):
    def __init__(self,user_socket):
        self.user_socket         =  user_socket
        self.user_session        =  session.ClientSession(self.user_socket)
        self.closed              =  True
        self.anonymous           =  False
        self.authenticated       =  False
        self.user_list           =  {"user":"user"}
        self.cwd                 =  os.getcwd()
        self.user                =  None
        self._bytes_manager      =  BYtesManager()
        self.data_session        =  None

    def send_reply(self,rep_code,params="",timeout=ONE_MINUTE):
        code_msg = decimal_to_bc(rep_code, FieldLength.Control_REP_L)
        msg = code_msg + params
        self.user_session.send_FC_msg(msg,timeout)

    def run(self):
        self.closed = False
        while not self.closed :
            try :
                message     = self.user_session.receive_FC_msg(TEN_MINUTE * 2)
                self._bytes_manager.reset(message)
                op_code     = self._bytes_manager.consume_with_decimal(FieldLength.Operation_L)
                op_explain  = OpCode.get_def(op_code)
                self.__getattribute__("ftp_" + op_explain.lower())()
            except :
                return

    def ftp_user(self):
        user = self._bytes_manager.consume_all()
        if not user or (user not in self.user_list ):
            if not user : user = ""
            self.send_reply(ReplyCodeDef.NO_USER,"Sorry,User {} not exists.".format(user))
        else :
            self.user = user
            self.send_reply(ReplyCodeDef.USER_OK,"User OKay,Please enter pass.")
        return

    def ftp_pass(self):
        h_password    = self.user_list.get(self.user)
        a_password    = self._bytes_manager.consume_all()
        if not h_password or (h_password != a_password) :
            self.send_reply(ReplyCodeDef.USER_OR_PASSWORD_ERR,"User or Password error,Check it.")
        else :
            self.authenticated = True
            self.send_reply(ReplyCodeDef.LOGIN_OK,"User Successfully Login.")
        return

    def ftp_quit(self):
        user = self.user if self.authenticated else ""
        self.send_reply(ReplyCodeDef.OK_OPERATION,"Bye Bye {}, Welcome next time.".format(user))
        self.close()
        return

    #检查权限
    def _check_auth_(self):
        if (not self.anonymous) and (not self.authenticated):
            self.send_reply(ReplyCodeDef.NEED_AUTH,NEED_AUTH)
            return False
        return True

    def ftp_pwd(self):
        if not self._check_auth_():
            return
        self.send_reply(ReplyCodeDef.OK_OPERATION,self.cwd)
        return

    def ftp_cd(self):
        if not self._check_auth_():
            return
        #----------------"auth check"------------------------
        dir_path      = self._bytes_manager.consume_all()
        target_dir    = os.path.abspath(os.path.join(self.cwd, dir_path))
        if not self._check_target_dir_(target_dir) :
            return #####文件夹不合法直接返回错误
        self.cwd      = target_dir  ##改变当前工作目录
        self.send_reply(ReplyCodeDef.OK_OPERATION,"Directory Successfully Changed.")
        return

    def ftp_mkd(self):
        if not self._check_auth_():
            return
        dir_name    = self._bytes_manager.consume_all()
        target_dir  = os.path.abspath(os.path.join(self.cwd, dir_name))
        if os.path.exists(target_dir):
            self.send_reply(ReplyCodeDef.BAD_OPERATION,"Directory {} already exists".format(target_dir))
            return
        try :
            os.makedirs(target_dir)
            self.send_reply(ReplyCodeDef.OK_OPERATION,"Directory {} Created.".format(target_dir))
            return
        except :
            self.send_reply(ReplyCodeDef.BAD_OPERATION,NO_PERMISSION)
            return

    def ftp_unknown(self):
        self._bytes_manager.consume_all()
        self.send_reply(ReplyCodeDef.UN_IMPLEMENT_CMD,"CMD UNKNOWN , Check it.")
        return

    def _check_target_dir_(self,dir_name):
        if not os.path.exists(dir_name) :
            self.send_reply(ReplyCodeDef.DIR_NOT_EXIST,DIR_NOT_EXISTS.format(dir_name))
            return False
        elif not os.path.isdir(dir_name):
            self.send_reply(ReplyCodeDef.NOT_DIR,NOT_A_DIR.format(dir_name))
            return False
        return True


    def _check_target_file(self,file_name):
        if not os.path.exists(file_name) :
            self.send_reply(ReplyCodeDef.FILE_NOT_EXIST,FILE_NOT_EXISTS.format(file_name))
            return False
        elif not os.path.isfile(file_name):
            self.send_reply(ReplyCodeDef.NOT_FILE,NOT_A_FILE.format(file_name))
            return False
        return True

    def ftp_sys(self):
        if not self._check_auth_():
            return
        sys_info = platform.system() + platform.release() + " ," + \
                   platform.version() + ", "+platform.machine() + ", "+ platform.processor()
        self.send_reply(ReplyCodeDef.OK_OPERATION,sys_info)
        return

    def close(self):
        self.closed = True

if __name__ == "__main__":
    server_socket = socket.socket()
    server_socket.bind(("127.0.0.1",9999))
    server_socket.listen(5)
    while True :
        client, address = server_socket.accept()
        try :
            UserSession(client).run()
        except :
            pass