# -*- coding:utf-8 -*-
from core import session
from core.protocol import FieldLength,ReplyCodeDef,pack_host_port,unpack_host_port
from core.common import BYtesManager

#--------------------------------------------------------

class FtpClient(object):
    def __init__(self,host,port,client_name=""):
        self.client_session      =   session.PortSession()
        self.host                =   host
        self.port                =   port
        self.data_session        =   None
        self._bytes_manager      =   BYtesManager()
        self.client_name         =   client_name

    def close(self):
        if self.client_session :
            self.client_session.close()
            self.client_session = None
        if self.data_session :
            self.data_session.close()
            self.data_session   = None

    def __check_connection__(self):
        if self.client_session :
            return
        self.client_session = session.PortSession(self.client_name)
        for _ in (0,5):
            try :
                self.client_session.connect(self.host, self.port, timeout=3000)
                break
            except :
                pass
        raise IOError("can't connect to server .")

    def pack_op_code(self,op_code,params=""):
        op_code = int(op_code)
        self._bytes_manager.clear()
        self._bytes_manager.add_bytes_with_decimal(op_code,FieldLength.Operation_L)
        self._bytes_manager.add_bytes(params)
        return self._bytes_manager.consume_all()

    ###返回操作码
    def receive_message(self):
        message = self.client_session.receive_FC_msg(2000,1000)
        self._bytes_manager.reset(message)
        rep_code  = self._bytes_manager.consume_with_decimal(FieldLength.Control_REP_L)
        message   = self._bytes_manager.consume_all()
        return rep_code , message

    def ftp_request(self,op_code,params=""):
        self.__check_connection__()


    def ftp_user(self,user):
        pass

    def ftp_pass(self,password):
        pass

    def ftp_pwd(self):
        pass

    def ftp_cd(self,dir_name):
        pass

    def ftp_mkd(self,dir_name):
        pass


if __name__ == "__main__":
    ftp_client   =  FtpClient("127.0.0.1",9999)
    pass

