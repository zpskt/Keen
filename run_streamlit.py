import sys
import os
import ssl
import warnings
### 此文件是为了防止ssl导致无法开启
# 1. 先禁用SSL验证
os.environ['PYTHONHTTPSVERIFY'] = '0'

# 2. 配置使用certifi证书
try:
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
    os.environ['REQUESTS_CA_BUNDLE'] = certifi.where()
except ImportError:
    pass

# 3. 猴子补丁：让create_default_context不加载Windows证书
_original_create_default_context = ssl.create_default_context

def patched_create_default_context(purpose=ssl.Purpose.SERVER_AUTH, *args, **kwargs):
    try:
        return _original_create_default_context(purpose, *args, **kwargs)
    except Exception as e:
        warnings.warn(f"SSL context creation failed: {e}, using unverified context")
        return ssl._create_unverified_context()

ssl.create_default_context = patched_create_default_context

# 4. 启动streamlit
if __name__ == '__main__':
    from streamlit.web import cli
    sys.argv = ['streamlit', 'run', 'frontend/app.py']
    cli.main()