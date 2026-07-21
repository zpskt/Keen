#!/usr/bin/env python
# -*- coding: UTF-8 -*-
'''
@Project ：Keen 
@File    ：oss_utils.py.py
@IDE     ：PyCharm 
@Author  ：张鹏
@Date    ：2026/7/22 01:15 
@Description： 
'''
# oss_utils.py
import os
import base64
from datetime import datetime
import alibabacloud_oss_v2 as oss


class OSSClient:
    """
    阿里云OSS操作客户端封装
    """

    def __init__(self, bucket_name: str, region: str = "cn-hangzhou"):
        """
        初始化OSS客户端
        :param bucket_name: OSS Bucket名称
        :param region: 地域，默认 cn-hangzhou
        """
        self.bucket_name = bucket_name
        self.region = region

        # 从环境变量获取凭证
        credentials_provider = oss.credentials.EnvironmentVariableCredentialsProvider()

        # 加载配置并设置凭证
        cfg = oss.config.load_default()
        cfg.credentials_provider = credentials_provider
        cfg.region = region

        # 如果使用自定义Endpoint，可以取消注释并设置
        # cfg.endpoint = f"oss-{region}.aliyuncs.com"

        self.client = oss.Client(cfg)

    def upload_image(self, image_base64: str, prefix: str = "fall-events") -> dict:
        """
        将Base64编码的图片上传到OSS
        :param image_base64: Base64编码的图片数据
        :param prefix: OSS目录前缀，默认 fall-events
        :return: 包含上传结果的信息字典
        """
        try:
            # 1. 解码Base64数据
            img_data = base64.b64decode(image_base64)

            # 2. 生成唯一的对象Key（文件名）
            timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            object_key = f"{prefix}/fall_{timestamp_str}.jpg"

            # 3. 上传到OSS
            put_result = self.client.put_object(
                oss.PutObjectRequest(
                    bucket=self.bucket_name,
                    key=object_key,
                    body=img_data,
                    # 可以附加自定义元数据
                    # metadata={
                    #     'source': source,
                    #     'event_type': 'fall',
                    # }
                )
            )

            # 4. 检查上传是否成功
            if put_result.status_code != 200:
                raise Exception(f"OSS上传失败，状态码: {put_result.status_code}")

            # 5. 构造图片访问URL
            # 注意：如果Bucket是私有读写，此URL需要签名才能访问
            image_url = f"https://{self.bucket_name}.oss-{self.region}.aliyuncs.com/{object_key}"

            return {
                "success": True,
                "object_key": object_key,
                "image_url": image_url,
                "bucket": self.bucket_name,
                "region": self.region
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def generate_signed_url(self, object_key: str, expires_in: int = 3600) -> str:
        """
        生成带签名的临时访问URL（用于私有Bucket）
        :param object_key: OSS对象Key
        :param expires_in: 有效期（秒），默认3600秒（1小时）
        :return: 带签名的临时URL
        """
        try:
            # 使用SDK生成预签名URL
            result = self.client.presign_url(
                oss.PresignUrlRequest(
                    bucket=self.bucket_name,
                    key=object_key,
                    method="GET",
                    expires_in=expires_in
                )
            )
            return result.url
        except Exception as e:
            print(f"生成签名URL失败: {e}")
            return None

    def delete_image(self, object_key: str) -> bool:
        """
        删除OSS中的图片
        :param object_key: OSS对象Key
        :return: 是否删除成功
        """
        try:
            self.client.delete_object(
                oss.DeleteObjectRequest(
                    bucket=self.bucket_name,
                    key=object_key
                )
            )
            return True
        except Exception as e:
            print(f"删除OSS对象失败: {e}")
            return False
