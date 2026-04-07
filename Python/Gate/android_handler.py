"""移动应用(Android)通信处理模块。

负责与 Android 移动应用的 TCP 通信，包括：
- 移动应用连接监听
- 用户登录/注册
- 阈值设置
- 设备数据推送
"""

import json
import logging
import socket
import threading
from typing import TYPE_CHECKING

from MyComm import format_comm_data_string, format_userdata_string, decode_comm_data
from common.constants import (
    DOOR_DENIED,
    FIELD_BRIGHTNESS,
    FIELD_HUMIDITY,
    FIELD_TEMPERATURE,
    LISTEN_BACKLOG,
    ANDROID_RECV_INTERVAL,
    ANDROID_SEND_INTERVAL,
)
from common.config import UserConfig, write_user_config, load_user_config
from common.protocol import send_json, recv_json, send_line, recv_line

if TYPE_CHECKING:
    from common.models import GatewayState

logger = logging.getLogger(__name__)


class AndroidHandler:
    """移动应用通信处理器。

    封装移动应用相关的通信逻辑，持有数据库服务器套接字引用。

    Attributes:
        db_socket: 与数据库服务器的 TCP 套接字。
        config_dir: 配置文件目录。
    """

    def __init__(self, db_socket: socket.socket, config_dir) -> None:
        self.db_socket = db_socket
        self.config_dir = config_dir

    def android_handler(self, gate_network_config, state: "GatewayState") -> None:
        """移动应用通信主监听线程。

        Args:
            gate_network_config: 网关网络配置。
            state: 网关共享状态对象。
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((gate_network_config.ip, gate_network_config.android_port))
        s.listen(LISTEN_BACKLOG)
        logger.info("移动应用通信端口已开启: %s:%d",
                     gate_network_config.ip, gate_network_config.android_port)

        while True:
            try:
                cs, addr = s.accept()
                logger.info("移动应用连接: %s", addr)
                thread = threading.Thread(
                    target=self._client_handler, args=(cs, state), daemon=True
                )
                thread.start()
            except OSError as error:
                logger.error("移动应用监听异常: %s", error)

    def _client_handler(self, cs: socket.socket, state: "GatewayState") -> None:
        """处理单个移动应用连接。

        Args:
            cs: 移动应用的 TCP 套接字。
            state: 网关共享状态对象。
        """
        try:
            recv_data = recv_json(cs)
            android_state, curr_user_json, status_code = decode_comm_data(recv_data)
            curr_user = curr_user_json if isinstance(curr_user_json, dict) else json.loads(curr_user_json)

            if android_state == "login":
                self._android_login(cs, curr_user, state)
            elif android_state == "register":
                self._android_register(cs, curr_user)

        except (json.JSONDecodeError, ValueError) as error:
            logger.error("解析移动应用数据失败: %s", error)
        except (ConnectionError, OSError) as error:
            logger.error("移动应用连接断开: %s", error)
        except Exception as error:
            logger.error("移动应用通信异常: %s", error)
        finally:
            cs.close()

    def _android_login(self, cs: socket.socket, curr_user: dict, state: "GatewayState") -> None:
        """处理用户登录。

        Args:
            cs: 移动应用的 TCP 套接字。
            curr_user: 用户信息字典，需包含 "account" 和 "password" 键。
            state: 网关共享状态对象。
        """
        try:
            user_config = load_user_config(config_dir=self.config_dir)
        except FileNotFoundError:
            user_config = UserConfig()

        if user_config.username == curr_user["account"] and user_config.password == curr_user["password"]:
            send_json(cs, {"status": 1})
            state.login_status = 1
            logger.info("用户 '%s' 登录成功", curr_user["account"])

            # 等待设备节点连接
            state.wait_for_sensor()

            # 启动收发线程
            recv_thread = threading.Thread(
                target=self._get_from_android, args=(cs, state), daemon=True
            )
            send_thread = threading.Thread(
                target=self._send_to_android, args=(cs, state), daemon=True
            )
            recv_thread.start()
            send_thread.start()
            recv_thread.join()
            send_thread.join()
        else:
            send_json(cs, {"status": 0})
            state.login_status = 0
            logger.warning("用户 '%s' 登录失败", curr_user["account"])

    def _android_register(self, cs: socket.socket, given_user: dict) -> None:
        """处理用户注册。

        流程：将用户信息发送到数据库服务器 → 根据结果更新本地配置。

        Args:
            cs: 移动应用的 TCP 套接字。
            given_user: 用户信息字典，需包含 "account"、"password"、"device_Key" 键。
        """
        logger.info("用户正在注册: %s", given_user.get("account"))

        # 构造并发送注册请求到数据库服务器
        db_data_send = format_comm_data_string(
            "add_new_user",
            format_userdata_string(given_user["account"], given_user["password"], given_user["device_Key"]),
            1,
        )
        send_json(self.db_socket, db_data_send)
        logger.info("向数据库服务器发送: %s", db_data_send)

        # 接收数据库服务器响应
        try:
            db_data_recv = recv_json(self.db_socket)
            _, data, status_code = decode_comm_data(db_data_recv)

            if status_code == 1:
                write_user_config(
                    UserConfig(
                        username=given_user["account"],
                        password=given_user["password"],
                        device_key=given_user["device_Key"],
                    ),
                    config_dir=self.config_dir,
                )
                logger.info("注册成功，用户信息已更新")
                send_json(cs, {"status": 1})
            elif status_code in (0, 2):
                logger.warning("注册失败: %s", data)
                send_json(cs, {"status": 0})
        except (ConnectionError, OSError) as error:
            logger.error("注册过程连接断开: %s", error)
            send_json(cs, {"status": 0})
        except Exception as error:
            logger.error("注册过程异常: %s", error)
            send_json(cs, {"status": 0})

    def _send_to_android(self, cs: socket.socket, state: "GatewayState") -> None:
        """向移动应用推送设备数据。

        使用 JSON 格式发送传感器数据。

        Args:
            cs: 移动应用的 TCP 套接字。
            state: 网关共享状态对象。
        """
        import time

        logger.info("移动应用发送子线程开启")

        try:
            while True:
                data = state.get_data_snapshot()
                send_json(cs, data)
                logger.info("向移动应用发送: %s", data)
                time.sleep(ANDROID_SEND_INTERVAL)

        except (ConnectionError, ConnectionAbortedError, OSError) as error:
            logger.error("移动应用发送连接断开: %s", error)

    def _get_from_android(self, cs: socket.socket, state: "GatewayState") -> None:
        """从移动应用接收控制指令。

        解析操作码并更新阈值数据：
        - light_th_open/close: 智能空调开关
        - change_temperature_threshold: 温度阈值
        - change_humidity_threshold: 湿度阈值
        - curtain_open/close: 窗帘控制
        - change_brightness_threshold: 光照度阈值

        Args:
            cs: 移动应用的 TCP 套接字。
            state: 网关共享状态对象。
        """
        import time

        logger.info("移动应用接收子线程开启")

        try:
            while True:
                recv_data = recv_json(cs)
                operation, operation_value, _ = decode_comm_data(recv_data)

                if operation == "light_th_open":
                    state.set_threshold(FIELD_TEMPERATURE, -1)
                    state.set_threshold(FIELD_HUMIDITY, -1)
                    logger.info("移动应用指令: 智能空调灯光开启")
                elif operation == "light_th_close":
                    state.set_threshold(FIELD_TEMPERATURE, 101)
                    state.set_threshold(FIELD_HUMIDITY, 101)
                    logger.info("移动应用指令: 智能空调灯光关闭")
                elif operation == "change_temperature_threshold":
                    state.set_threshold(FIELD_TEMPERATURE, operation_value)
                elif operation == "change_humidity_threshold":
                    state.set_threshold(FIELD_HUMIDITY, operation_value)
                elif operation == "curtain_close":
                    state.set_threshold(FIELD_BRIGHTNESS, 65535)
                    logger.info("移动应用指令: 窗帘关闭")
                elif operation == "curtain_open":
                    state.set_threshold(FIELD_BRIGHTNESS, -2)
                    logger.info("移动应用指令: 窗帘开启")
                elif operation == "change_brightness_threshold":
                    state.set_threshold(FIELD_BRIGHTNESS, operation_value)

                threshold = state.threshold_data
                logger.info(
                    "移动应用阈值更新: 温度=%s, 湿度=%s, 光照=%s",
                    threshold.get(FIELD_TEMPERATURE),
                    threshold.get(FIELD_HUMIDITY),
                    threshold.get(FIELD_BRIGHTNESS),
                )

        except (ConnectionError, ConnectionAbortedError, OSError) as error:
            logger.error("移动应用接收连接断开: %s", error)
        except (ValueError, json.JSONDecodeError) as error:
            logger.error("解析移动应用指令失败: %s", error)
