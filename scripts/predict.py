if __name__ == '__main__':
    from ultralytics import YOLO
    import cv2

    # Load a model
    model = YOLO("yolo26n-pose.pt")

    # Predict with the model
    results = model("datasets/img.png")

    # --- 1. 绘制并显示/保存结果 ---
    for result in results:
        # 直接在图像上绘制关键点和骨架
        annotated_img = result.plot()  # 返回BGR格式的图像

        # 显示图像
        cv2.imshow("Pose Estimation", annotated_img)
        cv2.waitKey(0)  # 按任意键关闭窗口
        cv2.destroyAllWindows()

        # 或者保存图像
        cv2.imwrite("datasets/pose_result.jpg", annotated_img)
        print("结果已保存至 pose_result.jpg")