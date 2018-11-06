
# -*- coding:utf-8 -*-
from common import decimal_to_bc
from common import BYtesManager

#----------------------------------------------------------------
class FieldLength(object):
    Control_MLL          = 2  #控制消息最长为65535字节
    Data_MLL             = 4  #数据消息最长 4294967295 字节
    Operation_L          = 2  #客户端操作类型码,最大65535种
    Control_REP_L        = 2   #服务器控制码回复最大65535种


class ReplyCodeDef(object):
    ENTER_PASSIVE_MODE       = 227
    ENTER_PORT_MODE          = 228
    USER_OK                  = 331 #用户存在需要登陆
    USER_OR_PASSWORD_ERR     = 530 #账号密码错误
    NO_USER                  = 231 #用户不存在
    NEED_AUTH                = 332 #需要登陆成功才能访问
    LOGIN_OK                 = 333 #登录成功
    BAD_OPERATION            = 550 #错误操作
    OK_OPERATION             = 200 #操作正确
    UN_IMPLEMENT_CMD         = 202 #命令未实现
    DATA_CONN_OK             = 224
    DATA_CONN_START          = 225 #开始数据连接
    DATA_CONN_FAILED         = 226 #数据连接失败
    DATA_CONN_ACK            = 330 #确认数据连接
    FILE_NOT_EXIST           = 551 #文件不存在
    NOT_FILE                 = 552 #不是文件
    DIR_NOT_EXIST            = 553 #文件夹不存在
    NOT_DIR                  = 554 #不是文件夹


class OpCode(object):
    UNKNOWN       = 000
    LIST          = 204
    PUT           = 205
    GET           = 206
    PWD           = 207
    USER          = 208
    PASS          = 209
    QUIT          = 210
    ABORT         = 211
    SYS           = 212
    CD            = 213
    MKD           = 214
    RMD           = 215
    PASV          = 216
    PORT          = 217

    code_def = {LIST:"LIST",PUT:"PUT",GET:"GET",USER:"USER",PWD:"PWD",
             PASS:"PASS",QUIT:"QUIT",SYS:"SYS",ABORT:"ABORT",CD:"CD",MKD:"MKD",RMD:"RMD",
               PASV:"PASV",PORT:"PORT"}

    @staticmethod
    def get_def(code):
        return OpCode.code_def.get(code,"UNKNOWN")


#将host 和 ip打包成二进制流
def pack_host_port(host,port):
    host = str(host)
    ips = host.split(".")
    if len(ips) != 4 :
        raise ValueError("host {} invalid ".format(host))
    host = ""
    for ip in ips :
        host = host + decimal_to_bc(int(ip),1)
    result = host + decimal_to_bc(port,2)
    return result

#将包含二进制流的ip port解析出来,返回元组
def unpack_host_port(host_port_str):
    if len(host_port_str) != 6 :
        raise ValueError("string {} invalid".format(host_port_str))
    b_consumer = BYtesManager(host_port_str)
    ips  = []
    for i in range(0,4):
        ips.append(b_consumer.consume_with_decimal(1))
    host = str(ips[0])+"."+str(ips[1])+"."+str(ips[2])+"."+str(ips[3])
    port = b_consumer.consume_with_decimal(2)
    return host , port


if __name__ == "__main__":
    host_port_str = pack_host_port("127.0.0.19",56)
    print host_port_str
    host , port   = unpack_host_port(host_port_str)
    print host , port
