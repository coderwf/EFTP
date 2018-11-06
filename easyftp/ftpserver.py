# -*- coding:utf-8 -*-
import socket
from core import session
from core.protocol import FieldLength , OpCode , ReplyCodeDef,pack_host_port,unpack_host_port
from core.common import bc_to_decimal,decimal_to_bc,BYtesManager
import os
import platform
import hashlib

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
DATA_CONN_CREATE_FAILED  = "Can't create data connection ,Check it."

PASV_MODE            =  0
PORT_MODE            =  1

ASCII_MODE           =  4
BINARY_MODE          =  5
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
        self.data_mode           =  None
        self.tran_mode           =  BINARY_MODE   ###传输方式

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
                print "client closed ."
        print "client closed ."

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

    def ftp_list(self):
        if not self._check_auth_() :
            return
        ###一共需要返回两次结果到客户端
        ###第一次如果检查无误则返回确认连接并进行第二次,否则返回错误并结束对话
        ###第二次确认连接并传输数据,然后返回传输结构
        dir_name     = self._bytes_manager.consume_all()
        target_dir   = os.path.abspath(os.path.join(self.cwd,dir_name))
        if not self._check_target_dir_(target_dir):
            return
        try :
            file_list = os.listdir(target_dir)
            self.send_reply(ReplyCodeDef.DATA_CONN_ACK,"Ack data conn.")
        except :
            self.send_reply(ReplyCodeDef.BAD_OPERATION,NO_PERMISSION)
            return  ##确认连接之前的任何异常直接结束
        ###进行连接确认
        try :
            self._ack_data_session_()
            ###如果连接确认ok则传输数据并
            self.data_session.send_FD_msg(str(file_list))
            self.send_reply(ReplyCodeDef.OK_OPERATION,"List Transport Done.")
            return
        except :
            self.send_reply(ReplyCodeDef.DATA_CONN_FAILED,"Data connection failed.")
            self.close_data_session()

    ###只能put到当前工作目录下
    def ftp_put(self):
        ####第一步检查是否可以put
        if not self._check_auth_():
            return ##auth first return
        file_size = self._bytes_manager.consume_with_decimal(8)
        file_name = self._bytes_manager.consume_all()  ##64bit的文件大小
        target_file  = os.path.abspath(os.path.join(self.cwd,file_name))
        if os.path.exists(target_file) :
            self.send_reply(ReplyCodeDef.BAD_OPERATION,"File {} already exists".format(target_file))
            return
        # if not os.path.isfile(target_file) :
        #         #     self.send_reply(ReplyCodeDef.BAD_OPERATION,NOT_A_FILE.format(target_file))
        #         #     return
        try :
            f = open(target_file,"wb")
        except :
            self.send_reply(ReplyCodeDef.BAD_OPERATION,NO_PERMISSION)
            return

        #-------check auth and other -----
        self.send_reply(ReplyCodeDef.DATA_CONN_ACK,"Data Connection Ack.",ONE_MINUTE)
        try :
            self._ack_data_session_()
            print "ack data session ok ..."
        except :
            f.close()
            self.send_reply(ReplyCodeDef.DATA_CONN_FAILED, "Data connection Failed.")
            self.close_data_session()
            self.remove_file(target_file) # remove file
            return  ###conn failed
        read_size  =  0
        m          =  hashlib.md5()
        try :
            while read_size != file_size:
                length  = self.data_session.receive(FieldLength.Data_MLL)
                length  = bc_to_decimal(length)
                stream = self.data_session.receive(length,2000)
                m.update(stream)
                read_size += len(stream)
                f.write(stream)
            f.close()
        except :
            f.close()
            self.close_data_session()
            self.remove_file(target_file)
            self.send_reply(ReplyCodeDef.DATA_CONN_FAILED,"Data connection Failed.")
            return
        try :
            check_sum = self.data_session.receive_FC_msg(ONE_MINUTE)
        except :
            self.send_reply(ReplyCodeDef.DATA_CONN_FAILED)
            self.remove_file(target_file)
            self.close_data_session()
            return
        if check_sum != m.hexdigest() :
            self.send_reply(ReplyCodeDef.BAD_OPERATION,"File Checksum Error.")
            self.remove_file(target_file)
            self.close_data_session()
            return
        self.send_reply(ReplyCodeDef.OK_OPERATION,"File Put Done.")
        return

    def ftp_get(self):
        if not self._check_auth_():
            return
        #-------check auth -------
        file_name    = self._bytes_manager.consume_all()
        target_file  = os.path.abspath(os.path.join(self.cwd,file_name))
        if not self._check_target_file(target_file) :
            return
        file_size    = os.stat(target_file).st_size
        ###----check---file
        try :
            f = open(target_file,"rb")
        except :
            self.send_reply(ReplyCodeDef.BAD_OPERATION,NO_PERMISSION)
            return
        ###---check-auth-file--and so on ----
        ## --- check ok ---
        self.send_reply(ReplyCodeDef.DATA_CONN_ACK,decimal_to_bc(file_size,8))
        ### start ack
        try :
            self._ack_data_session_()
        except :
            f.close()
            self.send_reply(ReplyCodeDef.DATA_CONN_FAILED,"Data connection Failed.")
            self.close_data_session()
            return ###conn failed
        ### -- start transport file
        read_size = 0
        m         = hashlib.md5()
        ###如果传输失败,则关闭连接并结束
        try :
            while read_size != file_size:
                stream = f.read(1024 * 1024)
                self.data_session.send_FD_msg(stream, ONE_MINUTE)
                read_size += len(stream)
                m.update(stream)
            f.close()
        except :
            self.send_reply(ReplyCodeDef.BAD_OPERATION,"File Get Error.")
            self.close_data_session()
            f.close()
            return
        ###发送check_sum
        try :
            self.data_session.send_FC_msg(m.hexdigest(),ONE_MINUTE)
        except :
            self.send_reply(ReplyCodeDef.BAD_OPERATION,"Check sum Get Error.")
            self.close_data_session()
            return
        self.send_reply(ReplyCodeDef.OK_OPERATION,"File Get Done.")
        return

    def remove_file(self, target_file):
        if os.path.exists(target_file) and os.path.isfile(target_file):
            import shutil
            shutil.rmtree(target_file)

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

    def ftp_rmd(self):
        if not self._check_auth_():
            return
        dir_name    = self._bytes_manager.consume_all()
        target_dir  = os.path.abspath(os.path.join(self.cwd, dir_name))
        if target_dir == self.cwd :
            self.send_reply(ReplyCodeDef.BAD_OPERATION,"Can't delete Working Directory.")
            return
        if not self._check_target_dir_(target_dir) :
            return
        try :
            import shutil
            shutil.rmtree(target_dir)
            self.send_reply(ReplyCodeDef.OK_OPERATION,"Directory {} Successfully Deleted.".format(target_dir))
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
        if not self._check_auth_() :
            return
        import time
        sys_info =  platform.system() + platform.release() + "," + platform.machine() + \
                    ","+str(long(time.time() * 1000))
        self.send_reply(ReplyCodeDef.OK_OPERATION,sys_info)
        return

    def ftp_port(self):
        try :
            host_port_str = self._bytes_manager.consume_all()
            host, port = unpack_host_port(host_port_str)
            self.close_data_session()
            self.data_session = session.PortSession()
            self.send_reply(ReplyCodeDef.DATA_CONN_START,"Start CONN.")
        except :
            self.send_reply(ReplyCodeDef.DATA_CONN_FAILED,DATA_CONN_CREATE_FAILED)
            return
        try :
            self.data_session.connect(host, port, 2000)
            self._ack_data_session_()
            self.send_reply(ReplyCodeDef.ENTER_PORT_MODE,"Entering Port Mode.")
            return
        except :
            self.send_reply(ReplyCodeDef.DATA_CONN_FAILED,DATA_CONN_CREATE_FAILED)
            return

    def ftp_pasv(self):
        ###一共返回两次结果 第一次表示连接是否可以建立 第二次表示连接是否成功
        if not self._check_auth_() :
            return
        host , port = self._create_pasv_session_()
        if not host :
            self.send_reply(ReplyCodeDef.DATA_CONN_FAILED,DATA_CONN_CREATE_FAILED)
            return
        self.send_reply(ReplyCodeDef.DATA_CONN_START,pack_host_port(host,port))
        try :
            self.data_session.accept(2000)  ##等待连接
            ###确认连接成功则返回OK并结束
            self._ack_data_session_()
            self.data_mode    = PASV_MODE
            self.send_reply(ReplyCodeDef.ENTER_PASSIVE_MODE,"Entering Pasv Mode.")
            return
        except Exception , e:
            print e
            ###连接失败则返回Failed并结束
            self.send_reply(ReplyCodeDef.DATA_CONN_FAILED,"Data connection Failed.")
            return

    def _create_pasv_session_(self):
        try :
            host, _ = self.user_session.get_address()
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

    def _ack_data_session_(self):
        if not self.data_session :
            raise ValueError("data session is none.")
        #3print self.data_session._read_buffer
        #self.data_session = session.PortSession()
        print self.data_session.receive(10,2000)
        ##print self.data_session._read_buffer
        self.data_session.send("1111111111",2000)

    def close(self):
        self.closed = True

    def close_data_session(self):
        if self.data_session :
            self.data_session.close()
            self.data_session  = None

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