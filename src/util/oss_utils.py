# oss_utils.py
import os
import base64
from datetime import datetime
import oss2
from oss2.credentials import EnvironmentVariableCredentialsProvider


class OSSClient:
    """
    阿里云OSS操作客户端封装（基于 oss2 旧版SDK）
    """

    def __init__(self, bucket_name: str, endpoint: str = None, region: str = "cn-hangzhou"):
        """
        初始化OSS客户端
        :param bucket_name: OSS Bucket名称
        :param endpoint: OSS Endpoint，如果不指定则自动构造
        :param region: 地域，默认 cn-hangzhou
        """
        self.bucket_name = bucket_name
        self.region = region

        # 构造Endpoint（如果未指定）
        if endpoint is None:
            endpoint = f"https://oss-{region}.aliyuncs.com"

        # 从环境变量获取凭证
        auth = oss2.ProviderAuthV4(EnvironmentVariableCredentialsProvider())

        # 创建Bucket实例
        self.bucket = oss2.Bucket(auth, endpoint, bucket_name, region=region)

    def upload_image(self, image_base64: str, prefix: str = "fall-events") -> dict:
        """
        将Base64编码的图片上传到OSS（支持深度冷归档Bucket）
        :param image_base64: Base64编码的图片数据
        :param prefix: OSS目录前缀，默认 fall-events
        :return: 包含上传结果的信息字典
        """
        try:
            # 1. 解码Base64数据
            img_data = base64.b64decode(image_base64)

            # 2. 生成唯一的Object Key（文件名）
            timestamp_str = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            object_key = f"{prefix}/fall_{timestamp_str}.jpg"

            # 3. 【关键修改】设置上传头，强制存储类型为标准存储
            headers = {
                'x-oss-storage-class': 'Standard'  # 强制为标准类型，绕过Bucket的深度冷归档限制
            }

            # 4. 上传到OSS（带上headers参数）
            result = self.bucket.put_object(object_key, img_data, headers=headers)

            # 检查上传是否成功
            if result.status != 200:
                raise Exception(f"OSS上传失败，状态码: {result.status}")

            # 5. 构造图片访问URL
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

    def upload(self, input_data: str, prefix: str = "fall-events") -> dict:
        """
        智能上传：支持本地路径或Base64字符串
        """
        # 判断是文件路径还是Base64
        if os.path.exists(input_data):
            # 是文件路径
            with open(input_data, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
        else:
            # 当作Base64处理
            image_base64 = input_data

        return self.upload_image(image_base64, prefix)

    def generate_signed_url(self, object_key: str, expires_in: int = 3600) -> str:
        """
        生成带签名的临时访问URL（用于私有Bucket）
        :param object_key: OSS对象Key
        :param expires_in: 有效期（秒），默认3600秒（1小时）
        :return: 带签名的临时URL
        """
        try:
            # 生成预签名URL
            url = self.bucket.sign_url('GET', object_key, expires_in)
            return url
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
            self.bucket.delete_object(object_key)
            return True
        except Exception as e:
            print(f"删除OSS对象失败: {e}")
            return False


# ===== 测试入口 =====
if __name__ == '__main__':
    import os
    import base64

    # 1. 配置测试参数（请替换为你的实际值）
    BUCKET_NAME = "fall-detection-dev"  # 替换为你的Bucket名称
    REGION = "cn-beijing"  # 替换为你的Bucket地域

    # 2. 初始化OSS客户端
    client = OSSClient(bucket_name=BUCKET_NAME, region=REGION)

    # 3. 准备测试图片数据（从本地读取一张图片作为测试）
    test_image_path = "/datasets/img.png"  # 替换为你的本地图片路径

    if os.path.exists(test_image_path):
        with open(test_image_path, "rb") as f:
            image_bytes = f.read()
            test_base64 = base64.b64encode(image_bytes).decode('utf-8')
            print(f"✅ 已加载测试图片: {test_image_path}, Base64长度: {len(test_base64)}")
    else:
        print(f"⚠️ 未找到测试图片 {test_image_path}，请准备一张测试图片")
        exit(1)

    # 4. 执行上传测试
    print(f"📤 开始上传图片到 OSS Bucket: {BUCKET_NAME}")
    result = client.upload(test_base64, prefix="test-upload")

    # 5. 打印结果
    if result["success"]:
        print("✅ 上传成功!")
        print(f"   📁 Object Key: {result['object_key']}")
        print(f"   🔗 图片URL: {result['image_url']}")
        print(f"   📦 Bucket: {result['bucket']}")
        print(f"   🌍 Region: {result['region']}")
    else:
        print(f"❌ 上传失败: {result['error']}")