# register_face.py
import cv2
import os
import sys
from face_utils import FaceRecognizer
from logger_utils import get_logger

# ===== 初始化日志 =====
logger = get_logger('face_register')


def clear_screen():
    """清空控制台"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_banner():
    """打印横幅"""
    print("=" * 60)
    print("  👤 人脸注册工具 v2.0 (交互式注册)")
    print("=" * 60)
    print()


def main():
    """主函数"""
    clear_screen()
    print_banner()

    # 初始化人脸识别器
    print("⏳ 正在初始化人脸识别器...")
    recognizer = FaceRecognizer(
        face_model_path="models/yolo26n-face.pt",
        encoding_file="data/face_encodings.pkl",
        confidence_threshold=0.7,
        match_threshold=0.6
    )

    print("✅ 初始化完成")
    print()

    # 选择注册方式
    print("请选择注册方式:")
    print("  1. 从摄像头实时注册")
    print("  2. 从图片文件注册")
    print("  3. 查看已注册人员列表")
    print("  4. 清空所有注册数据")
    print("  0. 退出")
    print("-" * 40)

    choice = input("请选择 (0-4): ").strip()

    if choice == '1':
        register_from_camera(recognizer)
    elif choice == '2':
        register_from_image(recognizer)
    elif choice == '3':
        list_registered_persons(recognizer)
    elif choice == '4':
        clear_all_data(recognizer)
    elif choice == '0':
        print("👋 再见！")
        sys.exit(0)
    else:
        print("❌ 无效选择")


def register_from_camera(recognizer):
    """从摄像头交互式注册"""
    clear_screen()
    print("📸 摄像头注册模式")
    print("=" * 50)
    print("操作说明:")
    print("  - 面对摄像头，确保脸部清晰可见")
    print("  - 按 's' 键捕获当前画面并开始注册")
    print("  - 按 'q' 键退出")
    print("=" * 50)
    print()

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("❌ 无法打开摄像头")
        return

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # 检测人脸并显示
        faces = recognizer.detect_faces(frame)

        # 绘制人脸框
        for face in faces:
            x1, y1, x2, y2 = face['bbox']
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"face: {face['confidence']:.2f}", (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        # 显示提示
        cv2.putText(frame, "Press 's' to register, 'q' to quit", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.putText(frame, f"Faces detected: {len(faces)}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

        cv2.imshow('Face Registration - Camera', frame)
        key = cv2.waitKey(1)

        if key == ord('s'):
            if len(faces) == 0:
                print("⚠️ 未检测到人脸，请调整位置后重试")
                continue

            # 调用交互式注册
            print("\n" + "=" * 50)
            print("📝 开始注册...")
            result = recognizer.register_face_interactive(frame)

            if result['success']:
                print(f"✅ {result['message']}")
            else:
                print(f"❌ {result['message']}")

            print("=" * 50)
            print("\n按 's' 继续注册，按 'q' 退出")

        elif key == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
    print("\n👋 摄像头模式已退出")


def register_from_image(recognizer):
    """从图片文件注册"""
    clear_screen()
    print("📷 图片文件注册模式")
    print("=" * 50)

    image_path = input("请输入图片路径: ").strip()

    if not os.path.exists(image_path):
        print(f"❌ 文件不存在: {image_path}")
        return

    image = cv2.imread(image_path)
    if image is None:
        print("❌ 图片读取失败")
        return

    # 检测人脸
    faces = recognizer.detect_faces(image)

    if len(faces) == 0:
        print("❌ 未检测到人脸")
        return

    print(f"✅ 检测到 {len(faces)} 个人脸")

    # 显示人脸
    for face in faces:
        x1, y1, x2, y2 = face['bbox']
        cv2.rectangle(image, (x1, y1), (x2, y2), (0, 255, 0), 2)

    cv2.imshow('Detected Faces', image)
    cv2.waitKey(1000)
    cv2.destroyAllWindows()

    # 调用交互式注册
    print("\n" + "=" * 50)
    print("📝 开始注册...")
    result = recognizer.register_face_interactive(image)

    if result['success']:
        print(f"✅ {result['message']}")
    else:
        print(f"❌ {result['message']}")

    print("=" * 50)


def list_registered_persons(recognizer):
    """列出已注册人员"""
    clear_screen()
    print("📋 已注册人员列表")
    print("=" * 60)

    if len(recognizer.known_person_ids) == 0:
        print("  (暂无注册人员)")
    else:
        print(f"  共 {len(recognizer.known_person_ids)} 人")
        print("-" * 60)
        for i, (pid, name, info) in enumerate(zip(
                recognizer.known_person_ids,
                recognizer.known_names,
                recognizer.known_person_info
        ), 1):
            room = info.get('room', '未设置')
            phone = info.get('guardian_phone', '未设置')
            print(f"  {i}. ID: {pid} | 姓名: {name} | 房间: {room} | 电话: {phone}")

    print("=" * 60)
    input("\n按 Enter 键返回...")


def clear_all_data(recognizer):
    """清空所有注册数据"""
    clear_screen()
    print("⚠️ 清空所有注册数据")
    print("=" * 50)

    if len(recognizer.known_person_ids) == 0:
        print("  (暂无数据)"
              "")
        input("\n按 Enter 键返回...")
        return

    print(f"  当前有 {len(recognizer.known_person_ids)} 个注册人员")
    print("  确认清空？(y/n): ", end="")

    confirm = input().strip().lower()
    if confirm == 'y':
        recognizer.known_encodings = []
        recognizer.known_person_ids = []
        recognizer.known_names = []
        recognizer.known_person_info = []
        recognizer.save_encodings()
        print("✅ 已清空所有注册数据")
    else:
        print("❌ 已取消")

    input("\n按 Enter 键返回...")


if __name__ == '__main__':
    main()