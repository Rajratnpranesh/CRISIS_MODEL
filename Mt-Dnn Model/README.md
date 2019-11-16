[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Travis-CI](https://travis-ci.org/namisan/mt-dnn.svg?branch=master)](https://github.com/namisan/mt-dnn)

**New Release ** <br/>
We are working on the v0.2 version which is easier to adapt it to new tasks. <br/>
You are welcomed to test our new version. <br/>
It supports Sequence Labeling Task, e.g., NER. <br/>
If you want to use the old version, please use following cmd to clone the code: <br/>
```git clone -b v0.1 https://github.com/namisan/mt-dnn.git ```



# Multi-Task Deep Neural Networks for Natural Language Understanding

This PyTorch package implements the Multi-Task Deep Neural Networks (MT-DNN) for Natural Language Understanding, as described in:

Xiaodong Liu\*, Pengcheng He\*, Weizhu Chen and Jianfeng Gao<br/>
Multi-Task Deep Neural Networks for Natural Language Understanding<br/>
[ACL 2019](https://aclweb.org/anthology/papers/P/P19/P19-1441/) <br/>
\*: Equal contribution <br/>

Xiaodong Liu, Pengcheng He, Weizhu Chen and Jianfeng Gao<br/>
Improving Multi-Task Deep Neural Networks via Knowledge Distillation for Natural Language Understanding <br/>
[arXiv version](https://arxiv.org/abs/1904.09482) <br/>


Pengcheng He, Xiaodong Liu, Weizhu Chen and Jianfeng Gao<br/>
Hybrid Neural Network Model for Commonsense Reasoning <br/>
[arXiv version](https://arxiv.org/abs/1907.11983) <br/>


Liyuan Liu, Haoming Jiang, Pengcheng He, Weizhu Chen, Xiaodong Liu, Jianfeng Gao and Jiawei Han <br/>
On the Variance of the Adaptive Learning Rate and Beyond <br/>
[arXiv version](https://arxiv.org/abs/1908.03265) <br/>

## Quickstart
## MODIFIED SOME PART OF MT-DNN MODEL TO WORK ON CRISIS DATA FOR OUR RESEARCH.
### Setup Environment
#### Install via pip:
1. python3.6 </br>
   Reference to download and install : https://www.python.org/downloads/release/python-360/

2. install requirements </br>
   ```> pip install -r requirements.txt```
   
3. Installing Apex </br>
   a)!touch setup.sh
   b)!git clone https://github.com/NVIDIA/apex
   c)!pip install -v --no-cache-dir --global-option="--cpp_ext" --global-option="--cuda_ext" ./apex
   d)!sh setup.sh

1. Download data </br>
   ```> sh download.sh``` </br>
   Please refer to download GLUE dataset: https://gluebenchmark.com/

   Replace the sst data(train, test and dev) from the downloaded data in the "data" folder by the data(train, test and dev) in the crisis folder. 
   
2. Preprocess data </br>
   ```> sh experiments/glue/prepro.sh```

3. Training </br>
   ```> python train.py```

**Note that we ran experiments on 4 V100 GPUs for base MT-DNN models. You may need to reduce batch size for other GPUs.** <br/>

