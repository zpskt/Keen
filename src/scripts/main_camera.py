import random

import cv2

from src.core.detect_fall_engine import process_frame
import os
from datetime import datetime

from logger_utils import get_logger

# ===== 初始化日志 =====
logger = get_logger('main_camera')
if __name__ == '__main__':
    cap = cv2.VideoCapture(0)  # 或视频文件路径
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        annotated_frame, status = process_frame(frame)
        cv2.imshow("Fall Detection", annotated_frame)
        # 5. 显示或保存结果
        if annotated_frame is not None and status == 'fall':
            # 1. 确保 output 文件夹存在
            output_dir = "output"
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)  # 创建文件夹
                logger.info(f"📁 已创建文件夹: {output_dir}")

            # 2. 生成文件名
            time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
            random_number = time_str + '_random_' + str(random.randint(100, 999))
            save_path = os.path.join(output_dir, f"fall_{random_number}.jpg")

            # 3. 保存图片并检查是否成功
            success = cv2.imwrite(save_path, annotated_frame)
            # cv2.imshow("Result", annotated_frame)
            # cv2.waitKey(0)
            # cv2.destroyAllWindows()
            # 也可以保存结果
            logger.info(f"✅ 处理完成，状态: {status}")
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()