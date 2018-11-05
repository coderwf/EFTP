
# -*- coding:utf-8 -*-

"""
通用工具


"""
import time
"""
超时异常
"""
class TimeoutError(Exception):
    def __init__(self,timeout,deadline,message=""):
        self.timeout  = timeout
        self.deadline = deadline
        self.message  = message
        self.items    = [self.timeout,self.deadline,self.message]

    def __str__(self):
        return "{} timeout for {}".format(self.message,self.timeout)

    def __getitem__(self, item):
        return self.items[item]

"""
时间检查类
超时检查
单位为ms
0 表示一直阻塞
"""
class TimeChecker(object) :
    def __init__(self,timeout,message=""):
        if not timeout : timeout = 0
        if timeout < 0:
            raise ValueError("timeout {} must greater than 0".format(timeout))
        self.timeout    =  timeout
        self.message    =  message
        self.deadline   =  time.time() * 1000 + timeout

    def check_timeout(self):
        if not self.timeout :
            return
        now = time.time() *1000
        if now > self.deadline :
            raise TimeoutError(self.timeout,self.deadline,self.message)

    def reset_timeout(self,timeout):
        if timeout <= 0:
            raise ValueError("timeout {} must greater than 0".format(timeout))
        if not timeout :
            raise ValueError("timeout {} invalid".format(timeout))
        self.timeout    = timeout
        self.deadline   = time.time() * 1000 + timeout

    def add_timeout(self,timeout):
        self.timeout    =  self.timeout +timeout
        self.deadline   = time.time() * 1000 + self.timeout

class BYtesManager(object):
    def __init__(self,bytes=""):
        self.bytes = bytes

    def consume(self,bytes_num):
        if len(self.bytes) <bytes_num:
            raise IOError("consume {} more than {}".format(bytes_num,len(self.bytes)))
        res = self.bytes[:bytes_num]
        self.bytes  = self.bytes[bytes_num:]
        return res

    def reset(self,bytes):
        self.bytes = bytes

    def clear(self):
        self.bytes = ""

    def consume_all(self):
        res         = self.bytes
        self.bytes  = ""
        return res

    def add_bytes(self,bytes):
        self.bytes += bytes

    def add_bytes_with_decimal(self,decimal_,B_num):
        self.bytes += decimal_to_bc(decimal_,B_num)

    #返回整数
    def consume_with_decimal(self,bytes_num):
        if len(self.bytes) < bytes_num:
            raise IOError("consume {} more than {}".format(bytes_num, len(self.bytes)))
        res = self.bytes[:bytes_num]
        self.bytes = self.bytes[bytes_num:]
        return bc_to_decimal(res)

# 二进制字符流到正数的转换工具

BASE              = 8
BASENUM           = 255

#二进制字符流转化为数字
def bc_to_decimal(bc):
    length = len(bc)
    decimal_ = 0L
    for i in range(0,length):
        num = (ord(bc[i]) << (length - i - 1)*BASE)
        decimal_ |= num
    return decimal_


#将数字转化为二进制字符流
def decimal_to_bc(decimal_,bytes_num):
    bc = ""
    for i in range(0,bytes_num):
        bc = chr(BASENUM & decimal_) + bc
        decimal_ >>= BASE
    return bc

if __name__ == "__main__":
    # t_check = TimeChecker(0,"test")
    # while True :
    #     t_check.check_timeout()
    #
    pass

