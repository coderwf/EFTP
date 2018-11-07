# -*- coding:utf-8 -*-
from core import session
from core.protocol import FieldLength,ReplyCodeDef,pack_host_port,unpack_host_port
from core.common import BYtesManager ,decimal_to_bc , bc_to_decimal
from core.protocol import OpCode
import os
import hashlib
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
        self.cwd                 =   os.getcwd() ###本地工作目录

    def close(self):
        if self.client_session :
            self.client_session.close()
            self.client_session = None
        if self.data_session :
            self.data_session.close()
            self.data_session   = None

    def _connect_ftp_server(self,host,port):
        if self.client_session :
            self.client_session.close()
            self.client_session   =  None
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
        return rep_code , message

    def ftp_pass(self,password):
        password = str(password)
        rep_code, message =  self.ftp_request(OpCode.PASS, password)
        return rep_code, message

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

    def ftp_cd(self,dir_name="."):
        self._check_none_(dir_name)
        rep_code , message = self.ftp_request(OpCode.CD,dir_name)
        print rep_code , message

    def ftp_mkd(self,dir_name):
        self._check_none_(dir_name)
        rep_code ,message  = self.ftp_request(OpCode.MKD,dir_name)
        print rep_code, message

    def ftp_rmd(self,dir_name):
        self._check_none_(dir_name)
        rep_code ,message = self.ftp_request(OpCode.RMD,dir_name)
        print rep_code , message

    def ftp_pasv(self):
        rep_code , message = self.ftp_request(OpCode.PASV)
        if rep_code != ReplyCodeDef.DATA_CONN_START :
            return rep_code , message
        ##----如果不是开始连接则表示服务器无法提供连接---直接返回错误码和错误信息
        ###关闭之前的data_session
        print rep_code , unpack_host_port(message)
        self.close_data_session()
        host , port = unpack_host_port(message) ##
        self.data_session = session.PortSession()
        self.data_session.connect(host,port,2000)
        ###确认数据连接
        if not self._ack_data_session_() :
            return ReplyCodeDef.DATA_CONN_FAILED , "Can't create Data connection."
        rep_code , message = self.receive_message()
        return rep_code , message

    def ftp_port(self):
        ######一共返回两次结果,第一次表示能否建立连接,第二次表示连接是否建立成功
        host, port = self._create_pasv_session_()
        if not host :
            raise IOError("Can't bind port")
        op_code , message = self.ftp_request(OpCode.PORT,pack_host_port(host,port))
        if op_code != ReplyCodeDef.DATA_CONN_START :
            return op_code , message
            ###如果服务器无法建立连接则直接返回
        try :
            ###服务器可以建立连接则开始接受服务器的连接
            self.data_session.accept(2000)
            ##连接成功开始确认连接
            self._ack_data_session_()
        except :
            pass
        ####接受服务器消息
        rep_code , message =  self.receive_message()
        return rep_code , message

    def _ack_data_session_(self):
        if not self.data_session :
            raise ValueError("data session is none.")
        try :
            self.data_session.send("1111111111", 2000)
            self.data_session.receive(10, 2000)
            return True   ###数据连接确认成功
        except Exception :
            self.close_data_session()
            return False ###数据连接失败

    def close_data_session(self):
        if self.data_session:
            self.data_session.close()
            self.data_session = None

    def clear_read_buffer(self):
        self.client_session.clear_read_buffer()
        ###清空缓冲区的内容

    def _create_pasv_session_(self):
        self.__check_connection__()
        try :
            host, _ = self.client_session.get_address()
        except :
            return None , None
        self.close_data_session()
        self.data_session = session.PasvSession()
        for port in range(7000,65525) :
            try :
                self.data_session.bind(host,port,2)
                return host,port
            except :
                pass
        return None,None

    def ftp_list(self,dir_name="."):
        self._check_none_(dir_name)
        op_code , message = self.ftp_request(OpCode.LIST,dir_name)
        if op_code != ReplyCodeDef.DATA_CONN_ACK :
            print op_code , message
            return
        ###确认连接
        self._ack_data_session_()
        rep_code , message = self.receive_message(2000)
        if rep_code != ReplyCodeDef.OK_OPERATION :
            self.close_data_session()
            print rep_code , message
            return
        file_list = self.data_session.receive_FD_msg(2000)
        print rep_code , message

    def ftp_put(self,file_path):
        self._check_none_(file_path)
        file_name  =  file_path.split(os.path.sep)[-1]
        file_size  =  os.stat(file_path).st_size
        try :
            f = open(file_path,"rb")
        except :
            return
        op_code , message = self.ftp_request(OpCode.PUT,decimal_to_bc(file_size,8)+file_name)
        if op_code != ReplyCodeDef.DATA_CONN_ACK :
            f.close()
            print op_code , message
            return
        ###------ check server -----
        if not self._ack_data_session_() :
            print self.receive_message(2000)
            return
        read_size   = 0
        m           = hashlib.md5()
        try :
            while read_size != file_size:
                stream = f.read(1024 * 1024)
                read_size += len(stream)
                m.update(stream)
                self.data_session.send_FD_msg(stream, ONE_MINUTE)
            f.close()
        except :
            self.close_data_session()
            print self.receive_message(2000)
            return
        try :
            self.data_session.send_FC_msg(m.hexdigest())
        except :
            self.close_data_session()
            print self.receive_message(2000)
            return
        print "transfer ok ."
        print self.receive_message(2000)
        return

    ###只能从工作目录中下载文件 target_dir是下载到哪个地方
    def ftp_get(self,file_name):
        self._check_none_(file_name)
        target_dir = os.path.abspath(os.path.join(self.cwd,file_name))
        if not os.path.exists(target_dir) or not os.path.isdir(target_dir) :
            raise ValueError("target_dir error , Check it.")
        target_file  = os.path.abspath(os.path.join(target_dir,file_name))
        try :
            f = open(target_file,"wb")
        except :
            return 0 , "can't open file {}".format(target_file)
        #--- check client file ----

        rep_code , message = self.ftp_request(OpCode.GET,file_name)
        ##-----check server auth or other -----
        if rep_code != ReplyCodeDef.DATA_CONN_ACK :
            f.close()
            print rep_code , message
            return
        file_size          = bc_to_decimal(message)
        if not self._ack_data_session_() :
            f.close()
            print self.receive_message(1000)
        read_size = 0
        m         = hashlib.md5()
        try :
            while read_size != file_size:
                stream = self.data_session.receive_FD_msg(ONE_MINUTE)
                m.update(stream)
                read_size += len(stream)
                f.write(stream)
            f.close()
        except :
            f.close()
            self.close_data_session()
            print self.receive_message(1000)
            return
        try :
            check_sum = self.data_session.receive_FD_msg(1000)
            print self.receive_message(1000)
            if check_sum != m.hexdigest() :
                self.remove_file(target_file)
                return
        except :
            self.close_data_session()
            print self.receive_message(1000)

    def remove_file(self,target_file):
        if os.path.exists(target_file) and os.path.isfile(target_file):
            import shutil
            shutil.rmtree(target_file)

    def _check_none_(self,name):
        if name == None :
            raise ValueError("name is none.")


    def local_list(self,dir_name="."):
        target_dir = os.path.abspath(os.path.join(self.cwd,dir_name))
        file_list = os.listdir(target_dir)
        for file in file_list :
            print file ,

    def local_cd(self,dir_name="."):
        target_dir = os.path.abspath(os.path.join(self.cwd, dir_name))
        if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
            print "bad operation."
            return
        self.cwd = target_dir

    def local_pwd(self):
        print self.cwd

    def local_mkd(self,dir_name):
        pass

    def local_rmd(self,dir_name):
        pass

def file_list_callback(file_list):
    file_list = eval(file_list)
    print ">>",
    for file in file_list :
        print file ,

def file_put_callback(file_size,read_size):
    print (read_size * 100.0) / file_size , "%"

if __name__ == "__main__":
    ftp_client = FtpClient("127.0.0.1",9999)
    ftp_client.local_list()
    ftp_client.local_cd("..")
    ftp_client.local_pwd()

