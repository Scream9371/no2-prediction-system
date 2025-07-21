# 基于机器学习大湾区的NO₂浓度预测与可视化系统

## 1. 项目概述

- **核心目标**：预测大湾区主要城市及地区未来24小时的大气NO₂浓度，展示变化折线图及预测区间。
- **主要功能**：
  - **数据采集**：通过和风天气API自动获取城市ID及近十天的空气质量和气象数据，存入数据库。
  - **数据处理**：对历史数据进行清洗、特征工程和标准化，为模型训练和预测做准备。
  - **模型训练与预测**：基于历史数据训练时间序列模型NC-CQR，用近十天数据预测未来24小时NO₂浓度及置信区间。
  - **前端可视化**：Flask后端接口，前端实时展示预测折线图和区间。
  - **定时任务**：定时采集数据、监控模型准确率并自动触发重训。

## 2. 项目结构

```bash
no2-prediction-system/
├── config/                     # 配置（环境变量、数据库、路径等）
│   ├── __init__.py
│   ├── settings.py
│   ├── database.py
│   └── paths.py                # data文件夹关键路径常量
│
├── database/                   # 数据库相关
│   ├── __init__.py
│   ├── models.py               # ORM模型定义
│   ├── crud.py                 # 增删改查
│   ├── schemas.py              # 数据序列化
│   └── session.py              # 会话管理
│
├── data/
│   ├── external/               # 外部数据（地理边界、城市坐标等）
│   │   ├── gba_boundary.geojson
│   │   └── cities.json
│   ├── ml_cache/               # 机器学习中间文件
│   │   ├── features/
│   │   └── scalers/
│   └── backup/                 # 数据库备份
│
├── ml/                         # 机器学习模块
│   ├── __init__.py
│   ├── models/
│   │   ├── trained/
│   │   └── retrained/
│   ├── notebooks/
│   │   ├── data_exploration.ipynb
│   │   └── model_tuning.ipynb
│   └── src/
│       ├── __init__.py
│       ├── data_loader.py
│       ├── data_processing.py
│       ├── train.py
│       ├── predict.py
│       ├── evaluate.py
│       └── retrain.py
│
├── api/
│   ├── __init__.py
│   ├── heweather/
│   │   ├── __init__.py
│   │   ├── client.py           # 获取城市ID和空气质量数据
│   │   ├── data_parser.py
│   │   └── constants.py
│   └── schedules/
│       ├── __init__.py
│       ├── data_collector.py   # 定时采集数据
│       └── monitor.py          # 监控准确率并自动重训
│
├── web/
│   ├── __init__.py
│   ├── app.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── main_routes.py
│   │   └── api_routes.py
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   ├── templates/
│   │   ├── base.html
│   │   ├── index.html
│   │   └── city.html
│   └── utils/
│       ├── __init__.py
│       ├── visualization.py
│       └── data_fetcher.py
│
├── scripts/
│   ├── setup_database.py
│   ├── run_data_collector.py
│   └── run_pipeline.py
│
├── tests/
│   ├── unit/
│   │   ├── test_data_processing.py
│   │   └── test_predict.py
│   └── integration/
│       ├── test_api.py
│       └── test_web.py
│
├── .env                        # 环境变量（API密钥、数据库等）
├── .gitignore                  # git忽略
├── requirements.txt
└── README.md
```

## 3. 实现说明

- **API采集**：`api/heweather/client.py`定义获取城市ID和历史十天天气及空气质量数据的API客户端，密钥等配置在`.env`。
- **数据入库**：采集到的数据通过`database/crud.py`写入数据库，结构定义见`database/models.py`。
- **数据采集**：`api/schedules/data_collector.py`采集过去十天的历史数据。
- **特征工程与标准化**：`ml/src/data_processing.py`负责数据清洗、特征提取和标准化，标准化器缓存于`data/ml_cache/scalers/`。
- **模型训练与预测**：`ml/src/train.py`训练模型，`ml/src/predict.py`用于预测未来24小时NO₂浓度及置信区间。
- **模型评估**：`ml/src/evaluate.py`评估预测准确率。
- **前端可视化**：`web/app.py`为Flask主程序，`web/routes/`定义路由，`web/utils/visualization.py`生成预测折线图，前端页面见`web/templates/`。

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
      ```

   > 提示：ed25519密钥生成以及使用方式详情见和风天气官方文档[身份认证](https://dev.qweather.com/docs/configuration/authentication/)。

3. **初始化数据库**
   ```bash
   python  -m scripts.setup_database
   ```

4. **采集历史数据**
   ```bash
   python -m scripts.run_data_collector 
   ```

5. **训练模型**
   ```bash
   python -m scripts.run_pipeline
   ```

6. **启动Web前端**
   ```bash
   python -m web.app.py
   ```
   访问 http://localhost:5000 查看预测结果和可视化图表。

7. **自动化运行**
   - 可用crontab或Windows任务计划定时运行`scripts/run_data_collector.py`和`scripts/run_pipeline.py`，实现数据自动采集与模型自动更新。

## 5. 其他说明

- **测试**：运行`pytest tests/`进行单元和集成测试。
- **模型手动训练**：进入项目根目录运行NC-CQR算法控制脚本，可对模型进行精细化调整
   ```bash
   python -m ml.src.control -h            # 查看脚本使用帮助
   ```
   运行模式: train(训练), predict(预测), evaluate(评估)

   | 选项 | 说明 |
   | --- | --- |
   |-h, --help | show this help message and exit |
   |--city CITY | 城市名称 (默认: dongguan) |
   |--steps STEPS | 预测步数(小时) (默认: 24) |
   |--epochs EPOCHS | 训练轮数 (默认: 150) |
   |--batch-size BATCH_SIZE | 批次大小 (默认: 32) |
   |--learning-rate LEARNING_RATE | 学习率 (默认: 1e-3) |
   |--save-chart | 保存预测图表 |
   |--list-cities | 列出支持的城市 |

   使用举例：
   ```bash
   python -m ml.src.control train --city dongguan --step 12   # 训练模型预测东莞城市未来12小时的NO₂浓度
   ```
- **模型与数据缓存**：所有模型存储在`ml/models/`中，所有标准化器和特征工程结果均缓存于`data/ml_cache/`，便于快速预测和重训。
- **可扩展性**：支持添加新城市、切换模型、调整预测区间等。
