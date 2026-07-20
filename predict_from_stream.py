if __name__ == '__main__':
    from ultralytics import YOLO
    import cv2

    # Load a model
    model = YOLO("yolo26l-pose.pt")

    # --- 打开摄像头 (0 代表默认摄像头) ---
    cap = cv2.VideoCapture(0)  # 如果 0 不行，尝试 1

    if not cap.isOpened():
        print("无法打开摄像头")
        exit()

    # --- 循环读取帧 ---
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            print("读取帧失败")
            break

        # 在每一帧上进行预测
        results = model(frame)  # 直接传入帧

        # 绘制结果
        for result in results:
            annotated_frame = result.plot()  # 绘制关键点和骨架

            # 在图像上添加文字信息（可选）
            cv2.putText(annotated_frame, "Press 'q' to quit", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # 显示实时画面
            cv2.imshow("YOLO Pose Estimation - Real-time", annotated_frame)

        # 按 'q' 键退出
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    # --- 释放资源 ---
    cap.release()
    cv2.destroyAllWindows()
    print("已退出摄像头识别")