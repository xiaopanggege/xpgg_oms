#!/usr/bin/env python3
#-.- coding=utf8 -.-

# 用户名密码还有domain的name都要按时间填写才行，下面没有填写哈哈

import requests
import logging
# Create your views here.
logger = logging.getLogger('xpgg_oms.views')

def refresh_cdn(select_type,urls):
    result = {'result': None, 'status': False}
    with requests.Session() as s:
        # 获取token,用户名密码还有domain的name都要按时间填写才行
        header = {"Content-Type":"application/json"}
        data = {"auth":
                    {"identity":
                         {"methods": ["password"],
                          "password": {"user":
                                           {"name": "你的用户名",
                                            "password": "你的用户密码",
                                            "domain": {"name": "你的账户名"}
                                            }
                                       }
                          },
                     "scope": {"project":
                                   {"name": "cn-east-2" }
                               }
                     }
                }
        r = s.post('https://iam.cn-east-2.myhuaweicloud.com/v3/auth/tokens',json=data,headers=header)
        try:
            r.raise_for_status()
        except Exception as e:
            logger.error('执行refresh_cdn函数，获取token失败')
            result['result'] = r.text
            return result

        token = {"x-auth-token":r.headers["X-Subject-Token"]}

        # 刷新缓存
        data = {"refreshTask":{
                                "type":select_type,
                                "urls":urls
                    }
                }
        r = s.post('https://cdn.myhwclouds.com/v1.0/cdn/refreshtasks', json=data, headers=token)
        try:
            r.raise_for_status()
        except Exception as e:
            logger.error('执行refresh_cdn函数，缓存刷新返回错误的code')
            result['result'] = r.json()
            return result
        result['result'] = r.json()['refreshTask']
        result['status'] = True
        return result

def preheating_cdn(urls):
    result = {'result': None, 'status': False}
    with requests.Session() as s:
        # 获取token
        header = {"Content-Type":"application/json"}
        data = {"auth":
                    {"identity":
                         {"methods": ["password"],
                          "password": {"user":
                                           {"name": "loyowl",
                                            "password": "loyo2018.",
                                            "domain": {"name": "loyowl"}
                                            }
                                       }
                          },
                     "scope": {"project":
                                   {"name": "cn-east-2" }
                               }
                     }
                }
        r = s.post('https://iam.cn-east-2.myhuaweicloud.com/v3/auth/tokens',json=data,headers=header)
        try:
            r.raise_for_status()
        except Exception as e:
            logger.error('执行preheating_cdn函数，获取token失败')
            result['result'] = r.text
            return result

        token = {"x-auth-token":r.headers["X-Subject-Token"]}

        # 缓存预热
        data = {"preheatingTask":{
                                "urls":urls
                    }
                }
        r = s.post('https://cdn.myhwclouds.com/v1.0/cdn/preheatingtasks', json=data, headers=token)
        try:
            r.raise_for_status()
        except Exception as e:
            logger.error('执行preheating_cdn函数，缓存预热返回错误的code')
            result['result'] = r.json()
            return result
        result['result'] = r.json()['preheatingTask']
        result['status'] = True
        return result

def history_task(task_id):
    result = {'result': None, 'status': False}
    with requests.Session() as s:
        # 获取token
        header = {"Content-Type":"application/json"}
        data = {"auth":
                    {"identity":
                         {"methods": ["password"],
                          "password": {"user":
                                           {"name": "loyowl",
                                            "password": "loyo2018.",
                                            "domain": {"name": "loyowl"}
                                            }
                                       }
                          },
                     "scope": {"project":
                                   {"name": "cn-east-2" }
                               }
                     }
                }
        r = s.post('https://iam.cn-east-2.myhuaweicloud.com/v3/auth/tokens',json=data,headers=header)
        try:
            r.raise_for_status()
        except Exception as e:
            logger.error('执行history_task函数，获取token失败')
            result['result'] = r.text
            return result

        token = {"x-auth-token":r.headers["X-Subject-Token"]}
        # 查看缓存刷新状态
        r = s.get('https://cdn.myhwclouds.com/v1.0/cdn/historytasks/%s/detail' % task_id, params=data, headers=token)
        try:
            r.raise_for_status()
        except Exception as e:
            logger.error('执行history_task函数，获取任务详情返回错误的code')
            result['result'] = r.json()
            return result
        result['result'] = r.json()
        result['status'] = True
        return result



