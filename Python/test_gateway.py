"""IoT 网关系统综合测试脚本。

在不依赖外部 MySQL/远程数据库服务器的情况下，验证所有核心模块和通信链路。
包括：协议编解码、配置加载、共享状态线程安全、模拟 TCP 通信全链路。
"""

import json
import os
import socket
import sys
import threading
import time
from pathlib import Path

# 将项目根目录和 Gate 目录添加到 sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent
_GATE_DIR = _PROJECT_ROOT / "Gate"

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
if str(_GATE_DIR) not in sys.path:
    sys.path.insert(0, str(_GATE_DIR))

# ============================================================
# 测试计数
# ============================================================
_passed = 0
_failed = 0
_errors = []


def _ok(name: str):
    global _passed
    _passed += 1
    print(f"  [PASS] {name}")


def _fail(name: str, reason: str):
    global _failed
    _failed += 1
    _errors.append((name, reason))
    print(f"  [FAIL] {name}: {reason}")


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ============================================================
# 1. 测试 protocol.py — JSON 编解码和 Socket 收发
# ============================================================
def test_protocol():
    section("1. 测试 protocol.py — JSON 编解码")

    from common.protocol import (
        pack_command, unpack_command,
        pack_user_data, unpack_user_data,
        send_json, recv_json,
        send_line, recv_line,
    )

    # 1.1 pack_command / unpack_command
    cmd = pack_command("login", {"username": "Jiang"}, 1)
    assert isinstance(cmd, dict)
    assert cmd["op"] == "login"
    assert cmd["data"] == {"username": "Jiang"}
    assert cmd["status"] == 1
    _ok("pack_command 构造正确")

    op, data, status = unpack_command(cmd)
    assert op == "login"
    assert data == {"username": "Jiang"}
    assert status == 1
    _ok("unpack_command 解包正确")

    # 1.2 status 类型：int vs JSON 反序列化
    cmd_int = pack_command("test", "data", 1)
    serialized = json.dumps(cmd_int)
    deserialized = json.loads(serialized)
    op2, data2, status2 = unpack_command(deserialized)
    assert status2 == 1 and isinstance(status2, int)
    _ok("status int 经 JSON 序列化/反序列化后仍为 int")

    # 1.3 模拟 Android 发送的 status 为 string
    cmd_str_status = {"op": "login", "data": "data", "status": "1"}
    _, _, status3 = unpack_command(cmd_str_status)
    assert status3 == "1" and isinstance(status3, str)
    _ok("Android string status 解包为 str 类型")

    # 1.4 pack_user_data / unpack_user_data
    user = pack_user_data("Jiang", "pwd123", "A1")
    assert user == {"username": "Jiang", "password": "pwd123", "device_key": "A1"}
    _ok("pack_user_data 构造正确")

    u, p, k = unpack_user_data(user)
    assert (u, p, k) == ("Jiang", "pwd123", "A1")
    _ok("unpack_user_data 解包正确")

    # 1.5 unpack_user_data 缺少 username 应抛异常
    try:
        unpack_user_data({"password": "pwd"})
        _fail("unpack_user_data 缺少 username", "未抛出异常")
    except ValueError:
        _ok("unpack_user_data 缺少 username 抛出 ValueError")

    # 1.6 Socket 收发测试
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", 0))
    server_sock.listen(1)
    port = server_sock.getsockname()[1]

    def _echo_server():
        conn, _ = server_sock.accept()
        data = recv_json(conn)
        send_json(conn, data)
        conn.close()

    t = threading.Thread(target=_echo_server, daemon=True)
    t.start()

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", port))

    original = {"op": "light_th_open", "data": None, "status": "1"}
    send_json(client, original)
    received = recv_json(client)
    assert received == original, f"期望 {original}, 实际 {received}"
    _ok("send_json/recv_json Socket 回环测试通过")

    client.close()
    server_sock.close()
    t.join(timeout=2)

    # 1.7 send_line/recv_line 测试
    server_sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock2.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock2.bind(("127.0.0.1", 0))
    server_sock2.listen(1)
    port2 = server_sock2.getsockname()[1]

    def _echo_line_server():
        conn, _ = server_sock2.accept()
        line = recv_line(conn)
        send_line(conn, line.upper())
        conn.close()

    t2 = threading.Thread(target=_echo_line_server, daemon=True)
    t2.start()

    client2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client2.connect(("127.0.0.1", port2))
    send_line(client2, "hello")
    resp = recv_line(client2)
    assert resp == "HELLO", f"期望 HELLO, 实际 {resp}"
    _ok("send_line/recv_line Socket 回环测试通过")

    client2.close()
    server_sock2.close()
    t2.join(timeout=2)


# ============================================================
# 2. 测试 MyComm.py — 兼容接口
# ============================================================
def test_mycomm():
    section("2. 测试 MyComm.py — 兼容接口")

    from MyComm import (
        format_comm_data_string, decode_comm_data,
        format_userdata_string, decode_user_data,
    )

    # 2.1 format_comm_data_string → decode_comm_data
    cmd = format_comm_data_string("add_new_user", {"username": "test"}, 1)
    op, data, status = decode_comm_data(cmd)
    assert op == "add_new_user"
    assert data == {"username": "test"}
    assert status == 1
    _ok("format_comm_data_string <-> decode_comm_data 往返正确")

    # 2.2 format_userdata_string → decode_user_data
    user = format_userdata_string("user1", "pass1", "key1")
    u, p, k = decode_user_data(user)
    assert (u, p, k) == ("user1", "pass1", "key1")
    _ok("format_userdata_string <-> decode_user_data 往返正确")

    # 2.3 Android 发送的 JSON 中 status 为 string "1"（模拟 fastjson 行为）
    android_json = {"op": "login", "data": "{\"account\":\"Jiang\",\"password\":\"pwd\"}", "status": "1"}
    op, data, status = decode_comm_data(android_json)
    assert op == "login"
    assert isinstance(status, str)  # str "1"
    _ok("Android 端 string status 解码为 str 类型")


# ============================================================
# 3. 测试 config.py — 配置加载
# ============================================================
def test_config():
    section("3. 测试 config.py — 配置加载")

    from common.config import load_gate_config, load_user_config

    # 3.1 加载 GateConfig
    config = load_gate_config(config_dir=_GATE_DIR)
    assert config.gate_network.ip == "192.168.1.107"
    assert config.gate_network.source_port == 9300
    assert config.gate_network.android_port == 9301
    assert config.db_server.ip == "192.168.1.107"
    assert config.db_server.db_server_port == 9302
    assert config.gate_db.user == "root"
    assert config.gate_db.password == "1234"
    assert config.gate_db.database == "gate_database"
    _ok("GateConfig.txt 加载正确，端口为 9300/9301/9302")

    # 3.2 加载 UserConfig
    user = load_user_config(config_dir=_GATE_DIR)
    assert user.username == "Jiang"
    assert user.password == "pwd"
    assert user.device_key == "A1"
    _ok("UserConfig.txt 加载正确")


# ============================================================
# 4. 测试 models.py — 共享状态线程安全
# ============================================================
def test_models():
    section("4. 测试 models.py — GatewayState 线程安全")

    from common.models import GatewayState
    from common.constants import DEFAULT_SENSOR_DATA, DEFAULT_THRESHOLD_DATA

    state = GatewayState()
    state.data_from_source = dict(DEFAULT_SENSOR_DATA)
    state.update_data(DEFAULT_THRESHOLD_DATA)

    # 4.1 基本属性读写
    assert state.login_status == 0
    state.login_status = 1
    assert state.login_status == 1
    _ok("login_status 读写正确")

    # 4.2 阈值操作
    state.set_threshold("Temperature", 30)
    assert state.get_threshold("Temperature") == 30
    assert state.threshold_data.get("Temperature") == 30
    _ok("set_threshold/get_threshold 正确")

    # 4.3 设备列表
    state.set_permitted_device(["esp_air", "esp_curtain"])
    assert state.is_device_permitted("esp_air") is True
    assert state.is_device_permitted("unknown") is False
    _ok("permitted_device/is_device_permitted 正确")

    # 4.4 sensor_ready_event
    assert state.source_start_flag == 0
    results = {"wait_done": False}

    def _waiter():
        state.wait_for_sensor(timeout=2)
        results["wait_done"] = True

    t = threading.Thread(target=_waiter, daemon=True)
    t.start()
    time.sleep(0.2)
    assert results["wait_done"] is False, "Event 不应提前触发"
    state.source_start_flag = 1  # 触发 event
    t.join(timeout=3)
    assert results["wait_done"] is True
    _ok("sensor_ready_event 等待/触发机制正确")

    # 4.5 并发写入安全性
    errors = []

    def _concurrent_writer(idx):
        try:
            for i in range(100):
                state.set_threshold(f"key_{idx}", i)
                state.update_data({f"data_{idx}": i})
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=_concurrent_writer, args=(i,)) for i in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)
    assert not errors, f"并发写入出错: {errors}"
    _ok("5 线程并发写入 threshold_data/data_from_source 无异常")

    # 4.6 get_data_snapshot 返回副本
    snap = state.get_data_snapshot()
    snap["Temperature"] = 999
    assert state.get_data_snapshot().get("Temperature") != 999
    _ok("get_data_snapshot 返回独立副本，外部修改不影响内部状态")


# ============================================================
# 5. 模拟 TCP 通信全链路测试
# ============================================================
def test_android_login_flow():
    """模拟 Android 登录的完整 TCP 通信流程。"""
    section("5. 模拟 Android 登录 TCP 通信链路")

    # 启动一个模拟 Android handler 服务端
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", 0))
    server_sock.listen(1)
    port = server_sock.getsockname()[1]

    # 模拟服务端行为：接收登录 JSON，发送 JSON 响应
    def _mock_android_handler():
        conn, _ = server_sock.accept()
        # 接收 Android 发来的 JSON
        data = recv_json(conn)
        from MyComm import decode_comm_data
        op, user_json, status = decode_comm_data(data)
        assert op == "login"
        _ok("服务端收到 login 操作码")

        user_data = json.loads(user_json) if isinstance(user_json, str) else user_json
        assert user_data["account"] == "Jiang"
        _ok("服务端正确解析用户名")

        # 模拟登录成功响应（新 JSON 格式）
        send_json(conn, {"status": 1})
        conn.close()

    from common.protocol import send_json, recv_json

    t = threading.Thread(target=_mock_android_handler, daemon=True)
    t.start()

    # 模拟 Android 客户端
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", port))

    # Android 发送登录请求（模拟 MyComm.java 的 format_comm_data）
    login_data = json.dumps({
        "op": "login",
        "data": json.dumps({"account": "Jiang", "password": "pwd", "device_Key": "NULL"}),
        "status": "1"
    })
    send_json(client, json.loads(login_data))
    _ok("Android 客户端发送 login JSON")

    # Android 接收响应（模拟新的 JSON 解析方式）
    response = recv_json(client)
    assert response == {"status": 1}
    _ok('Android 客户端收到 JSON 响应 {"status": 1}')

    client.close()
    server_sock.close()
    t.join(timeout=2)


def test_sensor_data_flow():
    """模拟设备节点上报传感器数据的完整流程。"""
    section("6. 模拟传感器数据 TCP 通信链路")

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", 0))
    server_sock.listen(1)
    port = server_sock.getsockname()[1]

    sensor_data = {
        "Light_TH": 1,
        "Temperature": 25.5,
        "Humidity": 60.2,
        "Light_CU": 0,
        "Brightness": 500,
        "Curtain_status": 0,
    }

    def _mock_sensor_receiver():
        from common.protocol import recv_json, send_line
        conn, _ = server_sock.accept()
        # 1. 接收设备 ID（纯文本行）
        device_id = recv_line(conn).strip()
        assert device_id == "esp_airconditioner"
        _ok("服务端收到设备 ID: esp_airconditioner")

        # 2. 发送 "start" 确认（纯文本行）
        send_line(conn, "start")
        _ok("服务端发送 'start' 确认")

        # 3. 接收传感器 JSON 数据
        data = recv_json(conn)
        assert data["Temperature"] == 25.5
        assert data["Humidity"] == 60.2
        _ok("服务端正确解析传感器 JSON 数据")

        # 4. 发送控制指令 JSON
        send_json(conn, {"Light_TH": 1, "Temperature": 30, "Humidity": 65})
        conn.close()

    from common.protocol import send_json, recv_json, send_line, recv_line

    t = threading.Thread(target=_mock_sensor_receiver, daemon=True)
    t.start()

    # 模拟 ESP8266 设备
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", port))

    # 1. 发送设备 ID（纯文本）
    send_line(client, "esp_airconditioner")
    _ok("设备发送 ID: esp_airconditioner")

    # 2. 接收 "start"
    resp = recv_line(client)
    assert resp == "start"
    _ok("设备收到 'start' 确认")

    # 3. 发送传感器数据（JSON + \n）
    send_json(client, sensor_data)
    _ok("设备发送传感器 JSON 数据")

    # 4. 接收控制指令
    control = recv_json(client)
    assert control["Temperature"] == 30
    _ok("设备收到控制指令 JSON")

    client.close()
    server_sock.close()
    t.join(timeout=2)


def test_db_server_protocol():
    """模拟网关与数据库服务器的 JSON 通信。"""
    section("7. 模拟网关<->数据库服务器 TCP 通信链路")

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind(("127.0.0.1", 0))
    server_sock.listen(1)
    port = server_sock.getsockname()[1]

    def _mock_db_server():
        from common.protocol import recv_json, send_json
        from MyComm import decode_comm_data, format_comm_data_string
        conn, _ = server_sock.accept()

        # 接收 check_device_id 请求
        req = recv_json(conn)
        op, data, status = decode_comm_data(req)
        assert op == "check_device_id"
        assert data == "A1"
        _ok("DB Server 收到 check_device_id 请求")

        # 返回设备列表（JSON 数组）
        devices = ["esp_airconditioner", "esp_curtain", "door_security"]
        send_json(conn, format_comm_data_string("check_device_id", devices, 1))
        _ok("DB Server 返回设备列表 JSON 数组")

        conn.close()

    from common.protocol import send_json, recv_json
    from MyComm import format_comm_data_string, decode_comm_data

    t = threading.Thread(target=_mock_db_server, daemon=True)
    t.start()

    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect(("127.0.0.1", port))

    # 网关发送 check_device_id
    send_json(client, format_comm_data_string("check_device_id", "A1", 1))
    _ok("网关发送 check_device_id 请求")

    # 网关接收设备列表
    resp = recv_json(client)
    op, data, status = decode_comm_data(resp)
    assert op == "check_device_id"
    assert status == 1
    assert isinstance(data, list)
    assert "esp_airconditioner" in data
    _ok("网关收到设备列表为 JSON 数组，包含 esp_airconditioner")

    client.close()
    server_sock.close()
    t.join(timeout=2)


def test_register_flow():
    """模拟注册流程：Android → 网关 → DB Server → 网关 → Android。"""
    section("8. 模拟注册全链路 TCP 通信")

    # 8.1 模拟 DB Server
    db_server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    db_server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    db_server_sock.bind(("127.0.0.1", 0))
    db_server_sock.listen(1)
    db_port = db_server_sock.getsockname()[1]

    from common.protocol import send_json, recv_json
    from MyComm import (
        format_comm_data_string, decode_comm_data,
        format_userdata_string, decode_user_data,
    )

    def _mock_db():
        conn, _ = db_server_sock.accept()
        req = recv_json(conn)
        op, data, status = decode_comm_data(req)
        assert op == "add_new_user"
        _ok("DB Server 收到 add_new_user")

        u, p, k = decode_user_data(data)
        assert u == "newuser"
        _ok("DB Server 正确解析用户信息")

        # 返回注册成功
        send_json(conn, format_comm_data_string("add_new_user", "NULL", 1))
        conn.close()

    db_thread = threading.Thread(target=_mock_db, daemon=True)
    db_thread.start()

    # 8.2 模拟网关（Android handler + DB client）
    gateway_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    gateway_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    gateway_sock.bind(("127.0.0.1", 0))
    gateway_sock.listen(1)
    gw_port = gateway_sock.getsockname()[1]

    def _mock_gateway():
        # 接受 Android 连接
        android_conn, _ = gateway_sock.accept()
        req = recv_json(android_conn)
        op, data, status = decode_comm_data(req)
        assert op == "register"
        _ok("网关收到 register 请求")

        user_data = json.loads(data) if isinstance(data, str) else data

        # 转发到 DB Server
        db_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        db_client.connect(("127.0.0.1", db_port))
        db_msg = format_comm_data_string(
            "add_new_user",
            format_userdata_string(user_data["account"], user_data["password"], user_data.get("device_Key", "")),
            1,
        )
        send_json(db_client, db_msg)

        db_resp = recv_json(db_client)
        _, _, db_status = decode_comm_data(db_resp)
        db_client.close()

        # 回复 Android
        send_json(android_conn, {"status": db_status})
        _ok(f"网关转发注册结果给 Android: status={db_status}")
        android_conn.close()

    gw_thread = threading.Thread(target=_mock_gateway, daemon=True)
    gw_thread.start()

    # 8.3 模拟 Android 客户端
    android_client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    android_client.connect(("127.0.0.1", gw_port))

    reg_data = {
        "op": "register",
        "data": json.dumps({"account": "newuser", "password": "newpwd", "device_Key": "B2"}),
        "status": "1",
    }
    send_json(android_client, reg_data)
    _ok("Android 发送 register JSON")

    response = recv_json(android_client)
    assert response == {"status": 1}
    _ok('Android 收到注册成功 JSON {"status": 1}')

    android_client.close()
    gateway_sock.close()
    db_server_sock.close()
    gw_thread.join(timeout=3)
    db_thread.join(timeout=3)


# ============================================================
# 主测试入口
# ============================================================
def main():
    print("=" * 60)
    print("  IoT 网关系统综合测试")
    print(f"  项目根目录: {_PROJECT_ROOT}")
    print("=" * 60)

    try:
        test_protocol()
    except Exception as e:
        _fail("test_protocol", str(e))
        import traceback
        traceback.print_exc()

    try:
        test_mycomm()
    except Exception as e:
        _fail("test_mycomm", str(e))
        import traceback
        traceback.print_exc()

    try:
        test_config()
    except Exception as e:
        _fail("test_config", str(e))
        import traceback
        traceback.print_exc()

    try:
        test_models()
    except Exception as e:
        _fail("test_models", str(e))
        import traceback
        traceback.print_exc()

    try:
        test_android_login_flow()
    except Exception as e:
        _fail("test_android_login_flow", str(e))
        import traceback
        traceback.print_exc()

    try:
        test_sensor_data_flow()
    except Exception as e:
        _fail("test_sensor_data_flow", str(e))
        import traceback
        traceback.print_exc()

    try:
        test_db_server_protocol()
    except Exception as e:
        _fail("test_db_server_protocol", str(e))
        import traceback
        traceback.print_exc()

    try:
        test_register_flow()
    except Exception as e:
        _fail("test_register_flow", str(e))
        import traceback
        traceback.print_exc()

    # 汇总
    print(f"\n{'='*60}")
    print(f"  测试结果: {_passed} 通过, {_failed} 失败, 共 {_passed + _failed} 项")
    if _errors:
        print(f"\n  失败详情:")
        for name, reason in _errors:
            print(f"    - {name}: {reason}")
    print(f"{'='*60}")

    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
