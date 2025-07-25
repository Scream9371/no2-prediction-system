import matplotlib
matplotlib.use('Agg')  # 设置非交互式后端，用于Web应用
import matplotlib.pyplot as plt
import io
import base64


def plot_prediction(dates, preds, lower, upper):
    plt.figure(figsize=(10, 5))
    plt.plot(dates, preds, label="预测NO₂")
    plt.fill_between(dates, lower, upper, color="gray", alpha=0.3, label="置信区间")
    plt.xlabel("时间")
    plt.ylabel("NO₂浓度")
    plt.legend()
    buf = io.BytesIO()
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    return img_base64
