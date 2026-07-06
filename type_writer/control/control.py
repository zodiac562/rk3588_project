import serial
import time
import asyncio
import threading

from read_write.read_write import read_position,write_position,OperationResult
from translation.translation_motor import build_speed_frame,build_abs_pos_frame,build_rel_pos_frame

stall_sign=False
condition=threading.Condition()

class controller():

    def __init__(self):
        self.DELAYTIME=0.01
        self.BACKSPEED=1200
        self.CLEARPOS='c501f8be5c'
        self.CLEARSTATUS='c501fbc15c'
        self.HURRYSTOP='c501fcc25c'
   

    async def auto_zero_frame(self,com:serial.Serial,file:str) -> None:
        speed=self.BACKSPEED
        pos=OperationResult(success=False,message="原始结果",code=0,value=None)
        pos=read_position(file)

        auto_zero=build_rel_pos_frame(0x01,'reverse',100,speed,pos.value)
        zero_speed=build_speed_frame(0x01,'forward',100,0)

        back_time=pos.value/(speed*51200/60) + 3

        com.write(bytes.fromhex(auto_zero))
        await asyncio.sleep(back_time)
       


        com.write(bytes.fromhex(zero_speed))
        await asyncio.sleep(self.DELAYTIME)

        com.reset_input_buffer()
        
        for i in range(5):

            transit_pos=build_abs_pos_frame(0x01,'forward',1,1,51200)
            com.write(bytes.fromhex(transit_pos))
            com.flush()
            await asyncio.sleep(self.DELAYTIME)
            com.write(bytes.fromhex(self.CLEARPOS))
            com.flush()
            await asyncio.sleep(self.DELAYTIME)

            transit_pos=build_abs_pos_frame(0x01,'forward',1,1,51200)
            com.write(bytes.fromhex(transit_pos))
            com.flush()
            await asyncio.sleep(self.DELAYTIME)

            com.write(bytes.fromhex(self.CLEARPOS))
            com.flush()
            await asyncio.sleep(self.DELAYTIME)

        for i in range(100):

            com.write(bytes.fromhex(zero_speed))
            await asyncio.sleep(self.DELAYTIME)



    def paired_motor_control(self,motor_com1:serial.Serial,motor_com2:serial.Serial,direction:str,accel:int,speed:int) -> None:
        
        speed_frame=build_speed_frame(0x01,direction,accel,speed)
        motor_com1.write(bytes.fromhex(speed_frame))
        motor_com2.write(bytes.fromhex(speed_frame))
        time.sleep(self.DELAYTIME)

    
    def hurry_stop(self,*args:serial.Serial) -> None:
        for motor_com in args:
            motor_com.write(bytes.fromhex(self.HURRYSTOP))
            motor_com.flush()

        time.sleep(1)

        
        for motor_com in args:
            motor_com.write(bytes.fromhex(self.CLEARSTATUS))
            motor_com.flush()

        time.sleep(self.DELAYTIME)
