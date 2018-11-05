# -*- coding:utf-8 -*-
from core import session
from core.protocol import *
from core.common import *

#--------------------------------------------------------

class FtpClient(object):
    def __init__(self,host,port):
        self.client_session   =   session.PortSession()
        self.closed           =   True
        self.host             =   host
        self.port             =   port

    def close(self):
        if not self.closed :
            self.closed         = True
            self.client_session.close()
            self.client_session = None

    def __check_connection__(self):
        if not self.closed or not self.client_session:
            return
        self.client_session = session.PortSession()
        self.client_session.connect(self.host,self.port,timeout=5000)
        self.closed   = False

    def package_opcode(self,op_code,params=""):
        code_msg = decimal_to_bc(op_code,FieldLength.Operation_CL)
        message = code_msg + params
        msg_l    = decimal_to_bc(len(message),FieldLength.Control_MLL)
        return msg_l + message

    def receive_message(self):
        length    = self.client_session.receive_with_decimal(FieldLength.Control_MLL,1000*5)
        b_consumer =  BytesConsumer(self.client_session.receive(length,1000*10))
        op_code    = b_consumer.consume_with_decimal(FieldLength.Control_REPL_CL)
        message   = b_consumer.consume_all()
        return op_code , message

    def ftp_pwd(self):
        msg = self.package_opcode(OpCode.PWD)
        self.client_session.send(msg)
        op_code , message = self.receive_message()
        print op_code , message

    def ftp_cd(self,dir_path):
        self.__check_connection__()
        msg = self.package_opcode(OpCode.CD,dir_path)
        self.client_session.send(msg)
        op_code , message = self.receive_message()
        print op_code , message

    def ftp_sys(self):
        self.__check_connection__()
        msg = self.package_opcode(OpCode.SYS)
        self.client_session.send(msg)
        op_code , message = self.receive_message()
        print op_code , message

    def ftp_mkd(self):
        pass

    def ftp_list(self):
        pass

    def ftp_user(self,user,timeout=None):
        self.__check_connection__()
        msg = self.package_opcode(OpCode.USER,user)
        self.client_session.send(msg,timeout)
        op_code, message = self.receive_message()
        print op_code , message

    def ftp_pass(self,password,timeout=None):
        self.__check_connection__()
        msg  = self.package_opcode(OpCode.PASS,password)
        self.client_session.send(msg,timeout)
        op_code , message = self.receive_message()
        print op_code , message

    def ftp_pasv(self):
        pass

    def ftp_port(self):
        pass


if __name__ == "__main__":
    ftp_client   =  FtpClient("127.0.0.1",9999)
    ftp_client.ftp_sys()

