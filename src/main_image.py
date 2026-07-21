# src/main_image.py
import random
import os
import cv2
from detect_fall_and_push import process_frame  # 确保导入正确
from datetime import datetime
if __name__ == '__main__':
    # 1. 明确指定你要检测的图片路径
    image_path = "datasets/img.png"  # 请替换为你的实际图片路径

    # 2. 使用 OpenCV 读取图片
    frame = cv2.imread(image_path)

    # 3. 检查图片是否成功读取
    if frame is None:
        print(f"❌ 无法读取图片: {image_path}")
        exit()

    # 4. 调用处理函数
    annotated_frame, status = process_frame(frame)

    # 5. 显示或保存结果
    if annotated_frame is not None:
        # 1. 确保 output 文件夹存在
        output_dir = "output"
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)  # 创建文件夹
            print(f"📁 已创建文件夹: {output_dir}")

        # 2. 生成文件名
        time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_number = time_str+'_random_' + str(random.randint(100, 999))
        save_path = os.path.join(output_dir, f"fall_{random_number}.jpg")

        # 3. 保存图片并检查是否成功
        success = cv2.imwrite(save_path, annotated_frame)
        # cv2.imshow("Result", annotated_frame)
        # cv2.waitKey(0)
        # cv2.destroyAllWindows()
        # 也可以保存结果
        print(f"✅ 处理完成，状态: {status}")
    else:
        print("❌ 处理失败")