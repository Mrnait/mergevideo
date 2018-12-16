#！/usr/bin/env python3

'''
这个代码是用来处理视频合并用的，目前只用到 flv 格式视频的合并，所以就先只写这个吧。
之前也想过去处理视频的合并，但是通过文件的读取然后简单的拼接在一起后，会出现播放器不能正常读取
视频时长出了问题，合并后的视频时长还是合并前第一个视频的时长。今天特意研究了一下 flv(flash video)视频格式的结构，有了一些解决思路。

弄了半天知道在 metadata 中的 duration 表示的是视频时长，但是卡在这了，无法解决将 duration 中的16进制值转化为时长，不知道其中的计算方法是什么。
经过两天的资料查询，终于解决 double2bin 和 bin2double 的计算问题，并使用 python 实现此过程，其实就是数值在内存中的存取问题，用 C 几行代码就行了。

'''

'''
合并视频的思路：
1. 首先需要知道 flv 文件的数据格式，播放器是读取 flv 文件的第一个脚本数据中的 duration 值来获得视频时长。

*   第一个难点：如何计算 duration value ？python 读取出的视频文件是以字节形式显示的，
    显示形式是二进制数据的十六进制形式，因为一个字节是八位，四位的二进制数据转换成一个十六进制数，
    所以一个字节就显示出两个16进制数，例如：'/x40'。
    根据 flv 格式可以知道 duration 的值占八个字节，获取到值不难，难的是需要模拟出 double 类型的数据在内存中的存取过程。
    这个对 C 语言很简单，直接使用 unoin 强制转换类型就可以，python实现需要模拟存取过程。

*   第二个难点：读出需要合并视频的时长、并将 double 值计算出后，进行相加。难在需要重新再转换回字节形式。

2. 其次需要找到每一帧的时间戳，第一个视频的时间戳不用管，第二个视频的时间戳需在第一个视频的时间戳的基础山进行累加，依次类推。
'''

import os
import sys
from decimal import Decimal
import binascii


def int_b2a(string):

    return int(binascii.b2a_hex(string), 16)


def int2hex(e_list):

    return int(''.join("%0*X" % (2, d) for d in e_list), 16)


'''
二进制数转浮点数,模仿内存中数据的存储
二进制转浮点(double) 的计算公式 ： V = (-1)^(S) * (1.M) * 2^(I-1023)[V 为 value 数值，S 为 符号(取 0或1)，M 为尾数，I 是指数]
'''


def bin2double(int_string):  # 模拟浮点数据从内存的取出过程，获得其值

    int_string = int(int_string)

    bin_string = ''.join(bin(int_string))  # 转成二进制

    bin_string = bin_string[2:]  # 由于python中二进制数前有 “0b” ，所以将其进行分割，取数值部分

    # print(bin_string,len(bin_string))

    if len(bin_string) <= 64:  # 目的是想转换成 double 类型，double 是 8 字节 64 位，所以判断下长度然后补全 64 位。

        add_zero_count = 64 - len(bin_string)

        bin_string = "0"*add_zero_count + bin_string
    # print(bin_string)

    # 符号部分
    symbol = int(bin_string[0])

    if symbol == 0:

        symbol = (-1)**0

    elif symbol == 1:

        symbol = (-1)**1

    else:
        print("symbol 不是 int 数值")
    # print(symbol)

    # 尾数部分
    # 这52位二进制的尾数部分计算为二进制的小数计算，也就是二进制的每一位乘二的负 N 次方（N的取值为1,2,3,4,5...）,直到2的负52次方为止。
    mantissa = bin_string[12:]  # mantissa（中文：尾数）计算后52位，得出 double 类型数据的二进制下的尾数
    # print(mantissa,len(mantissa))

    mantissa_value = 0

    for n in range(1, 53):

        mantissa_value += int(mantissa[n-1]) * ((1/2)**n)

    mantissa_value = mantissa_value + 1  # 在储存时 1 被省略，现在需要加上
    # print(mantissa_value)

    # 指数部分
    index = bin_string[1:12]  # index（中文：指数）计算指数
    # print(index,len(index))

    index = int(index, 2)  # 得到的值需要减去 1023（偏移值）

    index = 2 ** (index - 1023)
    # print(index)

    double_string = symbol * mantissa_value * index
    # print(double_string)

    return double_string


'''
浮点类型转二进制的方法是整数部分和小数部分分开计算，整数部分使用除以二取整，小数部分使用乘以二取整。
'''


def double2bin(double_string):  # 模拟 double 类型数据的储存过程，得到最后二进制值对应的十六进制数

    if int(double_string) < 0:

        symbol = '1'

    else:

        symbol = '0'

    # 为了保证精度，使用 Decimal 函数来显示精度值，转成字符串好整数小数分离
    double_string = str(Decimal(double_string))

    double_string = double_string.split(".")
    # print(double_string)

    # 整数部分
    int_part = double_string[0]

    decimal_part = "0." + double_string[1]
    # print(decimal_part)

    bin_intpart = bin(int(int_part))  # 将整数部分转换为二进制

    bin_intpart = bin_intpart[3:]  # 去除‘0b’

    # 确定整数部分二进制的长度，好计算小数部分需要计算多少位，因为就 52 位的长度
    bin_intpart_len = len(bin_intpart)

    offset = ''.join(bin(1023+bin_intpart_len))

    offset = offset[2:]  # 这 ‘0b’ 真恶心

    # print(bin_intpart)

    # 小数部分
    global value

    global bin_decimalpart  # 创建两个 globle 变量，将循环中接收的值传出

    bin_decimalpart = ''

    value = float(decimal_part)
    # print(value)

    bin_decimalpart_len = 52 - bin_intpart_len

    for n in range(0, bin_decimalpart_len):  # 因为尾数是整数部分的二进制数和小数部分的二进制数组合而成，一共 52 位。

        value = value * 2  # 对小数部分进行乘零操作，小于 1 时 取 0 ，大于 1 时 取 1 并减去 1，小数部分继续计算
        # print(value)

        if value < 1:

            bin_decimalpart = bin_decimalpart + '0'

        else:

            bin_decimalpart = bin_decimalpart + '1'

            value = value - 1

    mantissa = bin_intpart + bin_decimalpart  # 以下只是为了方便阅读

    index = offset

    bin_string = symbol + index + mantissa

    return bin_string


def get_last_ts(data):  # 获取到视频文件的最后一帧视频和最后一帧音频的时间戳

    video_timestamp = ''

    audio_timestamp = ''

    pre_tag_len = 4

    while True:

        pre_tag_value = int_b2a(data[-pre_tag_len:])

        last_tag = data[-pre_tag_value-pre_tag_len:-pre_tag_len]

        data = data[:-pre_tag_value-pre_tag_len]

        tag_type = binascii.b2a_hex(last_tag[:1])

        timestamp = last_tag[4:7]  # 低位

        timestamp_ex = last_tag[7:8]  # 高位，放第一位
      # print(timestamp,timestamp_ex)

        if tag_type == b'08':

            if len(audio_timestamp) == 0:

                audio_timestamp = '%s' % int_b2a(
                    timestamp_ex+timestamp)  # 最后一帧音频时间戳

        elif tag_type == b'09':

            if len(video_timestamp) == 0:

                video_timestamp = '%s' % int_b2a(
                    timestamp_ex+timestamp)  # 最后一帧视频时间戳

        if len(audio_timestamp) > 0 and len(video_timestamp) > 0:

            break

    return audio_timestamp, video_timestamp  # 字符串类型


'''  
修改第二个视频及以后的时间戳，保证正常播放。所以第二个视频需要叠加第一个视频的时间戳、
第三个视频需要叠加第二个视频的时间戳，以此类推。

这里需要注意一个问题，时间戳和扩展时间戳的高低位问题：
计算的时候由于 ts_ex 是高位所以需要将其放在首位，反向计算的时候也许要将其放回末尾位置。

解释下为什么只有音频帧(0x08)、视频帧(0x09),而没有脚本帧(0x12) 的修改，说实话除了第一个视频
需要脚本帧，后续的视频合并的时候只需要内容帧就好了
'''


def update_timestamp(data, last_ts):

    # last_ts 包含上一个视频的最后一帧视频时间戳、最后一帧音频时间戳
    last_audio_ts, last_video_ts = last_ts

    tag_list = []

    pre_tag_len = 4

    data = list(data)

    try:

        while True:

            if len(data) <= 13:
                break

            pre_tag_size = data[-pre_tag_len:]
            # print(pre_tag_size)

            pre_tag_value = int2hex(pre_tag_size)
            # print(pre_tag_value)

            last_tag = data[-pre_tag_value - pre_tag_len:-pre_tag_len]

            #  不开辟新的内存空间,直接在原始数据上边操作
            del data[-pre_tag_value-pre_tag_len:]
            # print(len(data))

            tag_type = last_tag[0]
            # print(tag_type,type(tag_type))

            # #  低位时间戳
            timestamp = last_tag[4:7]
            # print(timestamp)

            # # 高位，放第一位
            timestamp_ex = last_tag[7:8]
            # print(timestamp_ex)

            # 如果是音频帧，就将计算值叠加上一个音频时间戳
            if tag_type == 8:

                # 计算十进制下的时间戳
                audio_timestamp = int2hex(timestamp_ex+timestamp)
                # print(audio_timestamp)

                # 十进制下的更新值
                update_audio_ts = int(last_audio_ts) + audio_timestamp
                # print(audio_timestamp)

                # 16 进制
                update_audio_ts = hex(update_audio_ts)
                # print(update_audio_ts,type(update_audio_ts))

                if len(update_audio_ts) < 10:

                    # 补 0，差几位补几个
                    add_zero_count = 10 - len(update_audio_ts)

                    update_audio_ts = '0' * \
                        add_zero_count + update_audio_ts[2:]

                move_ts_ex = update_audio_ts[0:2]

                #  修改工作完成，接下来将此值与原始值替换
                update_audio_ts = update_audio_ts[2:] + move_ts_ex
                # print(update_audio_ts)

                #  重新转化成列表用来替换
                timestamp_list = []

                for n in range(0, 8, 2):

                    #  没办法,只能先转成16进制,再转成10进制才成,  bytes() 函数只接受数值类型
                    timestamp_list.append(int(update_audio_ts[n:n+2], 16))

                # print(timestamp_list)

                last_tag[4:8] = timestamp_list

            # 视频中的时间戳更新与上边音频时间戳更新操作一致
            elif tag_type == 9:

                # 计算十进制下的时间戳
                video_timestamp = int2hex(timestamp_ex+timestamp)
                # print(video_timestamp)

                # 十进制下的更新值
                update_audio_ts = int(last_audio_ts) + video_timestamp

                # 16 进制
                update_audio_ts = hex(update_audio_ts)
                # print(update_audio_ts,type(update_audio_ts))

                #  之所以为 10 是因为上边使用 hex() 函数后,字符串多了个"0x",我们需要的是一个四字节的字符串
                if len(update_audio_ts) < 10:

                    #  补 0，差几位补几个
                    add_zero_count = 10 - len(update_audio_ts)

                    update_audio_ts = '0' * \
                        add_zero_count + update_audio_ts[2:]
                    # print(update_audio_ts)

                move_ts_ex = update_audio_ts[0:2]

                #  修改工作完成，接下来将此值与原始值替换
                update_audio_ts = update_audio_ts[2:] + move_ts_ex
                # print(update_audio_ts)

                #  重新转化成列表用来替换
                timestamp_list = []

                for n in range(0, 8, 2):

                    #  没办法,只能先转成16进制,再转成10进制才成,  bytes() 函数只接受数值类型
                    timestamp_list.append(int(update_audio_ts[n:n+2], 16))

                # print(timestamp_list)

                last_tag[4:8] = timestamp_list

            #  保存进列表，后续需要转换成字符串合并视频，正好一个视频处理完就只有 tag 没有 flv_header
            tag_list.insert(0, last_tag + pre_tag_size)

    except KeyboardInterrupt:

        print("年轻人要有耐心-- Young people should be have patience")

        sys.exit()

    #  用列表接收字节值
    flv_body_list = []

    for data in tag_list[1:]:

        change_bytes = bytes(data)

        flv_body_list.append(change_bytes)

    #  转换成字节串
    flv_body_btyes = b"".join(flv_body_list)

    return flv_body_btyes


def get_duration(data):
    '''计算 duration'''
    duration_local = data.index(b"duration")  # 找到 duration 的位置

    #  根据 flv 数据结构，确定 duration 值的位置
    bin_duration_value = data[duration_local+9:duration_local+17]
    # print(duration_value,type(duration_value))

    #  将二进制的值转换成十六进制 ascii 码
    b2a_duration_value = binascii.b2a_hex(
        bin_duration_value)
    # print(b2a_duration_value)

    #  转换成十进制值，为后续计算出其 double 类型数值
    int_duration_value = int(b2a_duration_value, 16)
    # print(int_duration_value)

    return bin2double(int_duration_value)


def update_duration(data, duration_list):
    '''
    计算总的视频时长,然后在转换回去二进制形式，用这个总的视频时长值，替换第一个视频的时长值
    '''
    int_sum_duration = sum(duration_list)
    # print(int_sum_duration)

    #  转换回十六进制，替换原视频的视频长度值
    hex_sum_duration = hex(int(double2bin(int_sum_duration), 2))
    # print(hex_sum_duration,type(hex_sum_duration))

    #  去掉‘0x’,准备换回二进制的字节形式，像这样b'/x40/x70...'
    hex_sum_duration = hex_sum_duration[2:]

    a2b_sum_duration = binascii.a2b_hex(hex_sum_duration)
    # print(a2b_sum_duration)

    # 定位 duration 值的位置
    duration_local = data.index(b'duration')

    # 提取出值
    duration_value = data[duration_local+9:duration_local+17]

    # 进行替换
    update_data = data.replace(duration_value, a2b_sum_duration, 1)

    return update_data



def merge_flv_video():

    viedo_data_list = list()

    last_ts_list = list()

    duration_list = list()

    video_path, video_name_list, merged_video_name = get_video()

    '''
    获取每个视频文件的 duration ，视频 Tag 中的timestamp
    '''
    for n in range(0, len(video_name_list)):

        sys.stdout.write("\r\033[0;35m正在处理第 {} 个视频, 剩余视频数量 {}, 请耐心等待...\033[0m"
                         .format(n+1,  len(video_name_list) - (n+1)))

        sys.stdout.flush()

        with open(video_path + video_name_list[n], 'rb') as fileout:

            data = fileout.read()

        if n == 0:

            duration_value = get_duration(data)

            # 取出 duration 值，存进列表，一会儿计算总值使用
            duration_list.append(duration_value)

            last_ts_audio, last_ts_video = get_last_ts(data)

            last_ts_list.append((last_ts_audio, last_ts_video))

            viedo_data_list.append(data)

        if n > 0:

            duration_value = get_duration(data)

            # 取出 duration 值，存进列表，一会儿计算总值使用
            duration_list.append(duration_value)

            last_ts = last_ts_list.pop()

            # 修改时间戳，返回修改后的数据
            flv_body = update_timestamp(data, last_ts)

            # 取出修改完的最后一帧时间戳给下个视频用
            last_ts_audio, last_ts_video = get_last_ts(flv_body)

            last_ts_list.append((last_ts_audio, last_ts_video))

            # flv_body 就是视频数据，只是去掉了 flv_header 和 第一个 tag(脚本帧)
            viedo_data_list.append(flv_body)

    '''准备合并视频'''
    file_path = os.popen('pwd').read()

    make_file = os.popen("ls").read()

    if "merged_video" not in make_file:

        os.system("mkdir merged_video")

    save_path = file_path.strip('\n') + '/merged_video/'

    with open(save_path + merged_video_name + '.flv', 'wb') as filein:

        for n in range(0, len(viedo_data_list)):

            if n == 0:

                update_data = update_duration(
                    viedo_data_list[n], duration_list)  # 修改 duration，基本结束了

                filein.write(update_data)  # 写入文件

            else:

                filein.write(viedo_data_list[n])

    tip_message = "文件已储存在 {}\n视频名称为: {}".format(save_path, merged_video_name)

    print(tip_message)


def get_video(folder_name='FlashVideo/'):

    search_folder = os.popen('ls').read()

    search_folder = search_folder.split("\n")

    if "FlashVideo" not in search_folder:

        print(">>> 已在本文件目录建创建 FlashVideo 文件夹，请将需要合并的 flv 格式视频，放置本文件夹下，并再次运行程序")

        os.system("makedir FlashVideo")

        sys.exit()

    video_name_list = []

    path = (os.popen('pwd').read()).strip('\n') + '/'

    video_path = path + folder_name

    video_name = os.popen("ls %s" % video_path).read()

    video_name_list = (video_name.rstrip('\n')).split('\n')

    #  设置合并后的视频名称
    merged_video_name = ((video_name_list[0]).split("_"))[0]
    # print(merged_video_name)

    print("[>>>]  将要合并以下视频，请确认顺序:\n\n" +
          "\n".join(e for e in video_name_list) + "\n")
    print("[>>>] 一共 {} 个视频,请核对是否有误".format(len(video_name_list)) + "\n")

    try:

        while True:

            confirm = input("[>>>]  请输入 y/n\n")

            if confirm == 'y':

                print("[>>>]  即将开始合并视频，请耐心等待...")

                break

            elif confirm == 'n':

                print("[>>>]  已取消本次合并")

                sys.exit()

            else:

                print("[>>>]  请正确输入 y 或者 n,然后回车")

    except KeyboardInterrupt:

        print("Have a good day!\n")

        sys.exit()

    return video_path, video_name_list, merged_video_name


if __name__ == '__main__':

    merge_flv_video()
    # get_video()

