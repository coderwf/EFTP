
# -*- coding:utf-8 -*-
from common import bc_to_decimal , decimal_to_bc
from common import BytesConsumer

#----------------------------------------------------------------
class FieldLength(object):
    Control_MLL          = 2  #控制消息最长为65535字节
    Data_MLL             = 4  #数据消息最长 4294967295 字节
    Operation_CL         = 2  #客户端操作类型码,最大65535种
    Control_REPL_CL      = 2  #服务器控制码回复最大65535种


class ReplyCodeDef(object):
    ENTER_PASSIVE_MODE       = 227
    USER_LOGIN               = 230
    USER_OK_NEED_PASS        = 331
    USER_OR_PASSWORD_ERR     = 530
    NEED_PASS                = 332
    BAD_OPERATION            = 550
    OK_OPERATION             = 200
    DATA_CONN_NEED           = 425
    UNIMPLEMENT_CMD          = 202
    DATA_CONN_OK             = 225
    NO_USER                  = 231
    FILE_OR_DIR_NOT_EXIST    = 551
    NOT_DIR                  = 552


class OpCode(object):
    UNKNOWN       = 000
    LIST          = 204
    PUT           = 205
    GET           = 206
    PWD           = 207
    USER          = 208
    PASS          = 209
    QUIT          = 210
    ABOR          = 211
    SYS           = 212
    CD            = 213
    codedef = {LIST:"LIST",PUT:"PUT",GET:"GET",USER:"USER",PWD:"PWD",
             PASS:"PASS",QUIT:"QUIT",SYS:"SYS",ABOR:"ABOR",CD:"CD"}

    @staticmethod
    def get_def(code):
        return OpCode.codedef.get(code,"UNKNOWN")

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
    b_consumer = BytesConsumer(host_port_str)
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
