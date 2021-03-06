import os
import shutil
import vgg16
import paddle
import paddle.dataset.cifar as cifar
import paddle.fluid as fluid
from visualdl import LogWriter
try:
    # 兼容PaddlePaddle2.0
    paddle.enable_static()
except:
    pass


# 创建记录器
writer = LogWriter(logdir='log/')

# 定义输入层
image = fluid.data(name='image', shape=[None, 3, 32, 32], dtype='float32')
label = fluid.data(name='label', shape=[None, 1], dtype='int64')

# 获取分类器
model = vgg16.vgg16(image, 10)

# 获取损失函数和准确率函数
cost = fluid.layers.cross_entropy(input=model, label=label)
avg_cost = fluid.layers.mean(cost)
acc = fluid.layers.accuracy(input=model, label=label)

# 克隆测试程序
test_program = fluid.default_main_program().clone(for_test=True)

# 定义优化方法
l2 = fluid.regularizer.L2DecayRegularizer(2e-3)
optimizer = fluid.optimizer.MomentumOptimizer(learning_rate=1e-3,
                                              momentum=0.9,
                                              regularization=l2)
opts = optimizer.minimize(avg_cost)

# 获取CIFAR数据
train_reader = paddle.batch(cifar.train10(), batch_size=32)
test_reader = paddle.batch(cifar.test10(), batch_size=32)

# 定义一个使用GPU的执行器
place = fluid.CUDAPlace(0)
# place = fluid.CPUPlace()
exe = fluid.Executor(place)
# 进行参数初始化
exe.run(fluid.default_startup_program())

# 定义输入数据维度
feeder = fluid.DataFeeder(place=place, feed_list=[image, label])

# 定义日志的开始位置和获取参数名称
train_step = 0
test_step = 0
params_name = fluid.default_startup_program().global_block().all_parameters()[0].name

# 训练10次
for pass_id in range(10):
    # 进行训练
    for batch_id, data in enumerate(train_reader()):
        train_cost, train_acc, params = exe.run(program=fluid.default_main_program(),
                                                feed=feeder.feed(data),
                                                fetch_list=[avg_cost, acc, params_name])
        # 保存训练的日志数据
        train_step += 1
        writer.add_scalar(tag="训练/损失值", step=train_step, value=train_cost[0])
        writer.add_scalar(tag="训练/准确率", step=train_step, value=train_acc[0])
        writer.add_histogram(tag="训练/参数分布", step=train_step, values=params.flatten(), buckets=50)

        # 每100个batch打印一次信息
        if batch_id % 100 == 0:
            print('Pass:%d, Batch:%d, Cost:%0.5f, Accuracy:%0.5f' %
                  (pass_id, batch_id, train_cost[0], train_acc[0]))

    # 进行测试
    test_accs = []
    test_costs = []
    for batch_id, data in enumerate(test_reader()):
        test_cost, test_acc = exe.run(program=test_program,
                                      feed=feeder.feed(data),
                                      fetch_list=[avg_cost, acc])
        # 保存测试的日志数据
        test_step += 1
        writer.add_scalar(tag="测试/损失值", step=test_step, value=test_cost[0])
        writer.add_scalar(tag="测试/准确率", step=test_step, value=test_acc[0])

        print('Test:%d, Batch:%d, Cost:%0.5f, Accuracy:%0.5f' % (
            pass_id, batch_id, test_cost, test_acc))

    # 保存预测模型
    save_path = 'models/'
    # 删除旧的模型文件
    shutil.rmtree(save_path, ignore_errors=True)
    # 创建保持模型文件目录
    os.makedirs(save_path)
    # 保存预测模型
    fluid.io.save_inference_model(dirname=save_path,
                                  feeded_var_names=[image.name],
                                  target_vars=[model],
                                  executor=exe)
