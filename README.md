<div align="center">

# Edge Computing IoT Gateway System
### 边缘计算物联网智能网关系统

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.7+-green.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg)](https://github.com)
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)](https://github.com)

基于ESP8266的物联网智能网关系统，实现智能空调、窗帘、门禁等设备的统一管理和控制

[功能特性](#-功能特性) • [系统架构](#-系统架构) • [快速开始](#-快速开始) • [文档](#-文档) • [许可证](#-许可证)

</div>

---

## 📜 版权声明

Copyright (c) 2024-2026 Edge Computing IoT Gateway Contributors

本项目采用 [MIT License](LICENSE) 开源协议。您可以自由地使用、修改、分发本软件，但需保留原始版权声明和许可证副本。

**核心条款**：
- ✅ 商业用途允许
- ✅ 修改允许
- ✅ 分发允许
- ✅ 私人使用允许
- ⚠️ 需保留版权声明
- ⚠️ 需包含许可证副本
- ❌ 不提供担保
- ❌ 作者不承担责任

完整许可证文本请查看 [LICENSE](LICENSE) 文件。

---

## 🌟 功能特性

### 核心功能
- 🔌 **统一网关管理** - Python网关统一管理所有IoT设备
- 🏠 **多设备支持** - 空调、窗帘、门禁等多种智能设备
- 📱 **移动端控制** - Android应用实现远程控制和监控
- 🧠 **智能决策** - 基于传感器数据的自动化设备控制
- ⚙️ **集中配置** - 配置文件统一管理，易于维护
- 🗄️ **数据持久化** - MySQL数据库存储历史数据
- ☁️ **云端集成** - 支持阿里云IoT平台数据上传
- 🔐 **安全认证** - 用户身份验证和设备授权

### 技术特点
- 🎯 **生产就绪** - 完整的测试覆盖，系统稳定可靠
- 🔧 **健康检查** - 自动化工具验证系统状态
- 📊 **实时监控** - 设备状态实时上报和展示
- 🚀 **高性能** - 支持多设备并发连接
- 🛠️ **易扩展** - 模块化设计，易于添加新设备

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    IoT 智能网关系统架构                      │
└─────────────────────────────────────────────────────────────┘

                    ┌──────────────┐
                    │   Android    │
                    │     App      │ (端口 9301)
                    └──────┬───────┘
                           │ TCP
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Python 边缘网关服务器                      │
│  ┌────────────────────────────────────────────────────┐    │
│  │  • 设备通信模块 (端口 9300)                        │    │
│  │  • Android通信模块 (端口 9301)                      │    │
│  │  • 数据库服务器连接 (端口 9302)                     │    │
│  │  • 智能决策引擎                                     │    │
│  │  • 阿里云IoT上传模块                               │    │
│  │  • 数据预处理与分析                                 │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
        │               │               │
        ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  空调单元    │  │  窗帘单元    │  │  门禁单元    │
│ (A1_tem_hum) │  │ (A1_curtain) │  │ (A1_security)│
│   ESP8266    │  │   ESP8266    │  │   ESP8266    │
└─────────────┘  └─────────────┘  └─────────────┘
     传感器          传感器          传感器
    DHT11          BH1750          MFRC522
```

---

## 🚀 快速开始

### 前置要求

- Python 3.7+
- MySQL 5.7+
- Arduino IDE (用于设备固件上传)
- Android Studio (用于应用构建)

### 安装步骤

#### 1. 克隆项目

```bash
git clone https://github.com/yourusername/edge-computing-iot-gateway.git
cd edge-computing-iot-gateway
```

#### 2. 配置环境

```bash
# 安装Python依赖
cd Python
pip install -r requirements.txt

# 配置网关
# 编辑 Python/Gate/GateConfig.txt
```

#### 3. 初始化数据库

```bash
# 创建数据库
mysql -u root -p < Python/Database\ Server/init_database.sql

# 启动数据库服务器
cd Python/Database\ Server
python database_process_server.py
```

#### 4. 启动网关

```bash
# 生产模式
cd Python/Gate
python gate.py

# 测试模式（无需数据库）
python gate_test.py --test
```

#### 5. 上传设备固件

使用Arduino IDE上传各设备的固件：
- `Device Unit code/esp8266_airconditioner_unit/` - 空调单元
- `Device Unit code/esp8266_curtain_unit/` - 窗帘单元
- `Device Unit code/esp8266_doorsecurity_unit/` - 门禁单元

#### 6. 安装Android应用

```bash
cd Android\ IoT\ APP
./gradlew assembleDebug
# 安装APK到设备
```

### 健康检查

运行健康检查确保系统配置正确：

```bash
cd Python/scripts
python health_check.py
```

预期输出：`✓ 所有检查通过！系统配置良好。`

---

## 📁 项目结构

```
edge-computing-iot-gateway/
├── Python/                         # Python网关服务器
│   ├── Gate/                       # 网关主程序
│   │   ├── gate.py                # 主入口
│   │   ├── gate_test.py           # 测试版入口
│   │   ├── GateConfig.txt         # 网关配置
│   │   ├── UserConfig.txt         # 用户配置
│   │   ├── android_handler.py     # Android通信处理
│   │   ├── sensor_handler.py      # 传感器数据处理
│   │   ├── database.py            # 本地数据库
│   │   └── aliyun_handler.py      # 阿里云IoT集成
│   ├── Database Server/            # 数据库服务器
│   │   ├── database_process_server.py
│   │   ├── init_database.sql
│   │   └── serverConfig.txt
│   ├── common/                     # 公共模块
│   │   ├── config.py              # 配置管理
│   │   ├── constants.py           # 常量定义
│   │   ├── models.py              # 数据模型
│   │   ├── protocol.py            # 通信协议
│   │   └── log_setup.py           # 日志配置
│   └── scripts/                    # 工具脚本
│       ├── generate_device_config.py
│       ├── health_check.py
│       └── test_database_server.py
│
├── Android IoT APP/                # Android移动应用
│   └── app/src/main/
│       ├── assets/config.properties
│       └── java/
│
├── Device Unit code/               # 设备单元固件
│   ├── config_template.h          # 配置模板
│   ├── esp8266_airconditioner_unit/
│   ├── esp8266_curtain_unit/
│   └── esp8266_doorsecurity_unit/
│
├── README.md                       # 项目文档（本文件）
├── DEPLOYMENT_GUIDE.md            # 部署指南
├── DEVELOPER_GUIDE.md             # 开发者文档
├── QUICK_REFERENCE.md             # 快速参考
└── LICENSE                        # 开源许可证
```

---

## 📖 文档

- **[部署指南](DEPLOYMENT_GUIDE.md)** - 详细的部署步骤和环境配置
- **[开发者文档](DEVELOPER_GUIDE.md)** - 系统架构、API参考和开发指南
- **[快速参考](QUICK_REFERENCE.md)** - 常用命令和配置速查

---

## 🛠️ 技术栈

### 后端
- **Python 3.7+** - 网关服务器
- **MySQL** - 数据持久化
- **Socket** - TCP通信
- **Threading** - 多线程处理

### 前端
- **Android (Java)** - 移动应用
- **Material Design** - UI设计

### 嵌入式
- **ESP8266** - 设备单元核心
- **Arduino** - 固件开发

### 云服务
- **阿里云IoT** - 云平台集成

---

## 🔧 配置说明

### 端口分配

| 端口 | 服务 | 说明 |
|------|------|------|
| 9300 | 设备单元 | ESP8266设备连接 |
| 9301 | Android应用 | 移动应用连接 |
| 9302 | 数据库服务器 | 数据库进程通信 |
| 3306 | MySQL | 数据库连接 |

### 设备说明

| 设备 | 设备ID | 功能 | 传感器 |
|------|--------|------|--------|
| 智能空调 | A1_tem_hum | 温湿度监控 | DHT11 |
| 智能窗帘 | A1_curtain | 光照度监控、窗帘控制 | BH1750 |
| 智能门禁 | A1_security | 门禁控制 | MFRC522 |

---

## 🧪 测试

### 运行测试

```bash
# 健康检查
python Python/scripts/health_check.py

# 数据库服务器测试
python Python/scripts/test_database_server.py

# 设备模拟器
python Python/scripts/simulator_device.py

# Android模拟器
python Python/scripts/simulator_android.py
```

### 测试覆盖率

- ✅ 配置文件验证
- ✅ 端口配置一致性
- ✅ 设备通信测试
- ✅ Android通信测试
- ✅ 数据库连接测试
- ✅ 异常处理测试

---

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 如何贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 贡献规范

- 遵循现有的代码风格
- 更新相关文档
- 添加必要的测试
- 确保所有测试通过

---

## 🐛 故障排查

### 常见问题

**Q: 设备无法连接网关？**
- 检查WiFi配置是否正确
- 确认网关IP地址配置
- 运行健康检查工具诊断

**Q: Android应用连接失败？**
- 确认端口配置为9301
- 检查网关IP地址
- 验证网络连接

**Q: 数据库连接错误？**
- 确认MySQL服务已启动
- 检查数据库配置信息
- 运行数据库服务器测试脚本

更多问题请参考 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) 的故障排查章节。

---

## 📄 许可证

本项目采用 [MIT License](LICENSE) 开源协议。

```
MIT License

Copyright (c) 2024-2026 Edge Computing IoT Gateway Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 👥 作者与贡献者

- **项目创建者** - 初始架构设计与核心开发
- **贡献者** - 查看贡献列表

感谢所有为这个项目做出贡献的人！

---

## 📞 联系方式

- **问题反馈** - 请使用 [GitHub Issues](https://github.com/yourusername/edge-computing-iot-gateway/issues)
- **功能建议** - 欢迎提交 Feature Request
- **安全漏洞** - 请发送邮件至 security@example.com

---

## 🙏 致谢

感谢以下开源项目和技术支持：

- [Python](https://www.python.org/)
- [Arduino](https://www.arduino.cc/)
- [Android](https://www.android.com/)
- [ESP8266](https://www.espressif.com/)
- [阿里云IoT](https://www.aliyun.com/product/iot)

---

<div align="center">

**如果这个项目对您有帮助，请给一个 ⭐️ Star！**

Made with ❤️ by Edge Computing IoT Gateway Team

**系统状态**: ✅ 生产就绪

</div>
