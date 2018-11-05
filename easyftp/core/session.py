
# -*- coding:utf-8 -*-

"""
封装socket便于收发数据
"""

import  socket
import errno
from common import TimeCheck , bc_to_decimal , TimeoutError
import time

#----------------------------------------------------------
"""
所有的session都至少持有一个socket来进行通信
获取socket的方式有两种 1:外部提供 2:自己提供端口号并创建socket
"""

"""
最基础的session,只有receive和send功能,无其他拓展功能
"""
class BaseSession(object):
    def __init__(self,session_socket,read_chunk_size=1024*1024,
                 max_read_buffer_size=1024*1024*10):
        self.session_socket           = session_socket
        self.closed                   = False
        self._read_buffer             = ""
        self.max_read_buffer_size     = max_read_buffer_size
        self.read_chunk_size          = read_chunk_size
        self.session_socket.setblocking(False)

    def get_address(self):
        address = self.session_socket.getsockname()
        return address[0] , int(address[1])

    def send(self,data,timeout=None):
        if not self.session_socket :
            raise ValueError("session socket is none")
        t_check = TimeCheck(timeout,"session send data")
        while data :
            try :
                res  = self.session_socket.send(data)
                data = data[res:]
            except socket.error , e :
                if e[0] in (errno.EAGAIN, errno.EWOULDBLOCK):
                    t_check.check_timeout()
                    continue
                raise

    def receive(self,bytes,timeout=None):
        if not self.session_socket :
            raise ValueError("session socket is none")
        t_check  = TimeCheck(timeout,"session receive data")
        while len(self._read_buffer) < bytes :
            try :
                chunk = self.session_socket.recv(self.read_chunk_size)
                #print "chunk>>>",chunk
            except socket.error, e:
                if e[0] in (errno.EAGAIN, errno.EWOULDBLOCK):
                    t_check.check_timeout()
                    continue
                raise
            if not chunk:
                raise IOError("session read chunk is none")
            self._read_buffer += chunk
            #为了避免此处超时,再给一次机会检查
            if len(self._read_buffer) >= bytes:
                break
            t_check.check_timeout()
        return self._consume(bytes)

    def _consume(self,bytes):
        if len(self._read_buffer) < bytes :
            raise IOError("can't consume bytes {}".format(bytes))
        res                 = self._read_buffer[:bytes]
        self._read_buffer   = self._read_buffer[bytes:]
        return res

    def close(self):
        if not self.closed and self.session_socket:
            self.closed   = True
            self.session_socket.close()


class ClientSession(BaseSession):
    def __init__(self):
        BaseSession.__init__(self)


#当被动模式打开时使用这个session简化操作
class SupSession(object):
    def __init__(self):
        self.session         = None

    def send(self,data,timeout=None):
        if not self.session :
            raise IOError("pasv session is none")
        self.session.send(data,timeout)

    def receive(self,bytes,timeout=None):
        if not self.session :
            raise IOError("pasv session is none")
        return self.session.receive(bytes,timeout)

    def receive_with_decimal(self,bytes,timeout=None):
        bytes  = self.session.receive(bytes,timeout)
        return bc_to_decimal(bytes)

    # def receive_message(self,timeout=None):
    #     start_time  = time.time() * 1000
    #     length      = self.receive_with_decimal(4,timeout)
    #     time_used   = time.time() *1000 - start_time
    #     if timeout and time_used >timeout :
    #         raise TimeoutError(timeout,timeout+start_time,"pasv session receive message")
    #     rest_time = None if timeout == None else max(timeout-time_used,0)
    #     message  = self.receive(length,rest_time)
    #     return message

    def close(self):
        pass


#Port方式下主动连接的session
class PortSession(SupSession):
    def __init__(self):
        SupSession.__init__(self)
        self.session_socket     = None
        self.closed             = True

    def connect(self,host,port,timeout=None):
        t_check = TimeCheck(timeout,"port session connection ")
        if not self.session_socket :
            self.session_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self.closed         = False
        while True :
            try :
                self.session_socket.connect((host, port))
                #print "session_socket,>>>",self.session_socket
                self.session = BaseSession(self.session_socket)
                break
            except socket.error , e:
                if e[0] in (errno.EAGAIN,errno.EWOULDBLOCK):
                    t_check.check_timeout()
                    continue
                raise

    def close(self):
        if not self.closed and self.session:
            self.session.close()
            self.session = None


#被动等待接受连接并将得到的socket
class PasvSession(SupSession):
    def __init__(self):
        SupSession.__init__(self)
        self.bind_socket    =  None
        self.closed         =  True

    def bind_and_accept(self,bind_host,bind_port,timeout=None):
        t_check   = TimeCheck(timeout,"pasv bind and accept")
        if not self.bind_socket :
            self.bind_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            self.bind_socket.bind((bind_host,bind_port))
            self.bind_socket.setblocking(False)
            self.bind_socket.listen(2)
        while True :
            try :
                client_socket,client_address = self.bind_socket.accept()
                self.session = BaseSession(client_socket)
                self.closed  = False
                break
            except socket.error , e:
                if e[0] in (errno.EWOULDBLOCK,errno.EAGAIN):
                    t_check.check_timeout()
                    continue
                raise

    def close(self):
        if not self.closed :
            self.closed = True
            if self.session :
                self.session.close()
                self.session = None
            if self.bind_socket :
                self.bind_socket.close()
                self.bind_socket = None

    def close_session(self):
        if self.session :
            self.session.close()
            self.session = None








