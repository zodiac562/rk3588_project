#include "stm32f10x.h"                  // Device header
#include "PWM.h"

void Servo_Init(void)
{
	PWM_Init();
}

void Servo_SetAngle(float Angle)
{
	PWM_SetCompare2(Angle / 180 * 2000 + 500);
}

float Angleturn(float Angle)
{
	if(Angle == 0)
	{
		return 180;
	}
	if(Angle == 180)
	{
		return 0;
	}
}
