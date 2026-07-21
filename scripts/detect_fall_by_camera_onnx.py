if __name__ == '__main__':
    import onnx

    onnx_model = onnx.load("../models/yolo26n-pose.onnx")
    onnx.checker.check_model(onnx_model)