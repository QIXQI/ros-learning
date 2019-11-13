#!/usr/bin/env python
import rospy
 
from geometry_msgs.msg import Twist
 
import sys, select, termios, tty
 
#操作教程
msg = """
Control The Robot!
---------------------------
Moving around:
   u    i    o
   j    k    l
   m    ,    .
q/z : increase/decrease max speeds by 10%
w/x : increase/decrease only linear speed by 10%
e/c : increase/decrease only angular speed by 10%
space key, k : force stop
anything else : stop smoothly
CTRL-C to quit
"""
#用于改变机器人运动方向的字典
moveBindings = {
        'i':(1,0),
        'o':(1,-1),
        'j':(0,1),
        'l':(0,-1),
        'u':(1,1),
        ',':(-1,0),
        '.':(-1,1),
        'm':(-1,-1),
           }
#用于改变机器人运动速度的字典
speedBindings={
        'q':(1.1,1.1),
        'z':(.9,.9),
        'w':(1.1,1),
        'x':(.9,1),
        'e':(1,1.1),
        'c':(1,.9),
          }
 
def getKey():
    tty.setraw(sys.stdin.fileno())
    #tty 模块定义了将 tty 放入 cbreak 和 raw 模式的函数。因为它需要 termios 模块，所以只能在 Unix 上运行。
    #tty 模块定义了以下函数：
    #tty.setraw(fd, when=termios.TCSAFLUSH)
    #将文件描述符 fd 的模式更改为 raw 。如果 when 被省略，则默认为 termios.TCSAFLUSH ，并传递给 termios.tcsetattr() 。
    #tty.setcbreak(fd, when=termios.TCSAFLUSH)
    #将文件描述符 fd 的模式更改为 cbreak 。如果 when 被省略，则默认为 termios.TCSAFLUSH ，并传递给 termios.tcsetattr() 。
    rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
    #rlist则是键盘输入的信息列表
    #select()方法接收并监控3个通信列表
    #第一个是所有的输入的data,就是指外部发过来的数据
    #第2个是监控和接收所有要发出去的data(outgoing data)
    #第3个监控错误信息
 
    #判断是否接受到数据
    if rlist:
        key = sys.stdin.read(1)#读取终端上的交互输入
    else:
        key = ''
 
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
    #termios.tcsetattr(fd, when, attributes)
    #fd获取终端上交互输入的返回列表
    #when  tcsanow立即更改，tcsadrain在传输所有排队的输出后更改，或tcsaflush在传输所有排队的输出并丢弃所有排队的输入后更改。
    
    return key
 
speed = .2  #设置初始直行速度
turn = 1    #设置初始角速度
 
def vels(speed,turn): #打印输入目前的设置的速度和角速度
    return "currently:\tspeed %s\tturn %s " % (speed,turn)
 
if __name__=="__main__":
    settings = termios.tcgetattr(sys.stdin) #返回一个包含文件描述符fd的tty属性的列表，用于getkey的第三个参数
    
    rospy.init_node('robot_teleop')#初始化节点
    pub = rospy.Publisher('/cmd_vel_mux/input/teleop', Twist, queue_size=5)#发布话题
 
    x = 0  #代表机器人的前进和后退方向 1前进-1后退
    th = 0  #代表机器人的原地左转和右转方向  1左转-1右转
    status = 0 #调整加速减速的次数
    count = 0
    
    target_speed = 0   #目标直行速度 
    target_turn = 0     #目标角速度
    control_speed = 0   #实际运行直行速度
    control_turn = 0    #实际运行角速度
    try:
        print msg   #打印操作教程
        print vels(speed,turn)  #打印目前设置的最大速度和角速度
        while(1):
            key = getKey()  #获取终端上键盘的输入信息
            if key in moveBindings.keys(): #判断是否是控制移动方向的字典值
                x = moveBindings[key][0]
                th = moveBindings[key][1]
                count = 0
            elif key in speedBindings.keys():   #判断是否控制速度大小的字典值
                speed = speed * speedBindings[key][0]
                turn = turn * speedBindings[key][1]
                count = 0
 
                print vels(speed,turn)  #打印更改后的最大速度和角速度
                #超过14后重新打印操作教程
                if (status == 14):
                    print msg
                status = (status + 1) % 15
            elif key == ' ' or key == 'k' :#其余命令或者是k，均是代表停止
                x = 0
                th = 0
                control_speed = 0 #实际直行速度给0
                control_turn = 0    #实际角速度给0
            else:
                count = count + 1  #未接受键盘信息时，保持停止
                if count > 4:
                    x = 0
                    th = 0
                if (key == '\x03'):#猜测是ctrl+c退出键盘控制
                    break
 
            target_speed = speed * x #目标直行速度
            target_turn = turn * th #目标角速度
 
            #控制机器人的加速和减速过程 0.02,0.1分别代表当前频率下的速度和角速度变化率，相当于加速度大小
            if target_speed > control_speed:
                control_speed = min( target_speed, control_speed + 0.02 )
            elif target_speed < control_speed:
                control_speed = max( target_speed, control_speed - 0.02 )
            else:
                control_speed = target_speed
 
            if target_turn > control_turn:
                control_turn = min( target_turn, control_turn + 0.1 )
            elif target_turn < control_turn:
                control_turn = max( target_turn, control_turn - 0.1 )
            else:
                control_turn = target_turn
 
            twist = Twist()#初始化twist
            twist.linear.x = control_speed; twist.linear.y = 0; twist.linear.z = 0
            twist.angular.x = 0; twist.angular.y = 0; twist.angular.z = control_turn
            pub.publish(twist)#发布实时状态的控制速度和角速度
 
            #print("loop: {0}".format(count))
            #print("target: vx: {0}, wz: {1}".format(target_speed, target_turn))
            #print("publihsed: vx: {0}, wz: {1}".format(twist.linear.x, twist.angular.z))
 
    except:
        print e
 
    finally:  #控制机器人处于停止状态
        twist = Twist()
        twist.linear.x = 0; twist.linear.y = 0; twist.linear.z = 0
        twist.angular.x = 0; twist.angular.y = 0; twist.angular.z = 0
        pub.publish(twist)
 
    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)

