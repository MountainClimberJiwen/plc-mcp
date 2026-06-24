VAR_INPUT
    Start : BOOL;         // 启动信号
    Stop : BOOL;         // 停止信号
    Speed_SP : REAL;     // 速度设定值 (0-100%)
    Emergency_Stop : BOOL; // 紧急停止
END_VAR

VAR_OUTPUT
    Motor_Running : BOOL;  // 电机运行状态
    Current_Speed : REAL;  // 当前速度
    Error : BOOL;         // 错误状态
    Error_Code : INT;     // 错误代码
END_VAR

VAR
    Motor_State : INT;     // 电机状态 (0:停止, 1:启动中, 2:运行中, 3:停止中, 4:错误)
    Acceleration : REAL;   // 加速度
    Deceleration : REAL;  // 减速度
    Timer : TON;          // 定时器
END_VAR

BEGIN
    // 紧急停止处理
    IF Emergency_Stop THEN
        Motor_State := 4;
        Error := TRUE;
        Error_Code := 1; // 紧急停止错误代码
        Motor_Running := FALSE;
        Current_Speed := 0.0;
        RETURN;
    END_IF;

    // 状态机处理
    CASE Motor_State OF
        0:  // 停止状态
            IF Start AND NOT Stop THEN
                Motor_State := 1;
                Error := FALSE;
                Error_Code := 0;
            END_IF;
            Current_Speed := 0.0;
            Motor_Running := FALSE;

        1:  // 启动中
            Motor_Running := TRUE;
            IF Current_Speed < Speed_SP THEN
                Current_Speed := Current_Speed + Acceleration;
            ELSE
                Motor_State := 2;
            END_IF;

        2:  // 运行中
            IF Stop OR NOT Start THEN
                Motor_State := 3;
            ELSE
                Current_Speed := Speed_SP;
            END_IF;

        3:  // 停止中
            IF Current_Speed > 0.0 THEN
                Current_Speed := Current_Speed - Deceleration;
            ELSE
                Motor_State := 0;
                Motor_Running := FALSE;
            END_IF;

        4:  // 错误状态
            IF NOT Emergency_Stop AND NOT Start THEN
                Motor_State := 0;
                Error := FALSE;
                Error_Code := 0;
            END_IF;
    END_CASE;

    // 限制速度范围
    IF Current_Speed < 0.0 THEN
        Current_Speed := 0.0;
    ELSIF Current_Speed > 100.0 THEN
        Current_Speed := 100.0;
    END_IF;
END_PROGRAM 