FUNCTION_BLOCK "Temperature_Control"
// 输入变量声明
VAR_INPUT
    ActualTemp      : REAL;    // 实际温度值 (摄氏度)
    SetpointTemp    : REAL;    // 目标温度值 (摄氏度)
    ManualMode      : BOOL;    // 手动模式开关
    ManualOutput    : REAL;    // 手动模式下的输出值 (0-100%)
    Reset          : BOOL;     // 复位信号
    EnableControl  : BOOL;     // 控制使能
END_VAR

// 输出变量声明
VAR_OUTPUT
    HeatingOutput   : REAL;    // 加热器输出 (0-100%)
    HighTempAlarm   : BOOL;    // 高温报警
    LowTempAlarm    : BOOL;    // 低温报警
    SystemStatus    : INT;     // 系统状态代码
END_VAR

// 静态变量声明
VAR
    // PID控制参数
    Kp : REAL := 1.5;         // 比例系数
    Ki : REAL := 0.3;         // 积分系数
    Kd : REAL := 0.1;         // 微分系数
    
    // 内部变量
    Error           : REAL;    // 温度误差
    IntegralSum     : REAL;    // 积分累加值
    LastError       : REAL;    // 上次误差
    DerivativeTerm  : REAL;    // 微分项
    
    // 报警设置
    HighTempLimit   : REAL := 85.0;    // 高温报警阈值
    LowTempLimit    : REAL := 5.0;     // 低温报警阈值
    
    // 定时器
    SampleTime      : TIME := T#100MS;  // 采样时间
    Timer           : TON;              // 定时器实例
    
    // 数据处理
    TempHistory     : ARRAY[0..9] OF REAL;  // 温度历史数据
    HistoryIndex    : INT := 0;             // 历史数据索引
    AverageTemp     : REAL;                 // 平均温度
END_VAR

BEGIN
    // 系统使能检查
    IF NOT EnableControl THEN
        HeatingOutput := 0.0;
        SystemStatus := 0;  // 系统停止
        RETURN;
    END_IF;
    
    // 复位处理
    IF Reset THEN
        IntegralSum := 0.0;
        LastError := 0.0;
        HeatingOutput := 0.0;
        HistoryIndex := 0;
        SystemStatus := 1;  // 系统复位
        RETURN;
    END_IF;
    
    // 定时器控制
    Timer(IN := TRUE, PT := SampleTime);
    IF NOT Timer.Q THEN
        RETURN;
    END_IF;
    Timer(IN := FALSE);
    
    // 温度历史记录更新
    TempHistory[HistoryIndex] := ActualTemp;
    HistoryIndex := (HistoryIndex + 1) MOD 10;
    
    // 计算平均温度
    AverageTemp := 0.0;
    FOR i := 0 TO 9 DO
        AverageTemp := AverageTemp + TempHistory[i];
    END_FOR;
    AverageTemp := AverageTemp / 10.0;
    
    // 报警检查
    HighTempAlarm := ActualTemp >= HighTempLimit;
    LowTempAlarm := ActualTemp <= LowTempLimit;
    
    // 手动/自动模式控制
    IF ManualMode THEN
        HeatingOutput := LIMIT(0.0, ManualOutput, 100.0);
        SystemStatus := 2;  // 手动模式
    ELSE
        // PID控制计算
        Error := SetpointTemp - ActualTemp;
        
        // 积分项计算
        IntegralSum := IntegralSum + (Error * DINT_TO_REAL(SampleTime) / 1000.0);
        IntegralSum := LIMIT(-100.0, IntegralSum, 100.0);
        
        // 微分项计算
        DerivativeTerm := (Error - LastError) / (DINT_TO_REAL(SampleTime) / 1000.0);
        LastError := Error;
        
        // PID输出计算
        HeatingOutput := (Kp * Error) + (Ki * IntegralSum) + (Kd * DerivativeTerm);
        HeatingOutput := LIMIT(0.0, HeatingOutput, 100.0);
        
        SystemStatus := 3;  // 自动模式
    END_IF;
    
    // 报警状态更新系统状态
    IF HighTempAlarm OR LowTempAlarm THEN
        SystemStatus := 4;  // 报警状态
    END_IF;
    
END_FUNCTION_BLOCK 