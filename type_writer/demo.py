import serial
import time
import threading
import asyncio
from core.motion_planner import MotionPlanner
from control.control import controller
from read_write.read_write import read_motor_position,read_position,write_position,OperationResult
from translation.translation_motor import build_abs_pos_frame,build_speed_frame

pulse=51200
laps=129
speed=1200



if __name__=='__main__':
    result=OperationResult(success=False,message="原始结果",code=0,value=None)
    write_position(r'C:/Users/ZHY/Desktop/p_Code/program_type/type_writer/_position_x.bin', 0)
    write_position(r'C:/Users/ZHY/Desktop/p_Code/program_type/type_writer/_position_y1.bin', 0)
    write_position(r'C:/Users/ZHY/Desktop/p_Code/program_type/type_writer/_position_y2.bin', 0)
    result = read_position(r'C:/Users/ZHY/Desktop/p_Code/program_type/type_writer/_position_x.bin')
    if result.success:
        print(f"从文件读取位置: {result.value}")
    else:
        print(f"从文件读取状态: {result.message}")
    result = read_position(r'C:/Users/ZHY/Desktop/p_Code/program_type/type_writer/_position_y1.bin')
    if result.success:
        print(f"从文件读取位置: {result.value}")
    else:
        print(f"从文件读取状态: {result.message}")
    result = read_position(r'C:/Users/ZHY/Desktop/p_Code/program_type/type_writer/_position_y2.bin')
    if result.success:
        print(f"从文件读取位置: {result.value}")
    else:
        print(f"从文件读取状态: {result.message}")
