# 训练三分类模型（坐着、行走、跌倒）
if __name__ == '__main__':
    import torch

    print(f"PyTorch版本: {torch.__version__}")
    print(f"CUDA是否可用: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA版本: {torch.version.cuda}")
        print(f"GPU数量: {torch.cuda.device_count()}")
        print(f"当前GPU: {torch.cuda.get_device_name()}")

    from ultralytics import YOLO

    # Load a model
    # model = YOLO("yolo26n-pose.yaml")  # build a new model from YAML
    model = YOLO("models/yolo26n.pt")  # load a pretrained model (recommended for training)
    # model = YOLO("yolo26l-pose.yaml").load("yolo26l-pose.pt")  # build from YAML and transfer weights

    # Train the model
    results = model.train(data="datasets/object_dataset.yaml", epochs=100, imgsz=640)