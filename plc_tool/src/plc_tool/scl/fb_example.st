VAR_INPUT
    Input1 : BOOL;    // 输入布尔值
    Input2 : INT;     // 输入整数值
END_VAR

VAR_OUTPUT
    Output1 : BOOL;   // 输出布尔值
    Output2 : INT;    // 输出整数值
END_VAR

VAR
    TempVar : REAL;   // 临时变量
END_VAR

BEGIN
    // 简单的示例逻辑
    IF Input1 THEN
        Output1 := TRUE;
        Output2 := Input2 * 2;
    ELSE
        Output1 := FALSE;
        Output2 := Input2;
    END_IF;
END_PROGRAM 