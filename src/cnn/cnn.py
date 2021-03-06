from __future__ import print_function

import tensorflow as tf
import time
import numpy as np
import os
# Import MNIST data
#from tensorflow.examples.tutorials.mnist import input_data
#mnist = input_data.read_data_sets("/tmp/data/", one_hot=True)

# Parameters
from data.brightfield import BrightfieldGenerator
from visual import ComponentVisualizer


# mode = 'train'
mode = 'visualize'
# mode= 'debug'
# mode = 'stats'

learning_rate = 0.001
training_iters = 200000
#training_iters = 10000
batch_size = 128
display_step = 10
save_step = 50


model_folder = '../../models/m6-cnn-pristine-20-epochs/'
# initial_model_folder = model_folder
initial_model_folder = '../../models/m6-cnn-pristine-20-epochs/'
restore_model = True

if not os.path.exists(model_folder):
    os.makedirs(model_folder)

data_folder = '../../data/ds1-pristine/'
# data_folder = '../../data/ds2-diffraction/'

data_load_start = time.time()
#train_data, train_labels = BrightfieldGenerator.loadData(data_folder + "training/*.png")
#test_data, test_labels = BrightfieldGenerator.loadData(data_folder + "test/*.png")

train_npz = np.load(data_folder + 'training.npz')
test_npz = np.load(data_folder + 'test.npz')

train_data, train_labels = train_npz['data'], train_npz['labels']
test_data, test_labels = test_npz['data'], test_npz['labels']


print('Loading data in: ', (time.time() - data_load_start))

# diffaction images are 80, non-diffracted 40
image_w, image_h  = 40, 40
# image_w, image_h  = 80, 80

# Network Parameters
n_input = 40*40 # MNIST data input (img shape: 28*28)
n_classes = 6 # MNIST total classes (0-9 digits)
dropout = 0.75 # Dropout, probability to keep units

# tf Graph input
x = tf.placeholder(tf.float32, [None, n_input])
y = tf.placeholder(tf.float32, [None, n_classes])
# threshold = tf.placeholder(tf.float32)
keep_prob = tf.placeholder(tf.float32) #dropout (keep probability)

# Create some wrappers for simplicity
def conv2d(x, W, b, strides=1):
    # Conv2D wrapper, with bias and relu activation
    x = tf.nn.conv2d(x, W, strides=[1, strides, strides, 1], padding='SAME')
    x = tf.nn.bias_add(x, b)
    return tf.nn.relu(x)


def maxpool2d(x, k=2):
    # MaxPool2D wrapper
    return tf.nn.max_pool(x, ksize=[1, k, k, 1], strides=[1, k, k, 1],
                          padding='SAME')


# Create model
def conv_net(x, weights, biases, dropout):
    # Reshape input picture
    x = tf.reshape(x, shape=[-1, image_w, image_h, 1])

    # Convolution Layer
    conv1u = conv2d(x, weights['wc1'], biases['bc1'])
    # Max Pooling (down-sampling)
    conv1 = maxpool2d(conv1u, k=2)

    # Convolution Layer
    conv2u = conv2d(conv1, weights['wc2'], biases['bc2'])
    # Max Pooling (down-sampling)
    conv2 = maxpool2d(conv2u, k=2)

    # Fully connected layer
    # Reshape conv2 output to fit fully connected layer input
    fc1 = tf.reshape(conv2, [-1, weights['wd1'].get_shape().as_list()[0]])
    fc1 = tf.add(tf.matmul(fc1, weights['wd1']), biases['bd1'])
    fc1 = tf.nn.relu(fc1)
    # Apply Dropout
    fc1 = tf.nn.dropout(fc1, dropout)

    # Output, class prediction
    out = tf.add(tf.matmul(fc1, weights['out']), biases['out'])
    return out, conv1u, conv2u, fc1


def save_filters(destination, filters):
    with open(destination, 'ab') as f:
        for filter in range(filters.shape[3]):
            print(f,"Filter {0}: \n".format(filter))
            np.savetxt(f, filters[0,:,:,filter], fmt='%10.4f')


def get_model_folder(folder_name):
    folder = model_folder + folder_name + '/'
    if not os.path.exists(folder):
        os.makedirs(folder)
    return folder


def softmax(x):
    """Compute softmax values for each sets of scores in x."""
    e_x = np.exp(x - np.max(x))
    return e_x / e_x.sum()

# Store layers weight & bias
weights = {
    # 5x5 conv, 1 input, 32 outputs
    'wc1': tf.Variable(tf.random_normal([5, 5, 1, 32])),
    # 5x5 conv, 32 inputs, 64 outputs
    'wc2': tf.Variable(tf.random_normal([5, 5, 32, 64])),
    # fully connected, 7*7*64 inputs, 1024 outputs
    # 'wd1': tf.Variable(tf.random_normal([int(image_w/2)*int(image_h/2)*64, 1024])),
    'wd1': tf.Variable(tf.random_normal([10*10*64, 1024])),
    # 1024 inputs, 10 outputs (class prediction)
    'out': tf.Variable(tf.random_normal([1024, n_classes]))
}

biases = {
    'bc1': tf.Variable(tf.random_normal([32])),
    'bc2': tf.Variable(tf.random_normal([64])),
    'bd1': tf.Variable(tf.random_normal([1024])),
    'out': tf.Variable(tf.random_normal([n_classes]))
}

# Construct model
pred, cv1, cv2, fc_out = conv_net(x, weights, biases, keep_prob)

# Define loss and optimizer
#pred_softmax = tf.nn.softmax(pred, dim=1)
cost = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(logits=pred, labels=y))
optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate).minimize(cost)

# Evaluate model
correct_pred = tf.equal(tf.argmax(pred, 1), tf.argmax(y, 1))
accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))


# Initializing the variables
init = tf.global_variables_initializer()

# saving the model
saver = tf.train.Saver()

# Launch the graph
with tf.Session() as sess:
    sess.run(init)
    step = 1

    step_dt = []
    iter_dt = []
    train_loss_dt = []
    train_acc_dt = []
    test_acc_dt = []
    time_dt = []

    if restore_model:
        saver.restore(sess, initial_model_folder + "model.ckpt")

    if mode == 'visualize':
        cv_res1, cv_res2, wc1_res, wc2_res= sess.run([cv1, cv2, weights['wc1'], weights['wc2']],
            feed_dict={x: train_data[0:128, :],
                       y: train_labels[0:128], keep_prob: dropout})
        #ComponentVisualizer.plot_filter(cv_res1)
        #ComponentVisualizer.plot_filter(cv_res2)



        viz_folder = get_model_folder('visualizations')

        cr = 3
        ComponentVisualizer.saveTiledFilterOutputs(cv_res1, viz_folder + 'cv1_out_{0}_L{1}.png', train_data[0:128], train_labels[0:128], cropx=cr, cropy=cr)
        ComponentVisualizer.saveTiledFilterOutputs(cv_res2, viz_folder + 'cv2_out_{0}_L{1}.png', train_data[0:128], train_labels[0:128], cropx=cr, cropy=cr)

        ComponentVisualizer.saveTiledFilters(wc1_res, viz_folder + 'wc1_res.png')
        ComponentVisualizer.saveTiledFilters(wc2_res, viz_folder + 'wc2_res.png' )
    elif mode == 'stats':
        stats_folder = get_model_folder('stats')

        test_acc_stat, preds_out = sess.run([accuracy, pred], feed_dict={x: test_data,
                                          y: test_labels,
                                          keep_prob: 1.})
        # Calculate accuracy for all test images
        print("Testing Accuracy:", test_acc_stat )
        with open(stats_folder + 'accuracy.txt', "w") as text_file:
            text_file.write("Test Accuracy: {0}".format(test_acc_stat) )

        # softmax all the predictions
        for i in range(test_data.shape[0]):
            preds_out[i,:] = softmax(preds_out[i,:])

        # make ROC curve

        # pred should be 10000 x 6 matrix
        # tp_preds = []
        # n_preds = []
        # for threshold in np.arange(0,1,0.01):
        #     neg_pred = preds_out[:,0] >= threshold
        #     pos_pred = preds_out[:, 0] < threshold
        #     neg_gnd = test_data[:,0] == 1
        #     pos_gnd = test_data[:, 0] == 0
        #     true_pos = pos_gnd == pos_pred
        #     false_pos = pos_pred == neg_gnd


    elif mode == 'debug':
        pred_res, cv_res1, cv_res2, fc_res = sess.run([pred, cv1, cv2, fc_out],
                                    feed_dict={x: train_data[0:128, :],
                                               y: train_labels[0:128], keep_prob: dropout})
        # write fc to csv
        debug_folder = model_folder +'debug/'
        if not os.path.exists(debug_folder):
            os.makedirs(debug_folder)
        # delete all previous debug
        import glob
        for f in  glob.glob(debug_folder + "*.txt"):
            os.remove(f)

        for key,w in weights.items():
            if not key.startswith('wc'):
                wval = sess.run(w,feed_dict={x: train_data[0:128, :],
                                    y: train_labels[0:128], keep_prob: dropout})
                np.savetxt(debug_folder + 'debug_weight_{0}.txt'.format(key), wval, fmt='%10.4f')

        for key, b in biases.items():
            bval = sess.run(b, feed_dict={x: train_data[0:128, :],
                                          y: train_labels[0:128], keep_prob: dropout})
            np.savetxt(debug_folder + 'debug_bias_{0}.txt'.format(key), bval, fmt='%10.4f')

        np.savetxt(debug_folder + 'debug_pred.txt', pred_res, fmt='%10.4f')
        np.savetxt(debug_folder + 'debug_fc.txt', fc_res,  fmt='%10.4f')
        save_filters(debug_folder + 'debug_conv1.txt', cv_res1)
        save_filters(debug_folder + 'debug_conv2.txt', cv_res2)


    elif mode == 'train':
        start_time = time.time()

        # Keep training until reach max iterations
        while step * batch_size < training_iters:
            batch_range = range(step * batch_size % 10000, (step+1) * batch_size % 10000)
            batch_x, batch_y = train_data[batch_range, :], train_labels[batch_range]

            # Run optimization op (backprop)
            sess.run(optimizer, feed_dict={x: batch_x, y: batch_y,
                                           keep_prob: dropout})
            if step % display_step == 0:
                # Calculate batch loss and accuracy
                train_loss, train_acc = sess.run([cost, accuracy], feed_dict={x: batch_x,
                                                                              y: batch_y,
                                                                              keep_prob: 1.})
                test_acc = sess.run(accuracy, feed_dict={x: test_data[:256],
                                              y: test_labels[:256],
                                              keep_prob: 1.})

                print("Iter " + str(step*batch_size) + ", Minibatch Loss= " + \
                      "{:.6f}".format(train_loss) + ", Training Accuracy= " + \
                      "{:.5f}".format(train_acc) + ", Test Accuracy= " + \
                      "{:.5f}".format(test_acc))

                step_dt.append(step)
                iter_dt.append(step*batch_size)
                train_loss_dt.append(train_loss)
                train_acc_dt.append(train_acc)
                test_acc_dt.append(test_acc)
                time_dt.append(time.time() - start_time)

                header = "step_dt, iter_dt, train_loss_dt, train_acc_dt, test_acc_dt, time_dt"
                perf_data = np.asarray([step_dt, iter_dt, train_loss_dt, train_acc_dt, test_acc_dt, time_dt])

                np.savetxt(model_folder + "performance.csv", np.transpose(perf_data), fmt='%10.4f', header = header, delimiter=',')
                np.savez(model_folder + "performance.npz",step_dt=step_dt, iter_dt=iter_dt,
                         train_loss_dt=train_loss_dt, train_acc_dt=train_acc_dt, test_acc_dt=test_acc_dt, time_dt=time_dt)

            if step % save_step == 0:
                saver.save(sess, model_folder + "model.ckpt")

            step += 1

        # save the model
        save_path = saver.save(sess, model_folder + "model.ckpt")

        print("Optimization Finished!")

        # Calculate accuracy for all test images
        print("Testing Accuracy:", \
            sess.run(accuracy, feed_dict={x: test_data,
                                          y: test_labels,
                                          keep_prob: 1.}))