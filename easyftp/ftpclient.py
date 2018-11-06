# -*- coding:utf-8 -*-
from core import session
from core.protocol import FieldLength,ReplyCodeDef,pack_host_port,unpack_host_port
from core.common import BYtesManager
from core.protocol import OpCode
#--------------------------------------------------------
ONE_MINUTE              =   1000  * 60
FIVE_MINUTE             =   5  * ONE_MINUTE
TEN_MINUTE              =   2  * FIVE_MINUTE
TWENTY_MINUTE           =   2  * TEN_MINUTE
ONE_HOUR                =   3  * TWENTY_MINUTE
ONE_DAY                 =   24 * ONE_HOUR




#----------------------------------------------------------
class FtpClient(object):
    def __init__(self,host,port,client_name=""):
        self.client_session      =   None
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
        self.client_session = session.PortSession()
        ####try for five times or throws excepton
        for _ in range(0,5):
            try :
                self.client_session.connect(self.host,self.port)
                return
            except Exception :
                pass
        raise IOError("can't connect to server .")
    #简化操作
    def pack_op_code(self,op_code,params=""):
        op_code = int(op_code)
        self._bytes_manager.clear()
        self._bytes_manager.add_bytes_with_decimal(op_code,FieldLength.Operation_L)
        self._bytes_manager.add_bytes(params)
        return self._bytes_manager.consume_all()

    ###简化请求的操作
    def ftp_request(self,op_code,params="",timeout=2000):
        self.__check_connection__()
        msg     = self.pack_op_code(op_code,params)
        self.client_session.send_FC_msg(msg,timeout)
        return self.receive_message(timeout)

    ###返回操作码 ###默认2s延迟否则超时异常
    def receive_message(self,timeout=2000):
        message = self.client_session.receive_FC_msg(timeout)
        self._bytes_manager.reset(message)
        rep_code  = self._bytes_manager.consume_with_decimal(FieldLength.Control_REP_L)
        message   = self._bytes_manager.consume_all()
        return rep_code , message

    def ftp_user(self,user):
        user = str(user)
        rep_code, message = self.ftp_request(OpCode.USER,user)
        print rep_code , message

    def ftp_pass(self,password):
        password = str(password)
        rep_code, message =  self.ftp_request(OpCode.PASS, password)
        print rep_code, message

    def ftp_sys(self):
        rep_code , message = self.ftp_request(OpCode.SYS)
        print rep_code , message

    def ftp_quit(self):
        self.ftp_request(OpCode.QUIT)
        op_code , message  = self.receive_message()
        print op_code , message

    def ftp_pwd(self):
        rep_code , message = self.ftp_request(OpCode.PWD)
        print rep_code, message

    def ftp_cd(self,dir_name):
        if dir_name == None :
            raise ValueError("dir_name is none")
        rep_code , message = self.ftp_request(OpCode.CD,dir_name)
        print rep_code , message

    def ftp_mkd(self,dir_name):
        pass


if __name__ == "__main__":
    ftp_client   =  FtpClient("127.0.0.1",9999)
    ftp_client.ftp_user("user")
    ftp_client.ftp_pass("user")
    ftp_client.ftp_sys()
    ftp_client.ftp_pwd()
    ftp_client.ftp_cd("c:/df")
    ftp_client.ftp_pwd()


