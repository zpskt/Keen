# 关键点索引常量
from datetime import datetime

NOSE = 0
LEFT_EYE = 1
RIGHT_EYE = 2
LEFT_EAR = 3
RIGHT_EAR = 4
LEFT_SHOULDER = 5
RIGHT_SHOULDER = 6
LEFT_ELBOW = 7
RIGHT_ELBOW = 8
LEFT_WRIST = 9
RIGHT_WRIST = 10
LEFT_HIP = 11
RIGHT_HIP = 12
LEFT_KNEE = 13
RIGHT_KNEE = 14
LEFT_ANKLE = 15
RIGHT_ANKLE = 16
def is_falling(keypoints_np, angle_threshold=45, conf_threshold=0.5):
    """
    根据关键点判断是否跌倒
    keypoints_np: numpy数组, shape (17, 3) 或 (17, 2)
    angle_threshold: 躯干与垂直方向的夹角阈值（度）
    """
    # 1. 检查关键点置信度 (如果有)
    # 假设 keypoints_np 是 (17, 3), 第三维是置信度
    if keypoints_np.shape[1] == 3:
        if keypoints_np[LEFT_SHOULDER][2] < conf_threshold or keypoints_np[RIGHT_HIP][2] < conf_threshold:
            return False  # 关键点不可靠

    # 2. 提取坐标 (如果包含置信度, 只取前两列)
    pts = keypoints_np[:, :2] if keypoints_np.shape[1] >= 2 else keypoints_np

    # 3. 计算肩膀中心和臀部中心
    shoulder_center = (pts[LEFT_SHOULDER] + pts[RIGHT_SHOULDER]) / 2
    hip_center = (pts[LEFT_HIP] + pts[RIGHT_HIP]) / 2

    # 4. 计算躯干向量 (臀部 → 肩膀)
    torso_vec = shoulder_center - hip_center

    # 5. 计算与垂直方向 (向上) 的夹角
    vertical_vec = np.array([0, -1])
    cos_angle = np.dot(torso_vec, vertical_vec) / (np.linalg.norm(torso_vec) * np.linalg.norm(vertical_vec))
    angle_deg = np.arccos(np.clip(cos_angle, -1.0, 1.0)) * 180 / np.pi

    # 6. 判断
    if angle_deg > angle_threshold:
        return True
    else:
        return False

if __name__ == '__main__':
    from ultralytics import YOLO
    import cv2

    # Load a model
    model = YOLO("yolo26n-pose.pt")

    # Predict with the model
    results = model("datasets/fall.jpg")

    for result in results:
        # 1. 检查是否检测到关键点
        if result.keypoints is not None:
            # 2. 提取关键点数据 (假设只有一个人)
            # 注意: keypoints.data 的形状通常是 [1, 17, 3] (1个人, 17个关键点, x,y,conf)
            keypoints_data = result.keypoints.data[0]  # 取第一个人

            # 3. 转换为NumPy数组方便操作
            import numpy as np

            kpts_np = keypoints_data.cpu().numpy()

            # 4. 判断姿态
            if is_falling(kpts_np, angle_threshold=50):  # 阈值可调
                print("⚠️ 检测到跌倒姿态! 正在保存图像...")

                # --- 绘制并保存图像 ---
                # 获取绘制好关键点和骨架的图像
                annotated_img = result.plot()  # 返回BGR格式图像

                # 在图像上添加文字标注 (可选)
                cv2.putText(annotated_img, "FALL DETECTED!", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                # 生成带时间戳的文件名，避免覆盖
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                save_path = f"fall_detected_{timestamp}.jpg"

                # 保存图像到当前目录
                success = cv2.imwrite(save_path, annotated_img)
                if success:
                    print(f"✅ 图像已保存至: {save_path}")
                else:
                    print("❌ 图像保存失败")

                # (可选) 显示图像
                cv2.imshow("Fall Detection", annotated_img)
                cv2.waitKey(0)
                cv2.destroyAllWindows()
            else:
                print("✅ 姿态正常")

        else:
            print("未检测到关键点")