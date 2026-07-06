#include "stm32f10x.h"                  // Device header
#include "Delay.h"
#include "Servo.h"
#include "Key.h"
#include "Motor.h"

uint8_t KeyNum;
float Angle;

int main(void)
{
	Servo_Init();
	Key_Init();
	Motor_Init();
	
	
	while (1)
	{
		KeyNum = Key_GetNum();
		if (KeyNum == 1)
		{
			Motor_SetSpeed(80);
			Delay_s(1);
			Motor_SetSpeed(0);
			Angle = Angleturn(Angle);
			Servo_SetAngle(Angle);
			Delay_s(2);
			Angle = Angleturn(Angle);
			Servo_SetAngle(Angle);
		}
		
	}
}
