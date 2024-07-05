import atexit
import os
import shutil
import sys
import threading

from loguru import logger

from interface import ProductCli, SettingCli, UserCli
from util import Bilibili, Captcha, Config, Notice, Request, Task


def cleanup_meipass() -> None:
    if hasattr(sys, "_MEIPASS"):
        meipass_path = sys._MEIPASS  # type: ignore
        try:
            shutil.rmtree(meipass_path)
            print(f"正在清理 {meipass_path}")
        except Exception as e:
            print(f"清理失败 {meipass_path}: {e}")


atexit.register(cleanup_meipass)

if __name__ == "__main__":
    # 删除缓存
    if os.path.exists(".cache"):
        shutil.rmtree(".cache")

    # 丢锅
    print(
        """
|=====================================================================
|
|  欢迎使用 https://github.com/biliticket/transition-ticket
|  本程序仅供学习交流, 不得用于商业用途
|  使用本程序进行违法操作产生的法律责任由操作者自行承担
|  对本程序进行二次开发/分发时请注意遵守GPL-3.0开源协议
|  本脚本仅适用于蹲回流票, 我们反对将其用于抢票
|  黄牛/收费代抢４０００＋
|
|  本版本移除了对用户数据的加密保护，以便云上远程部署（本地机器登录，云端运行）
|  如无此需求请使用原版
|
|=====================================================================
|
|  交互: 上下 键盘↑↓键, 多选 空格, 确认 回车
|
|=====================================================================
"""
    )

    # 日志
    logger.add(
        "log/{time}.log",
        colorize=False,
        enqueue=True,
        encoding="utf-8",
        # 调试
        backtrace=True,
        diagnose=True,
    )

    # 初始化
    # 用户数据文件
    userData = Config(dir="user")
    productData = Config(dir="product")
    settingData = Config(dir="setting")

    # 验证
    cap = Captcha()

    # 检测配置文件情况
    userList = userData.List()
    productList = productData.List()
    settingList = settingData.List()

    while True:
        # 读取配置
        userConfig = UserCli(conf=userData).Select(selects=userList) if userList != [] else UserCli(conf=userData).Generate()
        productConfig = ProductCli(conf=productData).Select(selects=productList) if productList != [] else ProductCli(conf=productData).Generate()
        settingConfig = SettingCli(conf=settingData).Select(selects=settingList) if settingList != [] else SettingCli(conf=settingData).Generate()

        net = Request(
            cookie=userConfig["cookie"],
            header=userConfig["header"],
            timeout=settingConfig["request"]["timeout"],
            proxy=settingConfig["request"]["proxy"],
            isDebug=settingConfig["dev"]["debug"],
        )

        api = Bilibili(
            net=net,
            projectId=productConfig["projectId"],
            screenId=productConfig["screenId"],
            skuId=productConfig["skuId"],
            buyer=userConfig["buyer"],
            count=len(userConfig["buyer"]),
            goldTime=settingConfig["request"]["gold"],
            phone=userConfig["phone"],
        )

        job = Task(
            net=net,
            cap=cap,
            api=api,
        )

        # job.DrawFSM()

        # 任务流
        if not job.Run():
            break

        notice = Notice(title="抢票", message="下单成功! 请在十分钟内支付")
        mode = settingConfig["notice"]
        logger.success("【抢票】下单成功! 请在十分钟内支付")

        # 通知
        noticeThread = []
        t1 = threading.Thread(target=notice.Message)
        t2 = threading.Thread(target=notice.Sound)
        t3 = threading.Thread(target=notice.PushPlus, args=(mode["plusPush"],))

        if mode["system"]:
            noticeThread.append(t1)
        if mode["sound"]:
            noticeThread.append(t2)
        if mode["wechat"]:
            noticeThread.append(t3)

        for t in noticeThread:
            t.start()

        logger.info("【通知】本轮抢票结束, 正在重启...")
