#!/usr/bin/env python3
#-.- coding=utf-8 -.-
#python3 安装scapy方法pip install scapy-python3
#并且安装yum install tcpdump 在三层扫描的时候会提示要安装这个

#注意，这个在引用的时候可能只能在views.py的某个方法里面引用，好像无法在views.py的全局上头引用，不然会报错，目前没研究如何解决！！！！

#用的是ARP ping速度杠杠的
#srp只能局域网扫描，sr只能用于三层网络
from scapy.all import *
import logging
# Create your views here.
logger = logging.getLogger('xpgg_oms.views')

def ipscan(ipnet):
    ip_list = []
    if int(ipnet.split('/')[1])<24:
        ip_list.append('由于性能问题，网段掩码请不要小于24位掩码，感谢使用！')
        return ip_list
    ip_check=ipnet.split('/')[0].rsplit('.',1)[0]
    #判断是局域网还是三层，因为三层扫描无法扫描局域网
    if ip_check=='192.168.68' or ip_check=='127.0.0':
        try:
            ans, unans = srp(Ether(dst="FF:FF:FF:FF:FF:FF") / ARP(pdst=ipnet), timeout=2, verbose=0)
        except Exception as e:
            return ip_list.append(e)
        else:
            # ip_list=[i for i in range(len(ans))]
            for snd, rcv in ans:
                ip_addr = 'IP:'.ljust(5) + rcv.sprintf("%ARP.psrc%").ljust(17) + 'MAC:'.ljust(6) + rcv.sprintf("%ARP.hwsrc%") + '  存在\n'
                ip_list.append(ip_addr)
                # 利用sort的key来排序，取到的是str所以要改成int才能对比整数，不然比str排序不对
            ip_list.sort(key=lambda x: int(x.rsplit('.', 1)[1].split()[0]))
            return ip_list
    else:
        try:
            ans, unans = sr(IP(dst=ipnet) / ICMP(),timeout=2,verbose=0)
        except Exception as e:
            return ip_list.append(e)
        else:
            for snd, rcv in ans:
                ip_addr = 'IP:'.ljust(5) + rcv.sprintf("%IP.src%").ljust(17) + '  存在\n'
                ip_list.append(ip_addr)
            ip_list.sort(key=lambda x: int(x.rsplit('.', 1)[1].split()[0]))
            return ip_list


def portscan(portscanip,portscan_startport,portscan_endport):
    port_list = []
    if portscanip == '192.168.68.50' or portscanip == '127.0.0.1' or portscanip == '192.168.68.50/32':
        return '对不起，本平台服务器IP不支持扫描嘿嘿'
    try:
        res, unans = sr(IP(dst=portscanip) / TCP(flags="S", dport=(portscan_startport,portscan_endport)), timeout=2,verbose=0)
    except Exception as e:
        return port_list.append(e)
    else:
        for snd, rcv in res:
            # 之前本来用下面这个sprintf来获取端口但是发现他会自动转成英文比如22转成ssh不方便弃用
            # list_port=rcv.sprintf("%TCP.sport%")

            # 获取扫描的flags值
            list_flags = rcv.sprintf("%TCP.flags%")

            # logger.error(rcv.show()) #查看扫描端口情况

            # flags='SA'表示能访问到，RA表示无法访问到
            if list_flags == 'SA':
                # 用str(rcv.sport)可以获取到端口而不会被转换成ssh、http之类的英文，方便点
                # print('端口%s is listening' % str(rcv.sport))
                port_list.append('IP:'.ljust(5) + rcv.sprintf("%IP.src%").ljust(17) + '端口' + str(rcv.sport).rjust(7)+'  is Listening\n')
                # UDP端口扫描
                # 和TCP类似只是把TCP改成UDP即可，用的少所以不测试了有需要再测
                # ans,unans=sr( IP(dst="192.168.*.1-10")/UDP(dport=0),timeout=2 )
        return port_list




def traceroutescan(tracert_data):
    tracert_list=[]
    try:
        res, unans = sr(IP(dst=tracert_data, ttl=(0, 30), id=RandShort()) / TCP(flags=0x2), timeout=2,verbose=0)
    except Exception as e:
        return tracert_list.append(e)
    else:
        for snd, rcv in res:
            # print(rcv.show()) #查看收数据的扫描情况
            # snd.ttl是路由跳数，rcv.src是每跳经过的地址，最后一个是判断是否有TCP这层，你从上面的
            # show()可以看出来在还没到达路由目的的时候是没有TCP层的数据，只有到达才有，用这个可以
            # 看出是否路由到达了
            if isinstance(rcv.payload, TCP):
                tracert_list.append(str(snd.ttl)+'\t'+ str(rcv.src)+'\t\t路由到达\n')
                return tracert_list
            else:
                tracert_list.append(str(snd.ttl)+'\t'+ str(rcv.src)+'\t\t未到达\n')
        return tracert_list