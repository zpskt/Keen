# 数据准备教程

本教程将指导您如何准备用于训练目标识别模型的数据集，包括下载数据、标注数据和组织数据结构。

## 目录

1. [数据结构要求](#数据结构要求)
2. [下载训练数据](#下载训练数据)
   - [使用脚本自动下载](#使用脚本自动下载)
   - [手动下载数据](#手动下载数据)
3. [标注数据](#标注数据)
4. [数据预处理](#数据预处理)

## 数据结构要求

为了训练目标识别模型，您需要按照以下结构组织数据：

```
data/
├── object/                    # 原始目标图片目录
│   ├── ingredient1/         # 每个目标一个文件夹
│   │   ├── img1.jpg
│   │   ├── img2.jpg
│   │   └── ...
│   ├── ingredient2/
│   │   ├── img1.jpg
│   │   ├── img2.jpg
│   │   └── ...
│   └── ...
├── train/                  # 训练集目录
│   ├── images/             # 训练图片
│   └── labels/             # 训练标签
├── val/                    # 验证集目录
│   ├── images/             # 验证图片
│   └── labels/             # 验证标签
└── object_dataset.yaml       # 数据集配置文件
```

## 下载训练数据

您可以从以下来源获取目标图片：

### 使用脚本自动下载

项目提供了一个自动下载脚本，可以从Kaggle下载目标数据集并保存到项目的[data](file:///Users/zhangpeng/Desktop/zpskt/refrigerator-object-detector/data)目录中：

```bash
cd src/data_processing
python prepare_data.py --download
```

此命令会：
1. 从Kaggle下载目标数据集
2. 将数据保存到项目的[data/object](file:///Users/zhangpeng/Desktop/zpskt/refrigerator-object-detector/data/object)目录
3. 自动处理数据并生成训练集和验证集

注意：使用此功能需要先安装kagglehub库：
```bash
pip install kagglehub
```

还需要配置Kaggle API凭证，参考[Kaggle API文档](https://github.com/Kaggle/kaggle-api)。

### 手动下载数据

#### 1. 公开数据集
- [object-101 Dataset](https://www.vision.ee.ethz.ch/datasets_extra/object-101/)
- [UEC-object-100 Dataset](http://objectcam.mobi/dataset100.html)
- [Recipe1M Dataset](http://pic2recipe.csail.mit.edu/)

#### 2. 网络爬虫
使用网络爬虫工具下载目标图片：
- Google Images爬虫
- 百度图片爬虫
- 专门的目标图片网站

#### 3. 自行拍摄
使用手机或相机拍摄目标中的目标照片。

将下载或拍摄的图片按照以下结构存放：

```
data/object/
├── ingredient1/
│   ├── img1.jpg
│   ├── img2.jpg
│   └── ...
├── ingredient2/
│   ├── img1.jpg
│   ├── img2.jpg
│   └── ...
└── ...
```

每个子文件夹代表一种目标，文件夹名为目标名称。

## 标注数据

本项目使用YOLO格式的标注文件。每个图片文件需要有一个对应的.txt标注文件。

### YOLO标注格式

每行代表一个检测对象，格式为：
```
<object_class> <x_center> <y_center> <width> <height>
```

参数说明：
- `object_class`：对象类别ID（整数，从0开始）
- `x_center`：边界框中心点的x坐标（相对于图像宽度的比例，0-1之间）
- `y_center`：边界框中心点的y坐标（相对于图像高度的比例，0-1之间）
- `width`：边界框的宽度（相对于图像宽度的比例，0-1之间）
- `height`：边界框的高度（相对于图像高度的比例，0-1之间）

对于目标识别这类图像分类任务，我们使用占位标签：
```
0 0.5 0.5 1.0 1.0
```

这表示整个图像都是该类别的目标。

### 自动标注工具
> ⚠️ **重要声明: 废弃，不建议使用** 自动标注仅适用于图像分类任务，目标检测检测是目标检测任务，即视频桢中会出现多个目标。。

项目提供自动标注工具，可以为每个目标图片生成YOLO格式的标注文件。

运行数据处理脚本：
```bash
cd src/data_processing
python prepare_data.py
```

该脚本会：
1. 遍历[data/object](file:///Users/zhangpeng/Desktop/zpskt/refrigerator-object-detector/data/object)目录下的所有目标文件夹
2. 将图片按比例分配到训练集和验证集
3. 自动生成对应的YOLO格式标签文件
4. 创建数据集配置文件[object_dataset.yaml](file:///Users/zhangpeng/Desktop/zpskt/refrigerator-object-detector/data/object_dataset.yaml)

注意：自动标注适用于图像分类任务，即整张图片只包含一种目标的情况。如果你需要进行精确的目标检测（在一张图片中识别和定位多个不同的目标），请使用手动标注工具。

### 手动标注工具

如果您需要更精确的标注（例如在一张图片中识别和定位多个不同的目标），可以使用以下工具：

1. [LabelImg](https://github.com/tzutalin/labelImg) - 图形化标注工具
2. [CVAT](https://github.com/openvinotoolkit/cvat) - 在线标注工具
3. [Label Studio](https://labelstud.io/) - 多功能数据标注平台

手动标注可以让你：
- 在图片上绘制精确的边界框
- 选择对应的目标类别
- 生成符合YOLO格式的标签文件

手动标注的标签文件可能像这样：
```
0 0.3 0.4 0.2 0.3
1 0.7 0.6 0.15 0.25
```

这表示图片中有两个目标对象，第一个是类别0，位于图片的特定位置，占图片的一部分区域；第二个是类别1，位于图片的另一个位置。

#### MakeSense.ai 标注工具

```shell
# clone repository
git clone https://github.com/SkalskiP/make-sense.git

# navigate to main dir
cd make-sense

# install dependencies
npm install

# serve with hot reload at localhost:3000
npm start
```
使用此工具进行数据标注

## 数据预处理

### 1. 图像尺寸调整
建议将图像调整为适合模型训练的尺寸，如640x640像素。

### 2. 数据增强
可以使用以下数据增强技术提高模型泛化能力：
- 随机旋转
- 随机裁剪
- 色彩抖动
- 水平翻转

### 3. 数据平衡
确保每个类别的样本数量相对平衡，避免模型偏向样本多的类别。

## 验证数据集

数据准备完成后，目录结构应该如下：
```
data/
├── object/
│   ├── tudou/
│   │   ├── img1.jpg
│   │   ├── img2.jpg
│   │   └── ...
│   └── ximei/
│       ├── img1.jpg
│       ├── img2.jpg
│       └── ...
├── train/
│   ├── images/
│   │   ├── img1.jpg
│   │   ├── img2.jpg
│   │   └── ...
│   └── labels/
│       ├── img1.txt
│       ├── img2.txt
│       └── ...
├── val/
│   ├── images/
│   │   ├── img3.jpg
│   │   ├── img4.jpg
│   │   └── ...
│   └── labels/
│       ├── img3.txt
│       ├── img4.txt
│       └── ...
└── object_dataset.yaml
```

其中[object_dataset.yaml](file:///Users/zhangpeng/Desktop/zpskt/refrigerator-object-detector/data/object_dataset.yaml)内容如下：
```yaml
path: ../data
train: train
val: val

names:
  0: tudou
  1: ximei
```

## 常见问题

### 1. 标注文件格式错误
确保每个标注文件与对应的图片文件同名，只是扩展名为.txt。

### 2. 类别映射问题
确保[object_dataset.yaml](file:///Users/zhangpeng/Desktop/zpskt/refrigerator-object-detector/data/object_dataset.yaml)中的类别名称与训练脚本中的配置一致。

### 3. 图像路径问题
确保数据集配置文件中的路径正确指向训练和验证数据。

准备好数据后，您可以开始[训练模型](./train_tutorial.md)。