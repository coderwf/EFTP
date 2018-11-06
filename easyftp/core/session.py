
# -*- coding:utf-8 -*-

"""
封装socket便于收发数据
"""

import  socket
import errno
from common import TimeChecker , bc_to_decimal , decimal_to_bc , BYtesManager
from protocol import FieldLength
import time
#----------------------------------------------------------
"""
基础的封装socket的session
"""

"""
通过规定的格式和各种session可以很容易的实现一个比较稳定的通信包

#--------------SERVER------------------------------------
def echo_back(s,msg):
    s.send_P_msg(2, msg)

def start_server(host,port,callback,timeout=0):
    s = PasvSession()
    s.bind_and_accept(host,port,2,timeout)
    while True :
        msg = s.receive_P_msg(2)
        callback(s,msg)
#---------------CLIENT-------------------------------------
p = PortSession()
p.connect("127.0.0.1",8888)
while True :
    p.send_P_msg(2,"Hi , baby !")
    print p.receive_P_msg(2)
"""
#-----------------------------------------------------------
class BaseSession(object):   # 2M 10M
    def __init__(self,session_name="",read_chunk_size=1024*1024*2,
                 max_read_buffer_size=1024*1024*10):
        self.data_socket                = None
        self._read_buffer               = ""
        self.max_read_buffer_size       = max_read_buffer_size
        self.read_chunk_size            = read_chunk_size
        self.session_name               = session_name

    def read_buffer_size(self):
        return len(self._read_buffer)

    def clear_read_buffer(self):
        self._read_buffer = ""

    def read_buffer_empty(self):
        return len(self._read_buffer) == 0

    def set_session_name(self,session_name):
        self.session_name = session_name

    def get_address(self):
        if not self.data_socket :
            raise ValueError("session {} data socket is none.".format(self.session_name))
        address = self.data_socket.getsockname()
        return address[0] , int(address[1])

    def send(self,data,timeout=0):
        data  = str(data)
        if not self.data_socket :
            raise ValueError("session {} data socket is none".format(self.session_name))
        t_checker = TimeChecker(timeout,"session {} send data".format(self.session_name))
        while data :
            try :
                res  = self.data_socket.send(data)
                data = data[res:]
            except socket.error , e :
                if e[0] in (errno.EAGAIN, errno.EWOULDBLOCK):
                    t_checker.check_timeout()
                    continue
                raise

    def receive(self,bytes_num,timeout=0):
        if not self.data_socket :
            raise ValueError("session {} data socket is none".format(self.session_name))
        t_checker  = TimeChecker(timeout,"session {} receive data".format(self.session_name))
        while len(self._read_buffer) < bytes_num :
            try :
                self.data_socket.setblocking(False)
                chunk = self.data_socket.recv(self.read_chunk_size)
                #print len(chunk)
                ###print "chunk>>>>",chunk
                #print "chunk>>>",chunk
            except socket.error, e:
                if e[0] in (errno.EAGAIN, errno.EWOULDBLOCK):
                    t_checker.check_timeout()
                    continue
                raise
            if not chunk:
                raise IOError("session {} read chunk is none".format(self.session_name))
            self._read_buffer += chunk
            print "buffer size",len(self._read_buffer)
            #为了避免此处超时,再给一次机会检查
            if len(self._read_buffer) >= bytes_num:
                break
            t_checker.check_timeout()
        return self._consume_(bytes_num)

    def _consume_(self,bytes_num):
        if len(self._read_buffer) < bytes_num :
            raise IOError("{} can't consume bytes {}".format(self.session_name,bytes))
        res                 = self._read_buffer[:bytes_num]
        self._read_buffer   = self._read_buffer[bytes_num:]
        return res

    def close(self):
        if self.data_socket :
            self.data_socket.close()
            self.data_socket = None


class FtpBaseSession(BaseSession):
    def __init__(self,session_name=""):
        BaseSession.__init__(self,session_name)

    def receive_with_decimal(self,bytes_num,timeout=0):
        msg = self.receive(bytes_num,timeout)
        return bc_to_decimal(msg)

    def receive_P_msg(self,MLL,timeout=0):
        start_time    =  time.time() * 1000
        msg_length = self.receive_with_decimal(MLL,timeout)
        if timeout == 0 :
            return self.receive(msg_length)
        else :
            time_used = time.time() * 1000 - start_time
            time_rest = max(200,timeout - time_used)
            print "time_rest",time_rest
            return self.receive(msg_length,time_rest)

    def send_P_msg(self,MLL,message,timeout=0):
        message           = str(message)
        msg_length        = len(message)
        msg_length_msg    = decimal_to_bc(msg_length,MLL)
        msg               = msg_length_msg + message
        self.send(msg,timeout)

    def receive_FC_msg(self,timeout=0):
        return self.receive_P_msg(FieldLength.Control_MLL,timeout)

    def receive_FD_msg(self,timeout=0):
        return self.receive_P_msg(FieldLength.Data_MLL,timeout)

    def send_FC_msg(self,message,timeout=0):
        self.send_P_msg(FieldLength.Control_MLL,message,timeout)

    def send_FD_msg(self,message,timeout=0):
        self.send_P_msg(FieldLength.Data_MLL,message,timeout)

    def receive_with_bytes_manager(self,bytes_num,timeout=0):
        message = self.receive(bytes_num,timeout)
        return BYtesManager(message)

class ClientSession(FtpBaseSession):
    def __init__(self,data_socket,session_name=""):
        FtpBaseSession.__init__(self,session_name)
        self.data_socket = data_socket
        self.data_socket.setblocking(False)

class PasvSession(FtpBaseSession):
    def __init__(self,session_name=""):
        FtpBaseSession.__init__(self,session_name)
        self.acc_socket       = None
        self.bind_host        = None
        self.bind_port        = None

    def close_acc_socket(self):
        if self.acc_socket :
            self.acc_socket.close()
            self.acc_socket   = None

    def close_data_socket(self):
        if self.data_socket :
            self.data_socket.close()
            self.data_socket  = None

    def close(self):
        self.close_acc_socket()
        self.close_data_socket()

    def bind(self,bind_host,bind_port,backlog=2):
        if self.acc_socket :
            self.acc_socket.close()
            self.acc_socket = None
        self.acc_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.acc_socket.bind((bind_host,bind_port))
        self.acc_socket.setblocking(False)
        self.acc_socket.listen(backlog)
        self.bind_host  = bind_host
        self.bind_port  = bind_port

    def accept(self,timeout=0):
        if not self.acc_socket :
            raise ValueError("session {} acc socket is none".format(self.session_name))
        t_checker  = TimeChecker(timeout)
        while True :
            try :
                client , address = self.acc_socket.accept()
                self.data_socket = client
                self.data_socket.setblocking(False)
                break
            except socket.error , e :
                if e[0] in (errno.EWOULDBLOCK,errno.EAGAIN):
                    t_checker.check_timeout()
                    continue
                raise

    def bind_and_accept(self,bind_host,bind_port,backlog=2,timeout=0):
        self.bind(bind_host,bind_port,backlog)
        self.accept(timeout)

class PortSession(FtpBaseSession):
    def __init__(self,host=None,port=None,session_name=""):
        FtpBaseSession.__init__(self,session_name)
        self.host    = host
        self.port    = port

    def connect(self,host,port,timeout=0):
        if self.data_socket :
            self.data_socket.close()
            self.data_socket  = None
        self.data_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        t_checker = TimeChecker(timeout)
        while True :
            try :
                self.data_socket.connect((host,port))
                self.data_socket.setblocking(False)
                break
            except socket.error, e:
                if e[0] in (errno.EWOULDBLOCK, errno.EAGAIN):
                    t_checker.check_timeout()
                    continue
                raise

    def start_connect(self,timeout=0):
        if (not self.host) and (not self.port):
            raise ValueError("session {} host port is none".format(self.session_name))
        self.connect(self.host,self.port,timeout)



if __name__ == "__main__":
    server = PasvSession()
    server.bind_and_accept("127.0.0.1",8888)
    while True :
        print server.receive_FC_msg(timeout=200)
        server.send_FC_msg("hi , baby !")