# 基于机器学习大湾区的NO₂浓度预测与可视化系统

## 1. 项目概述

- **核心目标**：预测大湾区主要城市及地区未来24小时的大气NO₂浓度，展示变化折线图及预测区间。
- **主要功能**：
    - **数据采集**：通过和风天气API自动获取城市ID及近十天的空气质量和气象数据，存入数据库。
    - **数据处理**：对历史数据进行清洗、特征工程和标准化，为模型训练和预测做准备。
    - **模型训练与预测**：基于历史数据训练时间序列模型NC-CQR，用近三十天数据预测未来24小时NO₂浓度及置信区间。
    - **前端可视化**：Flask后端接口，前端实时展示预测折线图和区间。
    - **定时任务**：定时采集数据、监控模型准确率并自动触发重训。

## 2. 项目结构

```bash
no2-prediction-system/
├── config/                     # 配置（环境变量、数据库、路径等）
│   ├── __init__.py
│   ├── cities.py               # 城市配置和映射
│   ├── database.py             # 数据库连接配置
│   ├── paths.py                # 路径常量定义
│   └── settings.py             # 系统设置
│
├── database/                   # 数据库相关
│   ├── __init__.py
│   ├── crud.py                 # 增删改查操作
│   ├── models.py               # ORM模型定义
│   └── session.py              # 会话管理
│
├── data/                       # 数据目录
│   ├── ml_cache/               # 机器学习缓存文件
│   │   ├── features/           # 特征工程缓存
│   │   └── scalers/            # 数据标准化器（按城市分离）
│   └── backup/                 # 数据库备份文件
│
├── ml/                         # 机器学习模块
│   ├── __init__.py
│   ├── models/                 # 模型存储（版本控制）
│   │   ├── __init__.py
│   │   ├── daily/              # 按日期版本的模型
│   │   └── latest/             # 最新模型链接
│   └── src/                    # 核心算法实现
│       ├── __init__.py
│       ├── control.py          # NC-CQR控制脚本
│       ├── data_loader.py      # 数据加载器
│       ├── data_processing.py  # 数据预处理
│       ├── evaluate.py         # 模型评估
│       ├── predict.py          # 预测模块
│       └── train.py            # 模型训练
│
├── outputs/                    # 输出文件目录
│   ├── ml_cache/               # 控制脚本专用缓存
│   │   ├── features/
│   │   └── scalers/
│   ├── models/                 # 控制脚本模型输出
│   │   └── __init__.py
│   └── predictions/            # 预测结果输出（包含csv表格预测数据和png折线图）
│
├── api/                        # API相关
│   ├── __init__.py
│   ├── heweather/              # 和风天气API集成
│   │   ├── __init__.py
│   │   ├── client.py           # API客户端（JWT认证）
│   │   └── data_parser.py      # 数据解析器
│   └── schedules/              # 定时任务
│       ├── __init__.py
│       └── data_collector.py   # 定时数据采集
│
├── web/                        # Web应用
│   ├── __init__.py
│   ├── app.py                  # Flask应用入口
│   ├── routes/                 # 路由定义
│   │   ├── __init__.py
│   │   ├── api_routes.py       # API接口路由
│   │   └── main_routes.py      # 主页面路由
│   ├── static/                 # 静态资源
│   │   ├── images/             # 城市背景图片
│   │   └── js/                 # JavaScript相关类型定义
│   └── templates/              # HTML模板
│       ├── city.html           # 城市详情页
│       └── index.html          # 主页模板
│
├── scripts/                    # 执行脚本
│   ├── run_data_collector.py   # 数据采集脚本
│   ├── run_databackup.py       # 数据备份脚本
│   ├── run_pipeline.py         # 模型训练管道
│   └── setup_database.py       # 数据库初始化
│
├── tests/                      # 测试文件
│
├── utils/                      # 工具函数
│   ├── __init__.py
│   └── auth.py                 # 认证相关工具
│
├── CLAUDE.md                   # 项目开发指导文档
├── .env                        # 环境变量（API密钥、数据库等）
├── ed25519-private.pem         # 和风天气API私钥
├── ed25519-public.pem          # 和风天气API公钥
├── requirements.txt            # Python依赖
└── README.md                   # 项目说明文档
```

## 3. 实现说明

- **API采集**：[`api/heweather/client.py`](api/heweather/client.py)
  定义获取城市ID和历史十天天气及空气质量数据的API客户端，支持JWT认证，密钥等配置在[`.env`](.env)。
- **数据入库**：采集到的数据通过[`database/crud.py`](database/crud.py)写入数据库，结构定义见[
  `database/models.py`](database/models.py)，支持11个城市的分表存储。
- **数据采集**：[`api/schedules/data_collector.py`](api/schedules/data_collector.py)采集过去十天的历史数据，支持防重复插入机制。
- **城市配置**：[`config/cities.py`](config/cities.py)管理城市ID映射和配置，[`config/paths.py`](config/paths.py)定义项目路径常量。
- **数据加载**：[`ml/src/data_loader.py`](ml/src/data_loader.py)负责从数据库加载数据，使用30天滑动窗口（720小时）获取训练数据。
- **特征工程与标准化**：[`ml/src/data_processing.py`](ml/src/data_processing.py)
  负责数据清洗、特征提取和标准化，标准化器按城市分离缓存于[`data/ml_cache/scalers/`](data/ml_cache/scalers/)。
- **模型训练与预测**：
    - **训练管道**：[`ml/src/train.py`](ml/src/train.py)训练NC-CQR模型，[
      `scripts/run_pipeline.py`](scripts/run_pipeline.py)提供批量训练和版本控制
    - **控制脚本**：[`ml/src/control.py`](ml/src/control.py)提供独立的训练、预测、评估功能
    - **预测模块**：[`ml/src/predict.py`](ml/src/predict.py)用于预测未来24小时NO₂浓度及95%置信区间
- **模型版本控制**：
    - **训练管道模型**：存储在[`ml/models/daily/`](ml/models/daily/)（按日期版本）和[
      `ml/models/latest/`](ml/models/latest/)（最新版本链接）
    - **控制脚本模型**：存储在[`outputs/models/`](outputs/models/)
- **模型评估**：[`ml/src/evaluate.py`](ml/src/evaluate.py)评估预测准确率和置信区间覆盖率。
- **前端可视化**：[`web/app.py`](web/app.py)为Flask主程序，[`web/routes/`](web/routes/)
  定义路由，前端使用Chart.js生成预测折线图，支持城市背景图片和健康建议，前端页面见[`web/templates/`](web/templates/)。
- **工具函数**：[`utils/auth.py`](utils/auth.py)提供认证相关工具函数。

## 4. 使用方法

1. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

2. **配置环境变量**
    - 在根目录下创建`.env`存储环境变量，填写和风天气API密钥、数据库连接等信息。
    - `.env`所需变量信息如下
       ``` env
       HF_API_HOST=your_api_host  # 和风天气个人账号的API HOST
       HF_PRIVATE_KEY_FILE=ed25519-private.pem  # ed25519私钥路径，放在根目录
       HF_PROJECT_ID=your_project_id  # 和风天气项目ID
       HF_KEY_ID=your_credential_id  # 和风天气凭据ID
       DATABASE_URL=mysql+pymysql://<username>:<your_password>.@localhost:3306/<database>  # MySQL数据库地址
       BACKEND_BASE_URL=http://localhost:5000  # 本地开发环境 
       ```

   >
   提示：ed25519密钥生成以及使用方式详情见和风天气官方文档[身份认证](https://dev.qweather.com/docs/configuration/authentication/)。

3. 启动 MySQL 服务
    ```bash
    net start <your-service-name>
    ```

4. **初始化数据库**
   ```bash
   python  -m scripts.setup_database
   ```
   >
   注意！此操作会清除数据库中所有数据表以重新创建，你的数据库中的所有数据会被清除，若你的数据库中已经存有历史的NO₂数据，建议在执行此操作前先对原数据进行备份。备份操作参见[其他说明](#5-其他说明)。

5. **采集历史数据**
   ```bash
   python -m scripts.run_data_collector
   ```

6. **训练模型**
   ```bash
   python -m scripts.run_pipeline
   ```

7. **启动Web系统**

    - **后端服务启动**
      执行以下命令启动后端服务：
      ```bash
      python -m web.app
      ```
      成功启动后，终端将输出类似以下信息：
      ```bash
      * Serving Flask app 'app'
      * Debug mode: on
      * Running on http://127.0.0.1:5000
      Press CTRL+C to quit
      * Restarting with stat
      * Debugger is active!
      * Debugger PIN: 274-107-827
      ```
      上述输出表明：Flask应用已在本地5000端口成功启动，处于开发模式。
      可通过访问 [http://127.0.0.1:5000](http://127.0.0.1:5000) 查看预测结果和可视化图表。

    - **Web系统构成**
        - 前端页面：基于HTML、CSS和JavaScript实现，使用Chart.js进行数据可视化
        - 后端服务：基于Flask框架开发，提供数据接口和页面路由
        - 核心接口：
            - 城市列表接口：`/api/cities` - 获取所有支持的城市信息
            - 预测接口：`/api/predict/no2/<city_id>` - 获取指定城市的NO₂预测数据
            - 历史数据接口：`/api/no2/<city_id>` - 获取指定城市的历史NO₂数据

    - **访问方式**
      打开浏览器访问[http://127.0.0.1:5000](http://127.0.0.1:5000)即可使用系统，操作流程如下：
        - 在搜索框输入城市名（如"广州"、"深圳"），从下拉列表选择目标城市
        - 系统将自动加载并展示该城市未来24小时的NO₂浓度预测结果
        - 图表中包含预测值曲线和95%置信区间

    - **Web系统功能说明**
        - 城市搜索：支持模糊查询，快速定位大湾区城市
        - 数据可视化：通过折线图直观展示NO₂浓度预测趋势
        - 预测详情：显示未来24小时每小时的预测值及置信区间
        - 城市切换：可通过搜索框快速切换不同城市查看预测结果

8. **自动化运行**
    - 可用crontab或Windows任务计划定时运行`python -m scripts.run_data_collector`和`python -m scripts.run_pipeline`
      ，实现数据自动采集与模型自动更新。

## 5. 其他说明

- **数据备份**：备份数据到[`data/backup`](data/backup)
    ```bash
    python -m scripts.run_databackup         # 备份数据库数据到CSV文件
    ```
- **测试**：运行`pytest tests/`进行单元和集成测试。
- **模型手动训练**：进入项目根目录运行NC-CQR算法控制脚本，可对模型进行精细化调整。
    ```bash
    python -m ml.src.control -h            # 查看脚本使用帮助
    ```
  运行模式: train(训练), predict(预测), evaluate(评估)

  | 选项                            | 说明                              |
  |-------------------------------|---------------------------------|
  | -h, --help                    | show this help message and exit |
  | --city CITY                   | 城市名称 (默认: dongguan)             |
  | --steps STEPS                 | 预测步数(小时) (默认: 24)               |
  | --epochs EPOCHS               | 训练轮数 (默认: 150)                  |
  | --batch-size BATCH_SIZE       | 批次大小 (默认: 32)                   |
  | --learning-rate LEARNING_RATE | 学习率 (默认: 1e-3)                  |
  | --save-chart                  | 保存预测图表                          |
  | --list-cities                 | 列出支持的城市                         |

  使用举例：
    ```bash
    python -m ml.src.control train --city dongguan --step 12   # 训练模型预测东莞城市未来12小时的NO₂浓度
    ```
- **模型与数据缓存**：
    - **训练管道**：模型存储在`ml/models/daily/`（按日期版本）和`ml/models/latest/`（最新版本），标准化器缓存于
      `data/ml_cache/scalers/`
    - **控制脚本**：模型存储在`outputs/models/`，专用缓存在`outputs/ml_cache/`，预测结果保存在`outputs/predictions/`
    - **数据备份**：数据库备份自动保存在`data/backup/`目录，按城市分离
    > 上述目录会在执行脚本后自动创建，不会被版本追踪。
- **可扩展性**：支持添加新城市、切换模型、调整预测区间等。
