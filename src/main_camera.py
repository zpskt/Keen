import cv2

from detect_fall_and_push import process_frame

if __name__ == '__main__':
    cap = cv2.VideoCapture(0)  # 或视频文件路径
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            break
        annotated_frame, status = process_frame(frame)
        cv2.imshow("Fall Detection", annotated_frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    cap.release()
    cv2.destroyAllWindows()