#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2025/9/2 20:59
# @Author  : zhangpeng /zpskt
# @File    : upload_app.py
# @Software: PyCharm
from flask import Flask, request
import os

app = Flask(__name__)


# 设置一个路由，允许POST方法
@app.route('/upload', methods=['POST'])
def upload_file():
    # 检查请求中是否包含名为 'file' 的文件部分
    if 'file' not in request.files:
        return '没有找到文件部分', 400

    file = request.files['file']

    # 如果用户没有选择文件，浏览器可能会提交一个没有文件名的空部分
    if file.filename == '':
        return '没有选择文件', 400

    # 如果文件存在且合法，就保存它
    if file:
        # 直接使用客户端上传的文件名
        filename = file.filename
        # 将文件保存到当前运行目录下
        file.save(os.path.join(os.getcwd(), filename))
        return f'文件 {filename} 上传成功！', 200


if __name__ == '__main__':
    # 运行服务器，host='0.0.0.0' 允许所有IP访问，debug=True 提供调试信息
    app.run(host='0.0.0.0', port=6750, debug=True)