if __name__ == '__main__':
    from ultralytics import YOLO

    # Load a model
    model = YOLO("../models/yolo26n-pose.pt")  # load a custom-trained model

    # Export the model
    model.export(format="onnx", imgsz=640, opset=21)  # 关键：添加 opset=21