# -*- coding:utf-8 -*-
import socket
from core import session
from core.protocol import FieldLength , OpCode , ReplyCodeDef
from core.common import bc_to_decimal,decimal_to_bc,BYtesManager
import os
import platform

NeedPass = "Need login and pass first ."

#--------------------------------------------
class UserSession(object):
    def __init__(self,user_socket):
        self.user_socket         = user_socket
        self.user_session        = session.BaseSession(self.user_socket)
        self.closed              = False
        self.anonymous           = True
        self.authenticated       = False
        self.user_list           = {"user":"user"}
        self.cwd                 = os.getcwd()
        self.user                = None
        self._bytes_manager      = BYtesManager()

    def package_ctl_rep_code(self,code,message):
        code_msg             = decimal_to_bc(code,FieldLength.Control_REPL_CL)
        msg                  = code_msg + message
        msg_length_msg       = decimal_to_bc(len(msg),FieldLength.Control_MLL)
        return msg_length_msg + msg

    def receive_ctl_msg(self):
        msg_l            = self.user_session.receive(FieldLength.Control_MLL,timeout=1000*10*60)
        msg_length       = bc_to_decimal(msg_l)
        b_consumer       = BytesConsumer(self.user_session.receive(msg_length,1000*60))
        op_code          = b_consumer.consume_with_decimal(FieldLength.Operation_CL)
        return op_code , b_consumer

    def run(self):
        while True :
            op_code, b_consumer = self.receive_ctl_msg()
            op_explain = OpCode.get_def(op_code)
            self.__getattribute__("ftp_" + op_explain.lower())(b_consumer)

    def ftp_user(self,b_consumer):
        user = b_consumer.consume_all()
        if user not in self.user_list :
            reply = self.package_ctl_rep_code(ReplyCodeDef.NO_USER, "No user {} , check it.".format(user))
            self.user_session.send(reply)
            return
        reply = self.package_ctl_rep_code(ReplyCodeDef.USER_OK_NEED_PASS,"User okay , please pass.")
        self.user = user
        self.user_session.send(reply)
        return

    def ftp_pass(self,b_consumer):
        password    = self.user_list.get(self.user)
        i_password  = b_consumer.consume_all()
        if not password or password != i_password :
            reply   = self.package_ctl_rep_code(ReplyCodeDef.USER_OR_PASSWORD_ERR,"User or password error.")
        else :
            self.authenticated = True
            reply   = self.package_ctl_rep_code(ReplyCodeDef.USER_LOGIN,"User login successfully.")
        self.user_session.send(reply)
        return

    def ftp_pwd(self,b_consumer):
        if not self.anonymous and not self.authenticated :
            reply   = self.package_ctl_rep_code(ReplyCodeDef.NEED_PASS,NeedPass)
        else :
            reply   = self.package_ctl_rep_code(ReplyCodeDef.OK_OPERATION,self.cwd)
        self.user_session.send(reply)
        return

    def ftp_cd(self,b_consumer):
        if not self.anonymous and not self.authenticated:
            reply   = self.package_ctl_rep_code(ReplyCodeDef.NEED_PASS, NeedPass)
            self.user_session.send(reply)
            return
        #----------------"if loginin"------------------------
        dir_path   = b_consumer.consume_all()
        target_dir = os.path.abspath(os.path.join(self.cwd,dir_path))
        print target_dir
        if not os.path.exists(target_dir):
            reply = self.package_ctl_rep_code(ReplyCodeDef.FILE_OR_DIR_NOT_EXIST,"Directory or file {} "
                                                                                 "not exists.".format(target_dir))
        elif not os.path.isdir(target_dir):
            reply = self.package_ctl_rep_code(ReplyCodeDef.NOT_DIR,"{} is not a directory.")
        else :
            reply = self.package_ctl_rep_code(ReplyCodeDef.OK_OPERATION,"Directory changed successfully")
            self.cwd = target_dir
        self.user_session.send(reply)
        return


    def ftp_sys(self,b_consumer):
        if not self.anonymous and not self.authenticated:
            reply    = self.package_ctl_rep_code(ReplyCodeDef.NEED_PASS, NeedPass)
        else:
            sys_info = platform.system() + platform.release() + " ," + \
          platform.version() + ", "+platform.machine() + ", "+ platform.processor()
            reply    = self.package_ctl_rep_code(ReplyCodeDef.OK_OPERATION,sys_info)
        self.user_session.send(reply)
        return

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