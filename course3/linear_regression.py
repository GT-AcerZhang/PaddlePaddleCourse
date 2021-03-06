import paddle.fluid as fluid
import numpy as np
import paddle
try:
    # 兼容PaddlePaddle2.0
    paddle.enable_static()
except:
    pass

# 定义一个简单的线性网络
x = fluid.data(name='x', shape=[None, 1], dtype='float32')
hidden = fluid.layers.fc(input=x, size=100, act='relu')
hidden = fluid.layers.fc(input=hidden, size=100, act='relu')
net = fluid.layers.fc(input=hidden, size=1, act=None)

# 获取预测程序
infer_program = fluid.default_main_program().clone(for_test=True)

# 定义损失函数
y = fluid.data(name='y', shape=[None, 1], dtype='float32')
cost = fluid.layers.square_error_cost(input=net, label=y)
avg_cost = fluid.layers.mean(cost)

# 定义优化方法
optimizer = fluid.optimizer.SGDOptimizer(learning_rate=0.01)
opts = optimizer.minimize(avg_cost)

# 创建一个使用CPU的执行器
place = fluid.CPUPlace()
exe = fluid.Executor(place)
# 进行参数初始化
exe.run(fluid.default_startup_program())

# 定义训练和测试数据
x_data = np.array([[1.0], [2.0], [3.0], [4.0], [5.0]]).astype('float32')
y_data = np.array([[3.0], [5.0], [7.0], [9.0], [11.0]]).astype('float32')

# 开始训练100个pass
for pass_id in range(100):
    train_cost = exe.run(program=fluid.default_main_program(),
                         feed={x.name: x_data, y.name: y_data},
                         fetch_list=[avg_cost])
    print("Pass:%d, Cost:%0.5f" % (pass_id, train_cost[0]))


test_data = np.array([[6.0]]).astype('float32')
# 开始预测
result = exe.run(program=infer_program,
                 feed={x.name: test_data},
                 fetch_list=[net])
print("当x为6.0时，y为：%0.5f" % result[0][0][0])
