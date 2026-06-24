VAR_INPUT
    SetPoint : REAL;      // 设定值
    ActualValue : REAL;   // 实际值
    Kp : REAL;           // 比例系数
    Ki : REAL;           // 积分系数
    Kd : REAL;           // 微分系数
    Enable : BOOL;       // 使能信号
    Reset : BOOL;        // 复位信号
END_VAR

VAR_OUTPUT
    Output : REAL;       // 输出值
    Error : REAL;        // 误差
    Running : BOOL;      // 运行状态
END_VAR

VAR
    Integral : REAL;     // 积分值
    LastError : REAL;    // 上次误差
    DeltaTime : REAL;    // 采样时间
    FirstScan : BOOL;    // 首次扫描标志
END_VAR

BEGIN
    // 初始化
    IF FirstScan THEN
        FirstScan := FALSE;
        DeltaTime := 0.1; // 100ms采样时间
        Integral := 0.0;
        LastError := 0.0;
    END_IF;

    // PID控制
    IF Enable THEN
        Running := TRUE;
        
        // 计算误差
        Error := SetPoint - ActualValue;
        
        // 复位处理
        IF Reset THEN
            Integral := 0.0;
            LastError := 0.0;
            Output := 0.0;
            RETURN;
        END_IF;
        
        // PID算法
        Integral := Integral + Error * DeltaTime;
        
        // 计算输出
        Output := Kp * Error +                    // 比例项
                 Ki * Integral +                  // 积分项
                 Kd * (Error - LastError) / DeltaTime;  // 微分项
        
        // 更新上次误差
        LastError := Error;
        
        // 限制输出范围 (0-100%)
        IF Output < 0.0 THEN
            Output := 0.0;
            Integral := Integral - Error * DeltaTime; // 抗积分饱和
        ELSIF Output > 100.0 THEN
            Output := 100.0;
            Integral := Integral - Error * DeltaTime; // 抗积分饱和
        END_IF;
        
    ELSE
        Running := FALSE;
        Output := 0.0;
        Integral := 0.0;
        LastError := 0.0;
    END_IF;
END_PROGRAM 